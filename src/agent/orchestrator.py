"""Lead agent orchestrator: coordinates intake, research, composition, and adaptation.

Architecture: Lead Agent + Agentic Tool-Use Loop + Verify Loop
- Lead agent (this file) coordinates the overall flow
- Standard Anthropic tool-use loop: Claude proposes → parallel execution → results returned to Claude
- Two rounds of gathering: Round 1 (base data) → Round 2 (budget + packing, informed by Round 1)
- Composer builds and verifies the itinerary with a repair loop
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

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
    apply_pace_default,
    build_clarifying_reply,
    extract_brief_patch,
    merge_brief,
    missing_essential_fields,
    validate_brief_ready,
)
from src.agent.llm_helpers import normalize_blocks
from src.agent.preference_update import build_planning_preface, detect_changed_fields
from src.agent.prompts import SYSTEM_PROMPT, TOOL_PLANNING_PROMPT
from src.agent.research import (
    FIELD_TOOL_DEPENDENCIES,
    build_tool_input,
    build_tool_plan,
    execute_tools_parallel,
    execute_tools_streaming,
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

        # ── Phase 1: Intake — collect all 8 required fields ────────
        previous_brief = state.planning_brief.model_copy(deep=True)
        patch = extract_brief_patch(
            self.client, self.model, previous_brief, user_text, state.last_itinerary
        )
        brief = merge_brief(previous_brief, patch)
        state.planning_brief = brief

        # Gate: all 8 essential fields must be present before proceeding
        ready, essential_missing = validate_brief_ready(brief)
        if not ready:
            reply = build_clarifying_reply(self.client, self.model, brief, essential_missing)
            messages.append({"role": "assistant", "content": reply})
            state.messages = messages
            state.workspace_ready = False
            yield AgentEvent(type="assistant_message", message=reply)
            yield AgentEvent(
                type="final_response",
                message=reply,
                payload={
                    "reply": reply,
                    "itinerary": None,
                    "workspace_ready": False,
                    "missing_fields": essential_missing,
                    "planning_brief": brief.model_dump(mode="json"),
                },
            )
            return

        # All 8 fields present — apply pace default (only non-required field with a default)
        brief = apply_pace_default(brief)
        state.planning_brief = brief

        # ── Phase 2: Detect changes & plan ───────────────────────────
        changed_fields = detect_changed_fields(previous_brief, brief, patch)
        state.workspace_ready = True

        # Signal frontend to switch to workspace immediately
        yield AgentEvent(
            type="workspace_ready",
            payload={
                "workspace_ready": True,
                "planning_brief": brief.model_dump(mode="json"),
            },
        )

        # Skip preface message — jump straight into research steps
        has_existing = state.last_itinerary is not None
        yield AgentEvent(type="tool_started", tool_name="analyze_preferences", message="Analyzing your preferences")
        yield AgentEvent(
            type="tool_completed",
            tool_name="analyze_preferences",
            payload={
                "message": "Preferences analyzed",
                "changed_fields": sorted(changed_fields),
                "is_rerun": has_existing,
            },
        )

        # Show "planning research" as active while Claude decides which tools to call
        yield AgentEvent(type="tool_started", tool_name="plan_research", message="Planning research strategy")

        # ── Phase 3+4: Agentic gather loop (standard Anthropic tool-use pattern) ─
        # Now yields events in real-time instead of batching
        tool_payloads: dict[str, Any] = {}
        tool_inputs: dict[str, dict[str, Any]] = {}
        for event in self._agentic_gather_loop(brief, changed_fields, state.last_itinerary, tool_payloads):
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

        # ── Phase 7: Verify & Repair loop (SKIPPED FOR FASTER DEMO) ────────────────────────────
        # These steps are commented out for demo speed. Uncomment for production quality checks.
        # if itinerary:
        #     verification = verify_itinerary_quality(...)
        #     if not verification["approved"]:
        #         repaired_days = repair_daily_structure_with_claude(...)

        # ── Phase 9: Final reply + story metadata ─────────────────────
        yield AgentEvent(type="tool_started", tool_name="write_summary", message="Writing your trip summary")
        raw_reply, story_meta = compose_final_reply(
            self.client, self.model, self.system_prompt,
            brief, itinerary, changed_fields,
        )
        reply = compact_reply(raw_reply, itinerary)
        # Add itinerary link at the end of reply
        if itinerary:
            reply += "\n\n[View itinerary plan](#scroll-to-top)"
        yield AgentEvent(type="tool_completed", tool_name="write_summary", payload={"message": "Trip summary completed"})
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
        tool_payloads: dict[str, Any],
    ):
        """Standard Anthropic tool-use loop with two rounds of parallel execution.

        Yields AgentEvent objects in real-time as tools start and complete,
        and populates tool_payloads dict in-place.

        Round 1: Claude sees trip brief → proposes base gather tools (weather, hotels,
                 restaurants, experiences, visa) → all executed in parallel →
                 ALL results returned to Claude via tool_result messages.

        Round 2: Claude now sees hotel neighborhood & weather conditions →
                 proposes dependent tools (estimate_budget, get_packing_suggestions)
                 using actual data from Round 1 → executed in parallel →
                 results returned to Claude.

        Falls back to deterministic build_tool_plan if the loop fails entirely.
        """
        tool_payloads.update(dict(payloads_from_previous(previous)))
        has_existing_plan = previous is not None

        # ── Code-level gate: compute which tools are ALLOWED ──────────
        # This enforces selective rerun at the code level, not just via prompt.
        if has_existing_plan and changed_fields:
            allowed_tools: set[str] | None = set()
            for field in changed_fields:
                allowed_tools.update(FIELD_TOOL_DEPENDENCIES.get(field, set()))
            # Downstream dependencies: if weather reruns, packing should too
            if allowed_tools & {"get_weather"}:
                allowed_tools.add("get_packing_suggestions")
            # If hotels rerun, budget should be recalculated
            if allowed_tools & {"get_hotels"}:
                allowed_tools.add("estimate_budget")
        elif has_existing_plan and not changed_fields:
            # Nothing changed — don't allow any tools
            allowed_tools = set()
        else:
            # First plan — allow everything
            allowed_tools = None

        gather_tools = get_claude_tools(names=GATHER_TOOL_NAMES)

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

                # Complete plan_research step on first round
                if _round == 0:
                    yield AgentEvent(type="tool_completed", tool_name="plan_research", payload={"message": "Research plan ready"})

                blocks = normalize_blocks(response.content)
                tool_uses = [b for b in blocks if b.get("type") == "tool_use"]

                # ── Code-level selective rerun gate ───────────────────
                # Even if Claude proposes tools outside the allowed set,
                # we strip them here so only affected tools actually run.
                if allowed_tools is not None:
                    filtered = [tu for tu in tool_uses if tu["name"] in allowed_tools]
                    if len(filtered) < len(tool_uses):
                        skipped = [tu["name"] for tu in tool_uses if tu["name"] not in allowed_tools]
                        logger.info("Selective rerun: skipped tools %s (not in allowed set %s)", skipped, allowed_tools)
                    tool_uses = filtered

                if not tool_uses:
                    break  # Claude is done proposing tools

                # Emit tool_started for the first tool immediately, rest will be staggered
                first_started = False
                for tu in tool_uses:
                    if not first_started:
                        yield AgentEvent(
                            type="tool_started",
                            tool_name=tu["name"],
                            message=f"Running {tu['name']}",
                        )
                        first_started = True

                # Add Claude's full response to message history (required by API)
                loop_messages.append({"role": "assistant", "content": response.content})

                # Execute all proposed tools in parallel, streaming results as they complete
                gather_specs = [
                    (tu["name"], tu.get("input", {}))
                    for tu in tool_uses
                ]

                # Track which tools haven't started yet (for staggered start events)
                pending_starts = {tu["name"] for tu in tool_uses[1:]}  # first already started
                results: dict[str, tuple[str, Any]] = {}

                for name, status, result in execute_tools_streaming(gather_specs):
                    # When a tool completes, emit its completed event
                    results[name] = (status, result)
                    if status == "ok":
                        tool_payloads[name] = result
                        yield AgentEvent(
                            type="tool_completed", tool_name=name, payload=result
                        )

                    # Start the next pending tool (staggered effect)
                    if pending_starts:
                        next_name = pending_starts.pop()
                        yield AgentEvent(
                            type="tool_started",
                            tool_name=next_name,
                            message=f"Running {next_name}",
                        )

                # Emit remaining started events for any tools that haven't been signaled yet
                for remaining in pending_starts:
                    yield AgentEvent(
                        type="tool_started",
                        tool_name=remaining,
                        message=f"Running {remaining}",
                    )
                    if remaining in results and results[remaining][0] == "ok":
                        yield AgentEvent(
                            type="tool_completed", tool_name=remaining, payload=results[remaining][1]
                        )

                # Build tool_result blocks for Claude context
                tool_result_blocks: list[dict[str, Any]] = []
                for tu in tool_uses:
                    name = tu.get("name", "")
                    tool_id = tu.get("id", "")
                    if name in results:
                        status, result = results[name]
                        if status == "ok":
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
                            yield AgentEvent(
                                type="tool_completed", tool_name=name, payload={"error": result}
                            )
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
            logger.exception("Agentic gather loop failed, falling back to deterministic plan")

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
                    yield AgentEvent(
                        type="tool_started", tool_name=name, message=f"Running {name}"
                    )
                fallback_results = execute_tools_parallel(fallback_specs)
                for name, (status, result) in fallback_results.items():
                    if status == "ok":
                        tool_payloads[name] = result
                        yield AgentEvent(
                            type="tool_completed", tool_name=name, payload=result
                        )


def _issue_score(issues: list[dict[str, Any]]) -> int:
    """Sum severity scores across all issues."""
    return sum(int(issue.get("severity", 1)) for issue in issues)
