"""Lead agent orchestrator: coordinates intake, research, composition, and adaptation.

Architecture: Lead Agent + Parallel Workers + Verify Loop
- Lead agent (this file) coordinates the overall flow
- Claude proposes tool calls via tool-use API (hybrid pattern)
- Workers execute tools in parallel via ThreadPoolExecutor
- Composer builds and verifies the itinerary with a repair loop
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from src.agent.composer import (
    align_days_to_candidates,
    apply_day_swap_request,
    build_daily_structure_input,
    build_itinerary,
    compact_reply,
    compose_final_reply,
    enrich_days,
    generate_daily_structure_with_claude,
    polish_itinerary_days,
    repair_daily_structure_with_claude,
    verify_itinerary_quality,
)
from src.agent.intake import (
    build_clarifying_reply,
    extract_brief_patch,
    merge_brief,
    missing_fields,
)
from src.agent.llm_helpers import normalize_blocks
from src.agent.preference_update import build_planning_preface, detect_changed_fields
from src.agent.prompts import SYSTEM_PROMPT, TOOL_PLANNING_PROMPT
from src.agent.research import (
    build_tool_input,
    build_tool_plan,
    execute_tools_parallel,
    payloads_from_previous,
    prepare_candidate_context,
)
from src.agent.state import AgentEvent, AgentRunResult, ConversationState
from src.tools.registry import get_claude_tools, run_tool
from src.tools.schemas import (
    ItineraryDraft,
    PlanningBrief,
)


@dataclass
class AgentOrchestrator:
    """Lead agent that coordinates the travel planning pipeline.

    Flow: Intake → Tool Planning (Claude) → Parallel Gather → Compose → Verify → Polish → Reply
    """

    client: Any
    model: str
    system_prompt: str = SYSTEM_PROMPT
    max_tokens: int = 1800

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, state: ConversationState, user_message: str) -> AgentRunResult:
        events = list(self.stream(state=state, user_message=user_message))
        final_event = next((e for e in reversed(events) if e.type == "final_response"), None)
        reply = final_event.message if final_event and final_event.message else ""
        payload = final_event.payload if final_event and isinstance(final_event.payload, dict) else {}
        return AgentRunResult(
            reply=reply,
            events=events,
            itinerary=state.last_itinerary,
            workspace_ready=bool(payload.get("workspace_ready", state.workspace_ready)),
            missing_fields=list(payload.get("missing_fields", [])),
            planning_brief=state.planning_brief,
        )

    def stream(self, state: ConversationState, user_message: str):
        """Main agent loop: intake → gather → compose → verify → reply.

        Yields AgentEvent objects that drive the streaming UI.
        """
        user_text = user_message.strip()
        messages = list(state.messages)
        messages.append({"role": "user", "content": user_text})

        yield AgentEvent(type="session", payload={"session_id": state.session_id})

        # ── Phase 1: Intake ──────────────────────────────────────────
        previous_brief = state.planning_brief.model_copy(deep=True)
        patch = extract_brief_patch(
            self.client, self.model, previous_brief, user_text, state.last_itinerary
        )
        brief = merge_brief(previous_brief, patch)
        state.planning_brief = brief

        missing = missing_fields(brief)
        if missing:
            reply = build_clarifying_reply(self.client, self.model, brief, missing)
            messages.append({"role": "assistant", "content": reply})
            state.messages = messages
            state.workspace_ready = False
            yield AgentEvent(type="assistant_message", message=reply)
            yield AgentEvent(
                type="final_response",
                message=reply,
                payload={
                    "reply": reply,
                    "itinerary": state.last_itinerary.model_dump(mode="json") if state.last_itinerary else None,
                    "workspace_ready": False,
                    "missing_fields": missing,
                    "planning_brief": brief.model_dump(mode="json"),
                },
            )
            return

        # ── Phase 2: Detect changes & plan ───────────────────────────
        changed_fields = detect_changed_fields(previous_brief, brief, patch)
        state.workspace_ready = True

        preface = build_planning_preface(changed_fields, has_existing_plan=state.last_itinerary is not None)
        if preface:
            yield AgentEvent(type="assistant_message", message=preface)

        # ── Phase 3: Tool planning (hybrid — Claude proposes, we execute) ─
        tool_plan = self._plan_tools_with_claude(brief, changed_fields, state.last_itinerary)
        previous_payloads = payloads_from_previous(state.last_itinerary)
        tool_inputs: dict[str, dict[str, Any]] = {}
        tool_payloads: dict[str, Any] = dict(previous_payloads)

        # Build inputs and emit tool_started events
        gather_specs: list[tuple[str, dict[str, Any]]] = []
        for tool_name in tool_plan["gather_tools"]:
            tool_input = build_tool_input(tool_name, brief, state.last_itinerary)
            if not tool_input:
                continue
            tool_inputs[tool_name] = tool_input
            gather_specs.append((tool_name, tool_input))
            yield AgentEvent(type="tool_started", tool_name=tool_name, message=f"Running {tool_name}")

        # ── Phase 4: Parallel gather (workers) ───────────────────────
        if gather_specs:
            results = execute_tools_parallel(gather_specs)
            for tool_name, (status, result) in results.items():
                if status == "ok":
                    tool_payloads[tool_name] = result
                    yield AgentEvent(type="tool_completed", tool_name=tool_name, payload=result)
                else:
                    yield AgentEvent(type="tool_completed", tool_name=tool_name, payload={"error": result})

        # ── Phase 5: Compose daily structure ─────────────────────────
        planning_context = prepare_candidate_context(brief, tool_payloads, state.last_itinerary)
        daily_input = build_daily_structure_input(
            brief, tool_payloads, state.last_itinerary,
            patch.day_swap_request, planning_context,
        )
        tool_inputs["get_daily_structure"] = daily_input.model_dump(mode="json")
        yield AgentEvent(type="tool_started", tool_name="get_daily_structure", message="Running get_daily_structure")

        generated_days = generate_daily_structure_with_claude(
            self.client, self.model, self.system_prompt,
            brief, daily_input, planning_context,
            tool_payloads.get("get_weather"),
        )
        if generated_days:
            day_output = [day.model_dump(mode="json") for day in generated_days]
        else:
            day_output = run_tool("get_daily_structure", tool_inputs["get_daily_structure"])
        tool_payloads["get_daily_structure"] = day_output
        yield AgentEvent(type="tool_completed", tool_name="get_daily_structure", payload=day_output)

        # ── Phase 6: Build itinerary & apply swaps ───────────────────
        itinerary = build_itinerary(tool_inputs, tool_payloads, state.last_itinerary, planning_context)
        if itinerary and patch.day_swap_request:
            itinerary = apply_day_swap_request(itinerary, patch.day_swap_request)

        # ── Phase 7: Verify & Repair loop ────────────────────────────
        if itinerary:
            verification = verify_itinerary_quality(
                self.client, self.model, self.system_prompt, brief, itinerary,
            )
            if not verification["approved"]:
                yield AgentEvent(
                    type="assistant_message",
                    message="I am tightening this draft so it feels more coherent, less repetitive, and more useful.",
                )
                repaired_days = repair_daily_structure_with_claude(
                    self.client, self.model, self.system_prompt,
                    brief, itinerary, planning_context, verification["issues"],
                )
                if repaired_days:
                    repaired_days = align_days_to_candidates(
                        repaired_days,
                        planning_context["selected_hotel"],
                        planning_context["ranked_restaurants"],
                        planning_context["ranked_experiences"],
                    )
                    repaired_itinerary = itinerary.model_copy(
                        update={
                            "days": enrich_days(
                                repaired_days,
                                planning_context["selected_hotel"],
                                planning_context["restaurants"],
                                planning_context["experiences"],
                            )
                        }
                    )
                    repaired_verification = verify_itinerary_quality(
                        self.client, self.model, self.system_prompt,
                        brief, repaired_itinerary,
                    )
                    if _issue_score(repaired_verification["issues"]) <= _issue_score(verification["issues"]):
                        itinerary = repaired_itinerary

        # ── Phase 8: Polish copy ─────────────────────────────────────
        if itinerary:
            itinerary = polish_itinerary_days(
                self.client, self.model, self.system_prompt, brief, itinerary,
            )

        # ── Phase 9: Final reply ─────────────────────────────────────
        raw_reply = compose_final_reply(
            self.client, self.model, self.system_prompt,
            brief, itinerary, changed_fields,
        )
        reply = compact_reply(raw_reply, itinerary)
        if itinerary:
            itinerary = itinerary.model_copy(update={"summary": reply})

        messages.append({"role": "assistant", "content": reply})
        state.messages = messages
        state.last_itinerary = itinerary

        yield AgentEvent(
            type="final_response",
            message=reply,
            payload={
                "reply": reply,
                "itinerary": itinerary.model_dump(mode="json") if itinerary else None,
                "workspace_ready": True,
                "missing_fields": [],
                "planning_brief": brief.model_dump(mode="json"),
            },
        )

    # ------------------------------------------------------------------
    # Hybrid tool planning: Claude proposes, orchestrator executes
    # ------------------------------------------------------------------

    def _plan_tools_with_claude(
        self,
        brief: PlanningBrief,
        changed_fields: set[str],
        previous: ItineraryDraft | None,
    ) -> dict[str, Any]:
        """Let Claude decide which tools to call via tool-use API.

        Hybrid approach: Claude sees the tool schemas and proposes calls,
        but if Claude fails or returns unexpected output, we fall back to
        the deterministic build_tool_plan based on field dependencies.
        The orchestrator then executes proposed tools in parallel for speed.
        """
        has_existing_plan = previous is not None

        try:
            tools = get_claude_tools()
            # Only include gather tools (not get_daily_structure, which runs after gather)
            gather_tools = [t for t in tools if t["name"] != "get_daily_structure"]

            context = {
                "planning_brief": brief.model_dump(mode="json"),
                "has_existing_plan": has_existing_plan,
                "changed_fields": sorted(changed_fields) if changed_fields else [],
            }
            if has_existing_plan:
                context["instruction"] = (
                    "The user already has a plan. Only call tools whose inputs are affected "
                    "by the changed fields. If nothing changed, call no tools."
                )

            response = self.client.messages.create(
                model=self.model,
                max_tokens=600,
                system=TOOL_PLANNING_PROMPT,
                tools=gather_tools,
                messages=[{"role": "user", "content": json.dumps(context, ensure_ascii=False)}],
            )

            # Extract tool names from Claude's tool_use blocks
            blocks = normalize_blocks(response.content)
            proposed_tools = [
                b["name"] for b in blocks
                if b.get("type") == "tool_use" and b.get("name")
            ]

            if proposed_tools:
                return {"gather_tools": sorted(set(proposed_tools))}
        except Exception:  # pragma: no cover
            pass

        # Deterministic fallback: use field-dependency mapping
        return build_tool_plan(changed_fields, has_existing_plan)


def _issue_score(issues: list[dict[str, Any]]) -> int:
    """Sum severity scores across all issues."""
    return sum(int(issue.get("severity", 1)) for issue in issues)
