"""Lead agent orchestrator: coordinates intake, research, composition, and adaptation.

Architecture: Lead Agent + Agentic Tool-Use Loop + Verify Loop
- Lead agent (this file) coordinates the overall flow
- Standard Anthropic tool-use loop: Claude proposes → parallel execution → results returned to Claude
- Two rounds of gathering: Round 1 (base data) → Round 2 (budget + packing, informed by Round 1)
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
    apply_smart_defaults,
    build_landing_followup_reply,
    build_clarifying_reply,
    build_workspace_handoff_reply,
    extract_brief_patch,
    merge_brief,
    missing_landing_followup_fields,
    missing_essential_fields,
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
from src.tools.registry import GATHER_TOOL_NAMES, get_claude_tools, run_tool
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

        # ── Phase 1: Intake (lean — only block on essentials) ────────
        previous_brief = state.planning_brief.model_copy(deep=True)
        patch = extract_brief_patch(
            self.client, self.model, previous_brief, user_text, state.last_itinerary
        )
        brief = merge_brief(previous_brief, patch)

        should_hold_landing = (
            state.last_itinerary is None
            and not state.workspace_ready
            and not state.intake_followup_asked
        )
        landing_missing = missing_landing_followup_fields(brief)
        if should_hold_landing and landing_missing:
            reply = build_landing_followup_reply(brief, landing_missing, user_text)
            messages.append({"role": "assistant", "content": reply})
            state.planning_brief = brief
            state.messages = messages
            state.workspace_ready = False
            state.intake_followup_asked = True
            yield AgentEvent(type="assistant_message", message=reply)
            yield AgentEvent(
                type="final_response",
                message=reply,
                payload={
                    "reply": reply,
                    "itinerary": None,
                    "workspace_ready": False,
                    "missing_fields": landing_missing,
                    "planning_brief": brief.model_dump(mode="json"),
                },
            )
            return

        brief = apply_smart_defaults(brief)
        state.planning_brief = brief

        essential_missing = missing_essential_fields(brief)
        if essential_missing:
            if state.intake_followup_asked and state.last_itinerary is None:
                reply = build_workspace_handoff_reply(brief, essential_missing, user_text)
                workspace_ready = True
            else:
                reply = build_clarifying_reply(self.client, self.model, brief, essential_missing)
                workspace_ready = False
            messages.append({"role": "assistant", "content": reply})
            state.planning_brief = brief
            state.messages = messages
            state.workspace_ready = workspace_ready
            yield AgentEvent(type="assistant_message", message=reply)
            yield AgentEvent(
                type="final_response",
                message=reply,
                payload={
                    "reply": reply,
                    "itinerary": state.last_itinerary.model_dump(mode="json") if state.last_itinerary else None,
                    "workspace_ready": workspace_ready,
                    "missing_fields": essential_missing,
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

        # ── Phase 3+4: Agentic gather loop (standard Anthropic tool-use pattern) ─
        # Round 1: Claude sees brief → proposes base tools → results returned to Claude
        # Round 2: Claude sees hotel/weather → proposes estimate_budget + packing → results returned
        tool_payloads, gather_events = self._agentic_gather_loop(brief, changed_fields, state.last_itinerary)
        tool_inputs: dict[str, dict[str, Any]] = {}
        for event in gather_events:
            yield event

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

        # ── Phase 9: Final reply + story metadata ─────────────────────
        raw_reply, story_meta = compose_final_reply(
            self.client, self.model, self.system_prompt,
            brief, itinerary, changed_fields,
        )
        reply = compact_reply(raw_reply, itinerary)
        if itinerary:
            itinerary = itinerary.model_copy(update={
                "summary": reply,
                "trip_tone": story_meta.get("trip_tone") or itinerary.trip_tone,
                "key_moments": story_meta.get("key_moments") or itinerary.key_moments,
                "cultural_notes": story_meta.get("cultural_notes") or itinerary.cultural_notes,
            })

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
    # Agentic gather loop: proper Anthropic tool-use pattern
    # ------------------------------------------------------------------

    def _agentic_gather_loop(
        self,
        brief: PlanningBrief,
        changed_fields: set[str],
        previous: ItineraryDraft | None,
    ) -> tuple[dict[str, Any], list[AgentEvent]]:
        """Standard Anthropic tool-use loop with two rounds of parallel execution.

        Round 1: Claude sees trip brief → proposes base gather tools (weather, hotels,
                 restaurants, experiences, visa) → all executed in parallel →
                 ALL results returned to Claude via tool_result messages.

        Round 2: Claude now sees hotel neighborhood & weather conditions →
                 proposes dependent tools (estimate_budget, get_packing_suggestions)
                 using actual data from Round 1 → executed in parallel →
                 results returned to Claude.

        This closes the tool-use loop: Claude synthesises across all results and
        can make geographically informed decisions in the daily structure phase.

        Falls back to deterministic build_tool_plan if the loop fails entirely.
        """
        events: list[AgentEvent] = []
        tool_payloads: dict[str, Any] = dict(payloads_from_previous(previous))

        gather_tools = get_claude_tools(names=GATHER_TOOL_NAMES)
        has_existing_plan = previous is not None

        context: dict[str, Any] = {
            "planning_brief": brief.model_dump(mode="json"),
            "has_existing_plan": has_existing_plan,
            "changed_fields": sorted(changed_fields) if changed_fields else [],
        }
        if has_existing_plan:
            context["instruction"] = (
                "The user already has a plan. Only call tools whose inputs are affected "
                "by the changed fields. If nothing changed, call no tools."
            )

        loop_messages: list[dict[str, Any]] = [
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)}
        ]

        try:
            for _round in range(2):  # max 2 rounds
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    system=TOOL_PLANNING_PROMPT,
                    tools=gather_tools,
                    messages=loop_messages,
                )

                blocks = normalize_blocks(response.content)
                tool_uses = [b for b in blocks if b.get("type") == "tool_use"]

                if not tool_uses:
                    break  # Claude is done proposing tools

                # Emit tool_started events
                for tu in tool_uses:
                    events.append(AgentEvent(
                        type="tool_started",
                        tool_name=tu["name"],
                        message=f"Running {tu['name']}",
                    ))

                # Add Claude's full response to message history (required by API)
                loop_messages.append({"role": "assistant", "content": response.content})

                # Execute all proposed tools in parallel
                gather_specs = [
                    (tu["name"], tu.get("input", {}))
                    for tu in tool_uses
                ]
                results = execute_tools_parallel(gather_specs)

                # Build tool_result blocks and close the loop
                tool_result_blocks: list[dict[str, Any]] = []
                for tu in tool_uses:
                    name = tu.get("name", "")
                    tool_id = tu.get("id", "")
                    if name in results:
                        status, result = results[name]
                        if status == "ok":
                            tool_payloads[name] = result
                            events.append(AgentEvent(
                                type="tool_completed", tool_name=name, payload=result
                            ))
                            # Truncate to stay within token budget
                            result_str = json.dumps(result, ensure_ascii=False)
                            if len(result_str) > 4000:
                                result_str = result_str[:4000] + "...[truncated]"
                            tool_result_blocks.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": result_str,
                            })
                        else:
                            events.append(AgentEvent(
                                type="tool_completed", tool_name=name, payload={"error": result}
                            ))
                            tool_result_blocks.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "is_error": True,
                                "content": str(result),
                            })

                # Return results to Claude — this is what closes the loop
                if tool_result_blocks:
                    loop_messages.append({"role": "user", "content": tool_result_blocks})

        except Exception:  # pragma: no cover
            pass

        # Deterministic fallback: if the loop produced no base data, run standard plan
        base_tools = {"get_weather", "get_hotels", "get_restaurants", "get_experiences"}
        if not any(k in tool_payloads for k in base_tools):
            fallback_plan = build_tool_plan(changed_fields, has_existing_plan)
            fallback_specs = [
                (name, inp)
                for name in fallback_plan["gather_tools"]
                if (inp := build_tool_input(name, brief, previous)) is not None
            ]
            if fallback_specs:
                for name, _ in fallback_specs:
                    events.append(AgentEvent(
                        type="tool_started", tool_name=name, message=f"Running {name}"
                    ))
                fallback_results = execute_tools_parallel(fallback_specs)
                for name, (status, result) in fallback_results.items():
                    if status == "ok":
                        tool_payloads[name] = result
                        events.append(AgentEvent(
                            type="tool_completed", tool_name=name, payload=result
                        ))

        return tool_payloads, events


def _issue_score(issues: list[dict[str, Any]]) -> int:
    """Sum severity scores across all issues."""
    return sum(int(issue.get("severity", 1)) for issue in issues)
