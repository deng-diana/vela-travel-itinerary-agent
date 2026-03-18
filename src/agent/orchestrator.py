from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from src.agent.prompts import SYSTEM_PROMPT
from src.agent.state import AgentEvent, AgentRunResult, ConversationState
from src.tools.registry import run_tool
from src.tools.schemas import (
    DailyStructureInput,
    DayPlan,
    ExperienceOption,
    HotelOption,
    ItineraryDraft,
    PlanningBrief,
    PlanningBriefPatch,
    RestaurantOption,
    WeatherSummary,
)


REQUIRED_BRIEF_FIELDS = (
    "destination",
    "dates_or_month",
    "trip_length_days",
    "travel_party",
    "budget",
    "priorities",
    "constraints_confirmed",
)


@dataclass
class AgentOrchestrator:
    client: Any
    model: str
    system_prompt: str = SYSTEM_PROMPT
    max_tokens: int = 1800

    def run(self, state: ConversationState, user_message: str) -> AgentRunResult:
        events = list(self.stream(state=state, user_message=user_message))
        final_event = next((event for event in reversed(events) if event.type == "final_response"), None)
        reply = final_event.message if final_event and final_event.message else ""
        itinerary = state.last_itinerary
        payload = final_event.payload if final_event and isinstance(final_event.payload, dict) else {}
        return AgentRunResult(
            reply=reply,
            events=events,
            itinerary=itinerary,
            workspace_ready=bool(payload.get("workspace_ready", state.workspace_ready)),
            missing_fields=list(payload.get("missing_fields", [])),
            planning_brief=state.planning_brief,
        )

    def stream(self, state: ConversationState, user_message: str):
        user_text = user_message.strip()
        response_language = self._detect_response_language(user_text)
        messages = list(state.messages)
        messages.append({"role": "user", "content": user_text})

        yield AgentEvent(type="session", payload={"session_id": state.session_id})

        previous_brief = state.planning_brief.model_copy(deep=True)
        patch = self._extract_brief_patch(previous_brief, user_text, state.last_itinerary)
        brief = self._merge_brief(previous_brief, patch)
        state.planning_brief = brief

        missing_fields = self._missing_fields(brief)
        if missing_fields:
            reply = self._build_clarifying_reply(response_language, brief, missing_fields)
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
                    "missing_fields": missing_fields,
                    "planning_brief": brief.model_dump(mode="json"),
                },
            )
            return

        changed_fields = self._detect_changed_fields(previous_brief, brief, patch)
        state.workspace_ready = True

        preface = self._build_planning_preface(
            response_language,
            changed_fields,
            has_existing_plan=state.last_itinerary is not None,
        )
        if preface:
            yield AgentEvent(type="assistant_message", message=preface)

        tool_plan = self._build_tool_plan(changed_fields, has_existing_plan=state.last_itinerary is not None)
        previous_payloads = self._payloads_from_previous(state.last_itinerary)
        tool_inputs: dict[str, dict[str, Any]] = {}
        tool_payloads: dict[str, Any] = dict(previous_payloads)

        gather_specs: list[tuple[str, dict[str, Any]]] = []
        for tool_name in tool_plan["gather_tools"]:
            tool_input = self._build_tool_input(tool_name, brief, state.last_itinerary)
            if not tool_input:
                continue
            tool_inputs[tool_name] = tool_input
            gather_specs.append((tool_name, tool_input))
            yield AgentEvent(type="tool_started", tool_name=tool_name, message=f"Running {tool_name}")

        if gather_specs:
            with ThreadPoolExecutor(max_workers=min(4, len(gather_specs))) as executor:
                future_map = {executor.submit(run_tool, tool_name, tool_input): (tool_name, tool_input) for tool_name, tool_input in gather_specs}
                for future in as_completed(future_map):
                    tool_name, _tool_input = future_map[future]
                    try:
                        tool_output = future.result()
                        tool_payloads[tool_name] = tool_output
                        yield AgentEvent(type="tool_completed", tool_name=tool_name, payload=tool_output)
                    except Exception as exc:  # pragma: no cover - defensive path
                        yield AgentEvent(type="tool_completed", tool_name=tool_name, payload={"error": str(exc)})

        planning_context = self._prepare_candidate_context(brief, tool_payloads, state.last_itinerary)
        daily_input = self._build_daily_structure_input(
            brief,
            tool_payloads,
            state.last_itinerary,
            patch.day_swap_request,
            planning_context,
        )
        tool_inputs["get_daily_structure"] = daily_input.model_dump(mode="json")
        yield AgentEvent(type="tool_started", tool_name="get_daily_structure", message="Running get_daily_structure")
        generated_days = self._generate_daily_structure_with_claude(
            response_language=response_language,
            brief=brief,
            daily_input=daily_input,
            planning_context=planning_context,
            weather_payload=tool_payloads.get("get_weather"),
        )
        if generated_days:
            day_output = [day.model_dump(mode="json") for day in generated_days]
        else:
            day_output = run_tool("get_daily_structure", tool_inputs["get_daily_structure"])
        tool_payloads["get_daily_structure"] = day_output
        yield AgentEvent(type="tool_completed", tool_name="get_daily_structure", payload=day_output)

        itinerary = self._build_itinerary(tool_inputs, tool_payloads, state.last_itinerary, planning_context)
        if itinerary and patch.day_swap_request:
            itinerary = self._apply_day_swap_request(itinerary, patch.day_swap_request)
        if itinerary:
            verification = self._verify_itinerary_quality(brief, itinerary, response_language)
            if not verification["approved"]:
                yield AgentEvent(
                    type="assistant_message",
                    message=(
                        "我在把这版行程再收紧一点，让它更有节奏也更少重复。"
                        if response_language == "zh"
                        else "I am tightening this draft so it feels more coherent, less repetitive, and more useful."
                    ),
                )
                repaired_days = self._repair_daily_structure_with_claude(
                    response_language=response_language,
                    brief=brief,
                    itinerary=itinerary,
                    planning_context=planning_context,
                    issues=verification["issues"],
                )
                if repaired_days:
                    repaired_days = self._align_days_to_candidates(
                        repaired_days,
                        planning_context["selected_hotel"],
                        planning_context["ranked_restaurants"],
                        planning_context["ranked_experiences"],
                    )
                    repaired_itinerary = itinerary.model_copy(
                        update={
                            "days": self._enrich_days(
                                repaired_days,
                                planning_context["selected_hotel"],
                                planning_context["restaurants"],
                                planning_context["experiences"],
                            )
                        }
                    )
                    repaired_verification = self._verify_itinerary_quality(brief, repaired_itinerary, response_language)
                    if self._issue_score(repaired_verification["issues"]) <= self._issue_score(verification["issues"]):
                        itinerary = repaired_itinerary
        if itinerary:
            itinerary = self._polish_itinerary_days(brief, itinerary)

        raw_reply = self._compose_final_reply(response_language, brief, itinerary, changed_fields)
        reply = self._compact_reply(response_language, raw_reply, itinerary)
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

    def _extract_brief_patch(
        self,
        existing_brief: PlanningBrief,
        user_message: str,
        current_itinerary: ItineraryDraft | None,
    ) -> PlanningBriefPatch:
        prompt = (
            "You extract a structured travel-planning patch from the latest user message.\n"
            "Return JSON only. Do not include markdown or commentary.\n"
            "Only fill fields that the user clearly adds, confirms, or changes. Leave all other fields null.\n"
            "Schema keys: destination, dates_or_month, trip_length_days, travel_party, budget, priorities, "
            "constraints, constraints_confirmed, style_notes, pace, hotel_preference, neighborhood_preference, "
            "dietary_preferences, must_do, must_avoid, day_swap_request, notes.\n"
            "Rules:\n"
            "- Map budget to one of: budget, mid, luxury.\n"
            "- Map pace to one of: slow, balanced, packed.\n"
            "- priorities/style_notes/must_do/must_avoid/dietary_preferences/constraints are arrays when present.\n"
            "- Set constraints_confirmed=true if the user explicitly says there are no special restrictions.\n"
            "- If the user wants the current plan changed, capture the qualitative change in style_notes or notes.\n"
            "- If the user asks to swap or reorder days, put a short instruction in day_swap_request.\n"
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=600,
            system=prompt,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "existing_brief": existing_brief.model_dump(mode="json"),
                            "current_itinerary_summary": current_itinerary.summary if current_itinerary else None,
                            "latest_user_message": user_message,
                        },
                        ensure_ascii=False,
                    ),
                }
            ],
        )
        text = self._extract_text(self._normalize_blocks(response.content))
        payload = self._parse_json_block(text)
        patch = PlanningBriefPatch.model_validate(payload)
        return self._supplement_patch_from_text(existing_brief, patch, user_message)

    def _supplement_patch_from_text(
        self,
        existing_brief: PlanningBrief,
        patch: PlanningBriefPatch,
        user_message: str,
    ) -> PlanningBriefPatch:
        patch_data = patch.model_dump(exclude_none=True)
        normalized_text = user_message.strip()
        lower_text = normalized_text.lower()

        if not existing_brief.trip_length_days and patch.trip_length_days is None:
            trip_length = self._extract_trip_length(normalized_text)
            if trip_length:
                patch_data["trip_length_days"] = trip_length

        if not existing_brief.travel_party and patch.travel_party is None:
            travel_party = self._extract_travel_party(lower_text)
            if travel_party:
                patch_data["travel_party"] = travel_party

        if not existing_brief.destination and patch.destination is None:
            destination = self._extract_destination(normalized_text)
            if destination:
                patch_data["destination"] = destination

        if not existing_brief.dates_or_month and patch.dates_or_month is None:
            dates_or_month = self._extract_dates_or_month(normalized_text)
            if dates_or_month:
                patch_data["dates_or_month"] = dates_or_month

        if not existing_brief.budget and patch.budget is None:
            budget = self._extract_budget(lower_text)
            if budget:
                patch_data["budget"] = budget

        inferred_constraints = self._extract_constraints_from_text(normalized_text, lower_text)
        if inferred_constraints:
            existing_constraints = list(patch_data.get("constraints") or [])
            for constraint in inferred_constraints:
                if constraint not in existing_constraints:
                    existing_constraints.append(constraint)
            patch_data["constraints"] = existing_constraints

        if patch.pace is None:
            inferred_pace = self._extract_pace_from_text(lower_text)
            if inferred_pace:
                patch_data["pace"] = inferred_pace

        if not existing_brief.constraints and not existing_brief.constraints_confirmed:
            if patch.constraints is None and patch.constraints_confirmed is None:
                if any(token in lower_text for token in ("no special restrictions", "no restrictions", "没有特别限制", "没有限制")):
                    patch_data["constraints_confirmed"] = True

        return PlanningBriefPatch.model_validate(patch_data)

    def _parse_json_block(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned)

    def _merge_brief(self, existing: PlanningBrief, patch: PlanningBriefPatch) -> PlanningBrief:
        merged = existing.model_dump(mode="python")
        patch_data = patch.model_dump(exclude_none=True)
        for key, value in patch_data.items():
            merged[key] = value
        return PlanningBrief.model_validate(merged)

    def _missing_fields(self, brief: PlanningBrief) -> list[str]:
        missing: list[str] = []
        if not brief.destination:
            missing.append("destination")
        if not brief.dates_or_month:
            missing.append("dates_or_month")
        if not brief.trip_length_days:
            missing.append("trip_length_days")
        if not brief.travel_party:
            missing.append("travel_party")
        if not brief.budget:
            missing.append("budget")
        if not brief.priorities:
            missing.append("priorities")
        if not brief.constraints_confirmed and not brief.constraints and not brief.dietary_preferences:
            missing.append("constraints")
        return missing

    def _build_clarifying_reply(self, response_language: str, brief: PlanningBrief, missing_fields: list[str]) -> str:
        generated = self._generate_clarifying_reply_with_claude(response_language, brief, missing_fields)
        if generated:
            return generated
        if response_language == "zh":
            return self._build_clarifying_reply_zh(brief, missing_fields)
        return self._build_clarifying_reply_en(brief, missing_fields)

    def _generate_clarifying_reply_with_claude(
        self,
        response_language: str,
        brief: PlanningBrief,
        missing_fields: list[str],
    ) -> str | None:
        field_guidance = {
            "destination": "Ask which city or destination they want to go to.",
            "dates_or_month": "Ask when they are going. Give examples like next Friday, late January, or mid April.",
            "trip_length_days": "Ask how many days they have for the trip.",
            "travel_party": "Ask whether this is solo, couple, friends, or family travel.",
            "budget": "Ask whether the budget is budget, mid-range, or premium, or invite a rough amount.",
            "priorities": "Ask for the top 2 to 3 goals, such as food, art, classic landmarks, shopping, nightlife, or hidden gems.",
            "constraints": "Ask whether there are any constraints or things to avoid, such as dietary restrictions, mobility needs, long queues, or overly packed days.",
        }
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                system=(
                    "You write a warm, concise clarifying message for a travel-planning assistant.\n"
                    "Reply in plain text only.\n"
                    f"Write in {'Chinese' if response_language == 'zh' else 'English'}.\n"
                    "Rules:\n"
                    "- Ask only for the fields listed as missing.\n"
                    "- Do not repeat information the user already gave.\n"
                    "- Ask at most 4 bullet points.\n"
                    "- Each bullet must be concrete and easy to answer.\n"
                    "- Prefer examples or simple choices over abstract wording.\n"
                    "- Sound warm, calm, and helpful.\n"
                    "- End with one short sentence saying the user can answer in order or just reply with what they know.\n"
                ),
                messages=[
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "known_brief": brief.model_dump(mode="json"),
                                "missing_fields": missing_fields,
                                "field_guidance": {field: field_guidance[field] for field in missing_fields if field in field_guidance},
                            },
                            ensure_ascii=False,
                        ),
                    }
                ],
            )
            text = self._extract_text(self._normalize_blocks(response.content)).strip()
            return text or None
        except Exception:  # pragma: no cover - graceful fallback
            return None

    def _build_clarifying_reply_zh(self, brief: PlanningBrief, missing_fields: list[str]) -> str:
        questions: list[str] = []

        if "destination" in missing_fields:
            questions.append("先告诉我要去哪个城市。比如“巴黎”或“东京”。")
        if "dates_or_month" in missing_fields:
            questions.append("你准备什么时候去？比如“下周五”、“1月底”或“4月中旬”。")
        if "trip_length_days" in missing_fields:
            questions.append("这次准备玩几天？比如“3天”或“5天”。")
        if "travel_party" in missing_fields:
            questions.append("这次是一个人、情侣、朋友还是家庭出行？这会直接影响节奏和住宿选择。")
        if "budget" in missing_fields:
            questions.append("预算更接近省钱、适中，还是愿意多花一点换体验？也可以直接说一个大概金额。")
        if "priorities" in missing_fields:
            questions.append("这趟最重要的 2 到 3 个目标是什么？比如美食、艺术、经典景点、购物、夜生活、hidden gems。")
        if "constraints" in missing_fields:
            questions.append("有没有必须避开的东西或限制？比如饮食限制、太赶的行程、很多排队、带老人小孩。没有的话直接说“没有特别限制”。")

        opener = "我想先把这趟旅行的方向抓准一点，再帮你开始排第一版行程。还差几条很关键的信息："
        closing = "你可以直接按顺序回复，也可以只回答你现在最确定的部分。"
        return opener + "\n\n" + "\n".join(f"- {question}" for question in questions[:4]) + "\n\n" + closing

    def _build_clarifying_reply_en(self, brief: PlanningBrief, missing_fields: list[str]) -> str:
        questions: list[str] = []

        if "destination" in missing_fields:
            questions.append('First, tell me which city you want to go to. For example: "Paris" or "Tokyo."')
        if "dates_or_month" in missing_fields:
            questions.append('When are you going? For example: "next Friday," "late January," or "mid April."')
        if "trip_length_days" in missing_fields:
            questions.append('How many days do you have for this trip? For example: "3 days" or "5 days."')
        if "travel_party" in missing_fields:
            questions.append("Who is this trip for: solo, couple, friends, or family? That changes pacing and hotel choices.")
        if "budget" in missing_fields:
            questions.append("Is your budget closer to budget, mid-range, or more premium? You can also give me a rough amount.")
        if "priorities" in missing_fields:
            questions.append("What are the top 2 to 3 goals for this trip? For example: food, art, classic landmarks, shopping, nightlife, or hidden gems.")
        if "constraints" in missing_fields:
            questions.append("Do you have anything I should avoid or plan around, like dietary restrictions, very packed days, long queues, or mobility needs? If not, just say \"no special restrictions.\"")

        opener = "I want to get the shape of this trip right before I build the first draft. I still need a few key details:"
        closing = "You can answer in order, or just reply with the parts you already know."
        return opener + "\n\n" + "\n".join(f"- {question}" for question in questions[:4]) + "\n\n" + closing

    def _detect_changed_fields(
        self,
        previous: PlanningBrief,
        current: PlanningBrief,
        patch: PlanningBriefPatch,
    ) -> set[str]:
        changed = set(patch.model_dump(exclude_none=True).keys())
        comparable_fields = (
            "destination",
            "dates_or_month",
            "trip_length_days",
            "travel_party",
            "budget",
            "priorities",
            "constraints",
            "constraints_confirmed",
            "style_notes",
            "pace",
            "hotel_preference",
            "neighborhood_preference",
            "dietary_preferences",
            "must_do",
            "must_avoid",
        )
        for field in comparable_fields:
            if getattr(previous, field) != getattr(current, field):
                changed.add(field)
        return changed

    def _build_planning_preface(self, response_language: str, changed_fields: set[str], has_existing_plan: bool) -> str:
        if response_language == "zh":
            return self._build_planning_preface_zh(changed_fields, has_existing_plan)
        return self._build_planning_preface_en(changed_fields, has_existing_plan)

    def _build_planning_preface_zh(self, changed_fields: set[str], has_existing_plan: bool) -> str:
        if not has_existing_plan:
            return "信息已经够了。我先并行查天气、住宿、餐厅和体验，再把它们编成一版可执行的行程。"
        if not changed_fields:
            return "我会基于当前计划做一次轻量整理，不会把你的行程整份推翻。"
        if changed_fields == {"pace"}:
            return "我先按新的节奏调整现有行程，不去重查所有内容。"
        return "我会在当前计划上做针对性调整，只重算受影响的部分。"

    def _build_planning_preface_en(self, changed_fields: set[str], has_existing_plan: bool) -> str:
        if not has_existing_plan:
            return "I have enough to start. I will check weather, stays, dining, and experiences in parallel, then turn them into a usable plan."
        if not changed_fields:
            return "I will lightly refine the current plan without rebuilding it from scratch."
        if changed_fields == {"pace"}:
            return "I will adjust the pacing first and keep the rest of the plan as intact as possible."
        return "I will update the current plan selectively and only recalculate the parts your change affects."

    def _build_tool_plan(self, changed_fields: set[str], has_existing_plan: bool) -> dict[str, Any]:
        if not has_existing_plan:
            return {"gather_tools": ["get_weather", "get_hotels", "get_restaurants", "get_experiences"]}

        gather_tools: set[str] = set()

        if changed_fields & {"destination", "dates_or_month"}:
            gather_tools.update({"get_weather", "get_hotels", "get_restaurants", "get_experiences"})
        if changed_fields & {"trip_length_days", "travel_party"}:
            gather_tools.update({"get_hotels", "get_restaurants", "get_experiences"})
        if changed_fields & {"budget"}:
            gather_tools.update({"get_hotels", "get_restaurants", "get_experiences"})
        if changed_fields & {"hotel_preference", "neighborhood_preference"}:
            gather_tools.add("get_hotels")
        if changed_fields & {"priorities", "must_do", "must_avoid", "dietary_preferences", "style_notes", "notes"}:
            gather_tools.update({"get_restaurants", "get_experiences"})
        if changed_fields & {"pace"}:
            gather_tools.add("get_experiences")

        return {"gather_tools": sorted(gather_tools)}

    def _build_tool_input(self, tool_name: str, brief: PlanningBrief, previous: ItineraryDraft | None) -> dict[str, Any] | None:
        if tool_name == "get_weather":
            return {
                "destination": brief.destination,
                "month": brief.dates_or_month,
            }
        if tool_name == "get_hotels":
            return {
                "destination": brief.destination,
                "budget": brief.budget or "mid",
                "preferred_neighborhood": brief.neighborhood_preference,
                "accommodation_type": brief.hotel_preference,
            }
        if tool_name == "get_restaurants":
            neighborhoods = [brief.neighborhood_preference] if brief.neighborhood_preference else []
            return {
                "destination": brief.destination,
                "neighborhoods": neighborhoods,
                "interests": brief.priorities + brief.must_do + brief.style_notes,
                "budget": brief.budget or "mid",
                "dietary_preferences": brief.dietary_preferences,
            }
        if tool_name == "get_experiences":
            return {
                "destination": brief.destination,
                "interests": brief.priorities + brief.must_do + brief.style_notes,
                "travel_party": brief.travel_party,
                "pace": brief.pace or "balanced",
            }
        return None

    def _payloads_from_previous(self, itinerary: ItineraryDraft | None) -> dict[str, Any]:
        if not itinerary:
            return {}

        payloads: dict[str, Any] = {}
        if itinerary.weather:
            payloads["get_weather"] = itinerary.weather.model_dump(mode="json")
        if itinerary.hotels:
            payloads["get_hotels"] = [hotel.model_dump(mode="json") for hotel in itinerary.hotels]
        if itinerary.restaurants:
            payloads["get_restaurants"] = [restaurant.model_dump(mode="json") for restaurant in itinerary.restaurants]
        if itinerary.experiences:
            payloads["get_experiences"] = [experience.model_dump(mode="json") for experience in itinerary.experiences]
        if itinerary.days:
            payloads["get_daily_structure"] = [day.model_dump(mode="json") for day in itinerary.days]
        return payloads

    def _build_daily_structure_input(
        self,
        brief: PlanningBrief,
        tool_payloads: dict[str, Any],
        previous: ItineraryDraft | None,
        day_swap_request: str | None = None,
        planning_context: dict[str, Any] | None = None,
    ) -> DailyStructureInput:
        context = planning_context or self._prepare_candidate_context(brief, tool_payloads, previous)
        selected_hotel = context["selected_hotel"]
        ranked_restaurants = context["ranked_restaurants"]
        ranked_experiences = context["ranked_experiences"]
        restaurant_names = [restaurant.name for restaurant in ranked_restaurants[: max((brief.trip_length_days or 1) + 2, 5)]]
        experience_names = [experience.name for experience in ranked_experiences[: max(brief.trip_length_days or 1, 4)]]

        return DailyStructureInput(
            destination=brief.destination or "",
            month=brief.dates_or_month or "",
            trip_length_days=brief.trip_length_days or 1,
            travel_party=brief.travel_party,
            budget=brief.budget or "mid",
            interests=brief.priorities + brief.style_notes,
            hotel_name=selected_hotel.name if selected_hotel else "Selected stay",
            restaurant_names=restaurant_names,
            experience_names=experience_names,
            pace=brief.pace or "balanced",
            style_notes=brief.style_notes,
            must_do=brief.must_do,
            must_avoid=brief.must_avoid,
            day_swap_request=day_swap_request,
        )

    def _prepare_candidate_context(
        self,
        brief: PlanningBrief,
        tool_payloads: dict[str, Any],
        previous: ItineraryDraft | None,
    ) -> dict[str, Any]:
        hotels = [HotelOption.model_validate(item) for item in tool_payloads.get("get_hotels", [])]
        if not hotels and previous:
            hotels = previous.hotels

        restaurants = [RestaurantOption.model_validate(item) for item in tool_payloads.get("get_restaurants", [])]
        if not restaurants and previous:
            restaurants = previous.restaurants

        experiences = [ExperienceOption.model_validate(item) for item in tool_payloads.get("get_experiences", [])]
        if not experiences and previous:
            experiences = previous.experiences

        ranked_hotels = sorted(hotels, key=lambda hotel: self._score_hotel(hotel, brief), reverse=True)
        ranked_restaurants = sorted(restaurants, key=lambda restaurant: self._score_restaurant(restaurant, brief), reverse=True)
        ranked_experiences = sorted(experiences, key=lambda experience: self._score_experience(experience, brief), reverse=True)

        selected_hotel = ranked_hotels[0] if ranked_hotels else (previous.selected_hotel if previous else None)

        return {
            "hotels": hotels,
            "restaurants": restaurants,
            "experiences": experiences,
            "ranked_hotels": ranked_hotels,
            "ranked_restaurants": ranked_restaurants,
            "ranked_experiences": ranked_experiences,
            "selected_hotel": selected_hotel,
        }

    def _score_hotel(self, hotel: HotelOption, brief: PlanningBrief) -> int:
        score = 0
        text = self._normalize_text(" ".join([hotel.name, hotel.neighborhood, hotel.short_description, " ".join(hotel.key_highlights)]))

        if brief.neighborhood_preference and self._normalize_text(brief.neighborhood_preference) in text:
            score += 4
        if brief.hotel_preference and self._normalize_text(brief.hotel_preference) in text:
            score += 4
        for note in brief.style_notes:
            if self._normalize_text(note) in text:
                score += 2
        for avoid in brief.must_avoid:
            if self._normalize_text(avoid) in text:
                score -= 6
        score += self._rating_score(hotel.rating, hotel.user_rating_count)
        if brief.budget == hotel.category:
            score += 3
        if hotel.photo_name:
            score += 1
        return score

    def _score_restaurant(self, restaurant: RestaurantOption, brief: PlanningBrief) -> int:
        score = 0
        text = self._normalize_text(
            " ".join(
                [
                    restaurant.name,
                    restaurant.cuisine,
                    restaurant.neighborhood,
                    restaurant.why_it_fits,
                    restaurant.must_order_dish or "",
                ]
            )
        )

        if brief.neighborhood_preference and self._normalize_text(brief.neighborhood_preference) in text:
            score += 3
        for token in brief.priorities + brief.style_notes + brief.must_do + brief.dietary_preferences:
            if self._normalize_text(token) in text:
                score += 2
        for avoid in brief.must_avoid:
            if self._normalize_text(avoid) in text:
                score -= 6
        score += self._rating_score(restaurant.rating, restaurant.user_rating_count)
        score += self._hidden_gem_score(
            title=restaurant.name,
            category=restaurant.cuisine,
            neighborhood=restaurant.neighborhood,
            rating_count=restaurant.user_rating_count,
            brief=brief,
        )
        if restaurant.photo_name:
            score += 1
        return score

    def _score_experience(self, experience: ExperienceOption, brief: PlanningBrief) -> int:
        score = 0
        text = self._normalize_text(" ".join([experience.name, experience.category, experience.neighborhood, experience.why_it_fits]))

        if brief.neighborhood_preference and self._normalize_text(brief.neighborhood_preference) in text:
            score += 3
        for token in brief.priorities + brief.style_notes + brief.must_do:
            if self._normalize_text(token) in text:
                score += 2
        for avoid in brief.must_avoid:
            if self._normalize_text(avoid) in text:
                score -= 6
        score += self._rating_score(experience.rating, experience.user_rating_count)
        score += self._hidden_gem_score(
            title=experience.name,
            category=experience.category,
            neighborhood=experience.neighborhood,
            rating_count=experience.user_rating_count,
            brief=brief,
        )
        if brief.pace and experience.best_time.lower() == ("morning" if brief.pace == "packed" else "afternoon"):
            score += 1
        if experience.photo_name:
            score += 1
        return score

    def _normalize_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^\w\s]+", " ", value.lower())).strip()

    def _rating_score(self, rating: float | None, rating_count: int | None) -> int:
        score = 0
        if rating is not None:
            score += int(round((rating - 4.0) * 4))
        if rating_count:
            if rating_count >= 300:
                score += 2
            elif rating_count >= 100:
                score += 1
        return score

    def _hidden_gem_score(
        self,
        title: str,
        category: str,
        neighborhood: str,
        rating_count: int | None,
        brief: PlanningBrief,
    ) -> int:
        preference_text = " ".join(brief.priorities + brief.style_notes + brief.must_do).lower()
        if not any(token in preference_text for token in ("hidden", "local", "gem", "independent", "quiet", "neighborhood")):
            return 0

        score = 0
        combined = f"{title} {category} {neighborhood}".lower()
        if any(token in combined for token in ("independent", "bookstore", "gallery", "kissaten", "market", "backstreet", "local", "quiet", "neighborhood", "garden")):
            score += 3
        if rating_count:
            if rating_count < 400:
                score += 2
            elif rating_count > 5000:
                score -= 2
        return score

    def _generate_daily_structure_with_claude(
        self,
        response_language: str,
        brief: PlanningBrief,
        daily_input: DailyStructureInput,
        planning_context: dict[str, Any],
        weather_payload: Any,
    ) -> list[DayPlan] | None:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1800,
                system=(
                    f"{self.system_prompt}\n\n"
                    "You are the planning brain for Vela.\n"
                    "Use the provided venues and trip brief to create a strong, structured multi-day itinerary.\n"
                    "Return JSON only with this shape: "
                    '{"days":[{"day_number":1,"theme":"...","summary":"...","items":[{"time_label":"Morning","kind":"experience","title":"...","neighborhood":"...","description":"..."}]}]}.\n'
                    "Rules:\n"
                    "- Use only venues provided in the candidate lists.\n"
                    "- Minimize repeats. Do not reuse the same restaurant or experience unless there are no strong alternatives.\n"
                    "- Keep each day geographically sensible.\n"
                    "- Day 1 should be lighter and include the hotel plus one nearby meal and a soft evening idea.\n"
                    "- Full days should include Morning, Lunch, Afternoon, and Dinner. Evening is optional.\n"
                    "- Morning and Afternoon should normally be experiences, walks, markets, museums, or neighborhood exploration.\n"
                    "- Lunch and Dinner must be restaurants from the restaurant shortlist.\n"
                    "- Never use a landmark, museum, or attraction as Lunch or Dinner.\n"
                    "- Prefer concrete actions over vague notes. The user should know what to do in each time block.\n"
                    "- Use the hotel's neighborhood as a base for Day 1 and one or more nearby anchors.\n"
                    "- If the brief emphasizes hidden gems or local feel, include at least one less-obvious venue or quieter neighborhood choice.\n"
                    "- Respect must_do and must_avoid.\n"
                    "- Do not repeat the same restaurant or experience across multiple days unless there are no strong alternatives left.\n"
                    f"- Write in {'Chinese' if response_language == 'zh' else 'English'}.\n"
                ),
                messages=[
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "planning_brief": brief.model_dump(mode="json"),
                                "weather": weather_payload,
                                "selected_hotel": planning_context["selected_hotel"].model_dump(mode="json") if planning_context["selected_hotel"] else None,
                                "candidate_hotels": [self._hotel_brief_for_planning(hotel) for hotel in planning_context["ranked_hotels"][:3]],
                                "candidate_restaurants": [self._restaurant_brief_for_planning(restaurant, brief) for restaurant in planning_context["ranked_restaurants"][:10]],
                                "candidate_experiences": [self._experience_brief_for_planning(experience, brief) for experience in planning_context["ranked_experiences"][:10]],
                                "restaurant_names": [restaurant.name for restaurant in planning_context["ranked_restaurants"][:10]],
                                "experience_names": [experience.name for experience in planning_context["ranked_experiences"][:10]],
                                "daily_input": daily_input.model_dump(mode="json"),
                            },
                            ensure_ascii=False,
                        ),
                    }
                ],
            )
            text = self._extract_text(self._normalize_blocks(response.content))
            payload = self._parse_json_block(text)
            days = [DayPlan.model_validate(day) for day in payload.get("days", [])]
            return days or None
        except Exception:  # pragma: no cover - graceful fallback
            return None

    def _hotel_brief_for_planning(self, hotel: HotelOption) -> dict[str, Any]:
        return {
            "name": hotel.name,
            "neighborhood": hotel.neighborhood,
            "category": hotel.category,
            "nightly_rate_usd": hotel.nightly_rate_usd,
            "rating": hotel.rating,
            "user_rating_count": hotel.user_rating_count,
            "highlights": hotel.key_highlights,
            "description": hotel.short_description,
        }

    def _restaurant_brief_for_planning(self, restaurant: RestaurantOption, brief: PlanningBrief) -> dict[str, Any]:
        return {
            "name": restaurant.name,
            "cuisine": restaurant.cuisine,
            "neighborhood": restaurant.neighborhood,
            "price_range": restaurant.price_range,
            "rating": restaurant.rating,
            "user_rating_count": restaurant.user_rating_count,
            "why_it_fits": restaurant.why_it_fits,
            "hidden_gem_bias": self._hidden_gem_score(
                restaurant.name,
                restaurant.cuisine,
                restaurant.neighborhood,
                restaurant.user_rating_count,
                brief,
            ),
        }

    def _experience_brief_for_planning(self, experience: ExperienceOption, brief: PlanningBrief) -> dict[str, Any]:
        return {
            "name": experience.name,
            "category": experience.category,
            "neighborhood": experience.neighborhood,
            "duration_hours": experience.duration_hours,
            "estimated_cost_usd": experience.estimated_cost_usd,
            "best_time": experience.best_time,
            "rating": experience.rating,
            "user_rating_count": experience.user_rating_count,
            "why_it_fits": experience.why_it_fits,
            "hidden_gem_bias": self._hidden_gem_score(
                experience.name,
                experience.category,
                experience.neighborhood,
                experience.user_rating_count,
                brief,
            ),
        }

    def _verify_itinerary_quality(
        self,
        brief: PlanningBrief,
        itinerary: ItineraryDraft,
        response_language: str,
    ) -> dict[str, Any]:
        code_issues = self._code_quality_findings(brief, itinerary)
        llm_issues: list[dict[str, Any]] = []

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=700,
                system=(
                    "You verify itinerary quality against a rubric.\n"
                    "Return JSON only with shape: "
                    '{"approved":true,"issues":[{"code":"...","severity":1,"message":"...","repair_hint":"..."}]}.\n'
                    "Severity: 1=minor, 2=meaningful, 3=serious.\n"
                    "Rubric:\n"
                    "- coverage: each day should feel complete enough to use\n"
                    "- diversity: avoid repeating the same venues too often\n"
                    "- geography: keep each day reasonably clustered\n"
                    "- pace: match the requested pace\n"
                    "- interest_fit: the plan should clearly reflect the traveller's goals\n"
                    "- constraints_fit: avoid must_avoid and respect constraints\n"
                    "- memorability: include at least one or two notable anchors\n"
                    f"- Write issue messages in {'Chinese' if response_language == 'zh' else 'English'}.\n"
                ),
                messages=[
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "planning_brief": brief.model_dump(mode="json"),
                                "code_findings": code_issues,
                                "itinerary": itinerary.model_dump(mode="json"),
                            },
                            ensure_ascii=False,
                        ),
                    }
                ],
            )
            text = self._extract_text(self._normalize_blocks(response.content))
            payload = self._parse_json_block(text)
            llm_issues = [self._normalize_issue(issue) for issue in payload.get("issues", [])]
        except Exception:  # pragma: no cover - graceful fallback
            llm_issues = []

        merged_issues = code_issues + llm_issues
        return {
            "approved": self._issue_score(merged_issues) <= 2,
            "issues": merged_issues,
        }

    def _code_quality_findings(self, brief: PlanningBrief, itinerary: ItineraryDraft) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        seen_titles: dict[str, int] = {}

        for day in itinerary.days:
            real_items = [item for item in day.items if item.kind != "note"]
            unique_neighborhoods = {item.neighborhood for item in real_items if item.neighborhood}
            restaurants = [item for item in real_items if item.kind == "restaurant"]
            experiences = [item for item in real_items if item.kind == "experience"]
            labels = {item.time_label.lower() for item in real_items}

            minimum_items = 2 if day.day_number == 1 else 3
            if len(real_items) < minimum_items:
                issues.append(
                    {
                        "code": f"coverage_day_{day.day_number}",
                        "severity": 2,
                        "message": f"Day {day.day_number} feels too thin to be genuinely useful.",
                        "repair_hint": "Add another meaningful stop or meal anchor to make the day feel complete.",
                    }
                )

            if len(unique_neighborhoods) > 3:
                issues.append(
                    {
                        "code": f"geography_day_{day.day_number}",
                        "severity": 2,
                        "message": f"Day {day.day_number} spans too many neighborhoods and may feel scattered.",
                        "repair_hint": "Tighten the route so the day clusters around one or two areas.",
                    }
                )

            if day.day_number > 1 and not restaurants:
                issues.append(
                    {
                        "code": f"dining_day_{day.day_number}",
                        "severity": 1,
                        "message": f"Day {day.day_number} lacks a clear dining anchor.",
                        "repair_hint": "Add at least one restaurant stop that fits the day's area and mood.",
                    }
                )

            if day.day_number > 1 and not experiences:
                issues.append(
                    {
                        "code": f"experience_day_{day.day_number}",
                        "severity": 1,
                        "message": f"Day {day.day_number} lacks a clear experiential anchor.",
                        "repair_hint": "Add a museum, walk, neighborhood activity, or other notable experience.",
                    }
                )

            if day.day_number > 1 and "morning" not in labels:
                issues.append(
                    {
                        "code": f"morning_day_{day.day_number}",
                        "severity": 2,
                        "message": f"Day {day.day_number} is missing a clear morning plan.",
                        "repair_hint": "Add a strong morning anchor so the day can start with intention.",
                    }
                )

            if day.day_number > 1 and "lunch" not in labels:
                issues.append(
                    {
                        "code": f"lunch_day_{day.day_number}",
                        "severity": 1,
                        "message": f"Day {day.day_number} is missing a lunch stop.",
                        "repair_hint": "Add a lunch anchor that fits the neighborhood flow.",
                    }
                )

            if day.day_number > 1 and "afternoon" not in labels:
                issues.append(
                    {
                        "code": f"afternoon_day_{day.day_number}",
                        "severity": 1,
                        "message": f"Day {day.day_number} is missing a clear afternoon anchor.",
                        "repair_hint": "Add an afternoon experience or neighborhood activity that advances the day.",
                    }
                )

            if day.day_number > 1 and "dinner" not in labels:
                issues.append(
                    {
                        "code": f"dinner_day_{day.day_number}",
                        "severity": 1,
                        "message": f"Day {day.day_number} is missing a dinner plan.",
                        "repair_hint": "Add a dinner stop that fits the area and keeps the day feeling complete.",
                    }
                )

            for item in restaurants:
                if not self._matches_restaurant_candidate(item.title, itinerary.restaurants):
                    issues.append(
                        {
                            "code": f"invalid_restaurant_{day.day_number}_{self._normalize_text(item.title)}",
                            "severity": 3,
                            "message": f'"{item.title}" is being used as a restaurant, but it is not in the restaurant shortlist.',
                            "repair_hint": "Replace it with an actual restaurant from the shortlisted dining options.",
                        }
                    )

            for item in experiences:
                if not self._matches_experience_candidate(item.title, itinerary.experiences):
                    issues.append(
                        {
                            "code": f"invalid_experience_{day.day_number}_{self._normalize_text(item.title)}",
                            "severity": 2,
                            "message": f'"{item.title}" is being used as an experience, but it is not in the experience shortlist.',
                            "repair_hint": "Replace it with a real experience from the shortlisted options.",
                        }
                    )

            if (brief.pace or "balanced") == "slow" and len(real_items) > 4:
                issues.append(
                    {
                        "code": f"pace_day_{day.day_number}",
                        "severity": 1,
                        "message": f"Day {day.day_number} looks too packed for a slow-paced trip.",
                        "repair_hint": "Remove one stop or keep more breathing room.",
                    }
                )

            if (brief.pace or "balanced") == "packed" and len(real_items) < 4 and day.day_number > 1:
                issues.append(
                    {
                        "code": f"pace_day_{day.day_number}",
                        "severity": 1,
                        "message": f"Day {day.day_number} may feel too light for a packed trip.",
                        "repair_hint": "Add one more worthwhile anchor if it still feels geographically sensible.",
                    }
                )

            for item in real_items:
                key = item.title.lower()
                seen_titles[key] = seen_titles.get(key, 0) + 1

        for title, count in seen_titles.items():
            if count > 1:
                issues.append(
                    {
                        "code": f"duplicate_{title}",
                        "severity": 2,
                        "message": f'"{title}" appears too many times across the trip.',
                        "repair_hint": "Replace repeated venues with other strong options from the shortlist.",
                    }
                )

        if any(token in " ".join(brief.priorities + brief.style_notes).lower() for token in ("hidden", "local", "gem")):
            joined_text = " ".join(
                [day.theme + " " + day.summary + " " + " ".join(item.description for item in day.items) for day in itinerary.days]
            ).lower()
            if not any(token in joined_text for token in ("hidden", "local", "quiet", "independent", "neighborhood")):
                issues.append(
                    {
                        "code": "hidden_gem_signal",
                        "severity": 2,
                        "message": "The itinerary does not clearly deliver on the hidden-gem or local feel the traveller asked for.",
                        "repair_hint": "Swap at least one mainstream stop for a more local or less obvious choice.",
                    }
                )

        if len(itinerary.days) >= 3:
            used_neighborhood_sets = [
                tuple(sorted({item.neighborhood or "" for item in day.items if item.kind != "note"})) for day in itinerary.days
            ]
            if len(set(used_neighborhood_sets)) <= max(1, len(itinerary.days) - 2):
                issues.append(
                    {
                        "code": "neighborhood_variety",
                        "severity": 1,
                        "message": "Too many days feel geographically similar.",
                        "repair_hint": "Vary the neighborhoods or route logic so each day has a clearer identity.",
                    }
                )

        return issues

    def _normalize_issue(self, issue: dict[str, Any]) -> dict[str, Any]:
        severity = issue.get("severity", 1)
        try:
            severity = int(severity)
        except Exception:
            severity = 1
        severity = max(1, min(severity, 3))
        return {
            "code": issue.get("code", "quality_issue"),
            "severity": severity,
            "message": issue.get("message", ""),
            "repair_hint": issue.get("repair_hint", ""),
        }

    def _issue_score(self, issues: list[dict[str, Any]]) -> int:
        return sum(int(issue.get("severity", 1)) for issue in issues)

    def _repair_daily_structure_with_claude(
        self,
        response_language: str,
        brief: PlanningBrief,
        itinerary: ItineraryDraft,
        planning_context: dict[str, Any],
        issues: list[dict[str, Any]],
    ) -> list[DayPlan] | None:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1800,
                system=(
                    f"{self.system_prompt}\n\n"
                    "You are repairing an itinerary draft.\n"
                    "Return JSON only with the full repaired days array using the same shape as before.\n"
                    "Keep the plan recognizable, but fix the issues.\n"
                    "Use only the provided venue candidates.\n"
                    "- Reduce repetition.\n"
                    "- Improve day coverage.\n"
                    "- Tighten geography.\n"
                    "- Match the requested pace.\n"
                    "- Lunch and Dinner must be real restaurants from the shortlist.\n"
                    "- Experiences must be real experiences from the shortlist.\n"
                    "- Full days should have Morning, Lunch, Afternoon, and Dinner.\n"
                    f"- Write in {'Chinese' if response_language == 'zh' else 'English'}.\n"
                ),
                messages=[
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "planning_brief": brief.model_dump(mode="json"),
                                "issues": issues,
                                "current_days": [day.model_dump(mode="json") for day in itinerary.days],
                                "selected_hotel": self._hotel_brief_for_planning(planning_context["selected_hotel"]) if planning_context["selected_hotel"] else None,
                                "candidate_restaurants": [self._restaurant_brief_for_planning(restaurant, brief) for restaurant in planning_context["ranked_restaurants"][:10]],
                                "candidate_experiences": [self._experience_brief_for_planning(experience, brief) for experience in planning_context["ranked_experiences"][:10]],
                                "restaurant_names": [restaurant.name for restaurant in planning_context["ranked_restaurants"][:10]],
                                "experience_names": [experience.name for experience in planning_context["ranked_experiences"][:10]],
                            },
                            ensure_ascii=False,
                        ),
                    }
                ],
            )
            text = self._extract_text(self._normalize_blocks(response.content))
            payload = self._parse_json_block(text)
            days = [DayPlan.model_validate(day) for day in payload.get("days", [])]
            return days or None
        except Exception:  # pragma: no cover - graceful fallback
            return None

    def _build_itinerary(
        self,
        tool_inputs: dict[str, dict[str, Any]],
        tool_payloads: dict[str, Any],
        previous: ItineraryDraft | None,
        planning_context: dict[str, Any] | None = None,
    ) -> ItineraryDraft | None:
        if "get_daily_structure" not in tool_payloads:
            return previous

        daily_input = DailyStructureInput.model_validate(tool_inputs["get_daily_structure"])
        days = [DayPlan.model_validate(day) for day in tool_payloads["get_daily_structure"]]

        weather = None
        if "get_weather" in tool_payloads:
            weather = WeatherSummary.model_validate(tool_payloads["get_weather"])
        elif previous:
            weather = previous.weather

        hotels = [HotelOption.model_validate(item) for item in tool_payloads.get("get_hotels", [])]
        if not hotels and previous:
            hotels = previous.hotels

        restaurants = [RestaurantOption.model_validate(item) for item in tool_payloads.get("get_restaurants", [])]
        if not restaurants and previous:
            restaurants = previous.restaurants

        experiences = [ExperienceOption.model_validate(item) for item in tool_payloads.get("get_experiences", [])]
        if not experiences and previous:
            experiences = previous.experiences

        selected_hotel = next(
            (hotel for hotel in hotels if hotel.name.lower() == daily_input.hotel_name.lower()),
            hotels[0] if hotels else (previous.selected_hotel if previous else None),
        )

        if planning_context:
            days = self._align_days_to_candidates(
                days,
                selected_hotel,
                planning_context["ranked_restaurants"],
                planning_context["ranked_experiences"],
            )

        days = self._enrich_days(days, selected_hotel, restaurants, experiences)

        return ItineraryDraft(
            destination=daily_input.destination,
            month=daily_input.month,
            trip_length_days=daily_input.trip_length_days,
            travel_party=daily_input.travel_party,
            budget=daily_input.budget,
            interests=daily_input.interests,
            weather=weather,
            selected_hotel=selected_hotel,
            hotels=hotels,
            restaurants=restaurants,
            experiences=experiences,
            days=days,
            summary=previous.summary if previous else "Trip plan updated.",
        )

    def _enrich_days(
        self,
        days: list[DayPlan],
        selected_hotel: HotelOption | None,
        restaurants: list[RestaurantOption],
        experiences: list[ExperienceOption],
    ) -> list[DayPlan]:
        enriched_days: list[DayPlan] = []
        for day in days:
            enriched_items = []
            for item in day.items:
                if item.kind == "hotel" and selected_hotel and self._normalize_text(item.title) == self._normalize_text(selected_hotel.name):
                    enriched_items.append(
                        item.model_copy(
                            update={
                                "title": selected_hotel.name,
                                "neighborhood": selected_hotel.neighborhood,
                                "description": selected_hotel.short_description,
                                "booking_link": selected_hotel.affiliate_link,
                            }
                        )
                    )
                    continue

                if item.kind == "restaurant":
                    restaurant = self._find_option_by_title(item.title, restaurants)
                    if restaurant:
                        description = (
                            f"{restaurant.cuisine} in {restaurant.neighborhood}."
                            if not restaurant.must_order_dish
                            else f"{restaurant.cuisine} in {restaurant.neighborhood}. Signature: {restaurant.must_order_dish}."
                        )
                        enriched_items.append(
                            item.model_copy(
                                update={
                                    "title": restaurant.name,
                                    "neighborhood": restaurant.neighborhood,
                                    "description": description,
                                    "booking_link": restaurant.reservation_link,
                                }
                            )
                        )
                        continue

                if item.kind == "experience":
                    experience = self._find_option_by_title(item.title, experiences)
                    if experience:
                        enriched_items.append(
                            item.model_copy(
                                update={
                                    "title": experience.name,
                                    "neighborhood": experience.neighborhood,
                                    "description": experience.why_it_fits,
                                    "booking_link": experience.booking_link,
                                }
                            )
                        )
                        continue

                enriched_items.append(item)

            enriched_days.append(day.model_copy(update={"items": enriched_items}))

        return enriched_days

    def _align_days_to_candidates(
        self,
        days: list[DayPlan],
        selected_hotel: HotelOption | None,
        ranked_restaurants: list[RestaurantOption],
        ranked_experiences: list[ExperienceOption],
    ) -> list[DayPlan]:
        restaurant_uses: dict[str, int] = {}
        experience_uses: dict[str, int] = {}

        aligned_days: list[DayPlan] = []
        for day in days:
            aligned_items: list[DayItem] = []
            for item in day.items:
                if item.kind == "hotel" and selected_hotel:
                    aligned_items.append(item.model_copy(update={"title": selected_hotel.name, "neighborhood": selected_hotel.neighborhood}))
                    continue

                if item.kind == "restaurant":
                    restaurant = self._choose_balanced_candidate(item.title, ranked_restaurants, restaurant_uses)
                    if restaurant:
                        restaurant_uses[restaurant.id] = restaurant_uses.get(restaurant.id, 0) + 1
                        aligned_items.append(item.model_copy(update={"title": restaurant.name, "neighborhood": restaurant.neighborhood}))
                        continue

                if item.kind == "experience":
                    experience = self._choose_balanced_candidate(item.title, ranked_experiences, experience_uses)
                    if experience:
                        experience_uses[experience.id] = experience_uses.get(experience.id, 0) + 1
                        aligned_items.append(item.model_copy(update={"title": experience.name, "neighborhood": experience.neighborhood}))
                        continue

                aligned_items.append(item)

            aligned_days.append(day.model_copy(update={"items": aligned_items}))

        return aligned_days

    def _choose_balanced_candidate(self, title: str, candidates: list[Any], usage: dict[str, int]) -> Any | None:
        if not candidates:
            return None

        matched = self._find_option_by_title(title, candidates)
        minimum_use = min((usage.get(candidate.id, 0) for candidate in candidates), default=0)

        if matched and usage.get(matched.id, 0) <= minimum_use:
            return matched

        ranked = sorted(candidates, key=lambda candidate: (usage.get(candidate.id, 0), candidates.index(candidate)))
        return ranked[0] if ranked else matched

    def _find_option_by_title(self, title: str, options: list[Any]) -> Any | None:
        normalized_title = self._normalize_text(title)
        for option in options:
            candidate_title = self._normalize_text(option.name)
            if candidate_title == normalized_title or candidate_title in normalized_title or normalized_title in candidate_title:
                return option
        return None

    def _matches_restaurant_candidate(self, title: str, restaurants: list[RestaurantOption]) -> bool:
        return self._find_option_by_title(title, restaurants) is not None

    def _matches_experience_candidate(self, title: str, experiences: list[ExperienceOption]) -> bool:
        return self._find_option_by_title(title, experiences) is not None

    def _apply_day_swap_request(self, itinerary: ItineraryDraft, request: str) -> ItineraryDraft:
        numbers = [int(value) for value in re.findall(r"\d+", request)]
        if len(numbers) < 2:
            return itinerary

        first, second = numbers[0], numbers[1]
        if first == second:
            return itinerary

        day_map = {day.day_number: day for day in itinerary.days}
        if first not in day_map or second not in day_map:
            return itinerary

        swapped_days: list[DayPlan] = []
        for day in itinerary.days:
            if day.day_number == first:
                swapped_days.append(day_map[second].model_copy(update={"day_number": first}))
            elif day.day_number == second:
                swapped_days.append(day_map[first].model_copy(update={"day_number": second}))
            else:
                swapped_days.append(day)

        return itinerary.model_copy(update={"days": swapped_days})

    def _polish_itinerary_days(self, brief: PlanningBrief, itinerary: ItineraryDraft) -> ItineraryDraft:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1200,
                system=(
                    f"{self.system_prompt}\n\n"
                    "You rewrite itinerary copy for warmth and clarity. "
                    "Do not change venue names, time labels, number of days, number of items, or ordering. "
                    "Return JSON only with this shape: "
                    '{"days":[{"day_number":1,"theme":"...","summary":"...","item_descriptions":["..."]}]}.'
                ),
                messages=[
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "planning_brief": brief.model_dump(mode="json"),
                                "days": [
                                    {
                                        "day_number": day.day_number,
                                        "theme": day.theme,
                                        "summary": day.summary,
                                        "items": [
                                            {
                                                "time_label": item.time_label,
                                                "title": item.title,
                                                "kind": item.kind,
                                                "description": item.description,
                                            }
                                            for item in day.items
                                        ],
                                    }
                                    for day in itinerary.days
                                ],
                            },
                            ensure_ascii=False,
                        ),
                    }
                ],
            )
            text = self._extract_text(self._normalize_blocks(response.content))
            payload = self._parse_json_block(text)
            polished_days = payload.get("days", [])

            updated_days: list[DayPlan] = []
            for day, polished_day in zip(itinerary.days, polished_days):
                item_descriptions = polished_day.get("item_descriptions", [])
                updated_items = []
                for item, polished_description in zip(day.items, item_descriptions):
                    updated_items.append(item.model_copy(update={"description": polished_description}))

                updated_days.append(
                    day.model_copy(
                        update={
                            "theme": polished_day.get("theme", day.theme),
                            "summary": polished_day.get("summary", day.summary),
                            "items": updated_items or day.items,
                        }
                    )
                )

            if updated_days:
                return itinerary.model_copy(update={"days": updated_days})
        except Exception:  # pragma: no cover - graceful fallback
            return itinerary

        return itinerary

    def _compose_final_reply(
        self,
        response_language: str,
        brief: PlanningBrief,
        itinerary: ItineraryDraft | None,
        changed_fields: set[str],
    ) -> str:
        if not itinerary:
            if response_language == "zh":
                return "信息已经够了。你也可以继续告诉我你想更慢一点、更住在中心一点，或者更强调美食。"
            return "I have enough to start. If you want, you can still tell me to slow the pace down, stay more centrally, or make the trip more food-focused."

        response = self.client.messages.create(
            model=self.model,
            max_tokens=700,
            system=(
                f"{self.system_prompt}\n\n"
                "You are Vela, a thoughtful travel concierge. "
                "Write a short final reply in plain text, not markdown. "
                "Keep it warm, concrete, and concise. "
                f"Reply in {'Chinese' if response_language == 'zh' else 'English'}. "
                "Include a short 'Weather & What to Wear' section with 2 to 3 bullet points when weather is available. "
                "Then give a short trip summary and one useful follow-up question. "
                "Do not paste the full itinerary."
            ),
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "planning_brief": brief.model_dump(mode="json"),
                            "changed_fields": sorted(changed_fields),
                            "itinerary": itinerary.model_dump(mode="json"),
                        },
                        ensure_ascii=False,
                    ),
                }
            ],
        )
        return self._extract_text(self._normalize_blocks(response.content))

    def _normalize_blocks(self, blocks: Any) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for block in blocks:
            if hasattr(block, "model_dump"):
                normalized.append(block.model_dump(exclude_none=True))
                continue

            block_type = getattr(block, "type", None)
            payload = {"type": block_type}
            for field in ("id", "name", "input", "text"):
                if hasattr(block, field):
                    payload[field] = getattr(block, field)
            normalized.append(payload)
        return normalized

    def _extract_text(self, blocks: list[dict[str, Any]]) -> str:
        texts = [block["text"] for block in blocks if block.get("type") == "text" and block.get("text")]
        return "\n".join(texts).strip()

    def _compact_reply(self, response_language: str, reply: str, itinerary: ItineraryDraft | None) -> str:
        if not itinerary:
            return reply.strip()

        if len(reply.strip()) <= 520:
            return reply.strip()

        standout_bits = []
        if itinerary.selected_hotel:
            standout_bits.append(f"selected {itinerary.selected_hotel.name} as your base")
        if itinerary.restaurants:
            standout_bits.append(f"anchored the food plan around {itinerary.restaurants[0].name}")
        if itinerary.experiences:
            standout_bits.append(f"included {itinerary.experiences[0].name}")

        standout = ", and ".join(standout_bits[:2]) if standout_bits else "built a balanced plan"
        pace_hint = itinerary.days[0].theme if itinerary.days else "a coherent day-by-day structure"

        if response_language == "zh":
            return (
                f"我已经更新了你的 {itinerary.destination}{itinerary.trip_length_days} 天行程，重点围绕"
                f"{'、'.join(itinerary.interests) if itinerary.interests else '你的旅行目标'}。"
                f"目前我{standout}，整体节奏是{pace_hint.lower()}。"
                f"如果你愿意，我还可以继续把它调成更浪漫、更省钱、更慢节奏，或换一个住区。"
            )

        return (
            f"I've updated your {itinerary.trip_length_days}-day {itinerary.destination} plan for "
            f"{', '.join(itinerary.interests) if itinerary.interests else 'your trip goals'}. "
            f"I {standout}, with {pace_hint.lower()}. "
            f"If you want, I can now refine it for romance, budget, pace, or neighborhood preference."
        )

    def _detect_response_language(self, user_text: str) -> str:
        if re.search(r"[\u4e00-\u9fff]", user_text):
            return "zh"
        return "en"

    def _extract_trip_length(self, user_text: str) -> int | None:
        match = re.search(r"(\d+)\s*(?:days?|天|晚)", user_text, re.IGNORECASE)
        if not match:
            return None
        value = int(match.group(1))
        return value if 1 <= value <= 14 else None

    def _extract_travel_party(self, lower_text: str) -> str | None:
        if any(token in lower_text for token in ("solo", "alone", "by myself", "single traveler", "单人", "一个人", "自己")):
            return "solo"
        if any(token in lower_text for token in ("couple", "romantic", "两个人", "情侣")):
            return "couple"
        if any(token in lower_text for token in ("family", "kids", "children", "家庭", "带娃", "带孩子")):
            return "family"
        if any(token in lower_text for token in ("friends", "with friends", "朋友")):
            return "friends"
        return None

    def _extract_destination(self, user_text: str) -> str | None:
        english_patterns = [
            r"(?:go to|trip to|visit|visiting|travel to)\s+([a-zA-Z][a-zA-Z\s'&.-]{1,40}?)(?:\s+(?:for|next|this|in|on|with|alone|as|,|$))",
            r"(?:in)\s+([A-Z][a-zA-Z\s'&.-]{1,40}?)(?:\s+(?:for|next|this|on|with|alone|,|$))",
        ]
        for pattern in english_patterns:
            match = re.search(pattern, user_text, re.IGNORECASE)
            if match:
                destination = match.group(1).strip(" ,.")
                if destination:
                    return destination.title()

        chinese_match = re.search(r"(?:去|到)([\u4e00-\u9fffA-Za-z]{2,20})", user_text)
        if chinese_match:
            destination = chinese_match.group(1).strip("，。,. ")
            if destination.startswith("巴黎") and "伦敦" in destination:
                return "Paris"
            return destination
        return None

    def _extract_dates_or_month(self, user_text: str) -> str | None:
        english_match = re.search(
            r"(next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|weekend)|"
            r"this\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|weekend)|"
            r"(?:late|mid|early)\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)|"
            r"(?:january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+\d{1,2})?)",
            user_text,
            re.IGNORECASE,
        )
        if english_match:
            return english_match.group(1)

        chinese_match = re.search(r"(下周[一二三四五六日天]?|本周[一二三四五六日天]?|[0-9一二三四五六七八九十]+月(?:底|初|中旬|中)?|明年[0-9一二三四五六七八九十]+月)", user_text)
        if chinese_match:
            return chinese_match.group(1)
        return None

    def _extract_budget(self, lower_text: str) -> str | None:
        if any(token in lower_text for token in ("budget", "cheap", "省钱", "便宜")):
            return "budget"
        if any(token in lower_text for token in ("luxury", "premium", "high-end", "奢华", "高端")):
            return "luxury"

        amount_match = re.search(r"(\d[\d,\.]*)\s*(?:gbp|pounds?|usd|dollars?|eur|euros?|英镑|美元|欧元)", lower_text)
        if not amount_match:
            return None
        amount = float(amount_match.group(1).replace(",", ""))
        if amount < 800:
            return "budget"
        if amount > 2500:
            return "luxury"
        return "mid"

    def _extract_pace_from_text(self, lower_text: str) -> str | None:
        slow_tokens = (
            "not too packed",
            "not too busy",
            "don't want it too packed",
            "do not want it too packed",
            "slower pace",
            "slow pace",
            "take it easy",
            "relaxed",
            "轻松一点",
            "轻松些",
            "不要太满",
            "别太满",
            "不想太赶",
            "不要太赶",
            "慢一点",
            "悠闲",
        )
        packed_tokens = (
            "packed",
            "see as much as possible",
            "fit in a lot",
            "high density",
            "尽量多去",
            "多安排一点",
            "行程紧一点",
            "高密度",
        )

        if any(token in lower_text for token in slow_tokens):
            return "slow"
        if any(token in lower_text for token in packed_tokens):
            return "packed"
        return None

    def _extract_constraints_from_text(self, normalized_text: str, lower_text: str) -> list[str]:
        constraints: list[str] = []

        if any(
            token in lower_text
            for token in (
                "not too packed",
                "not too busy",
                "don't want it too packed",
                "do not want it too packed",
                "slower pace",
                "slow pace",
                "take it easy",
                "relaxed",
                "轻松一点",
                "轻松些",
                "不要太满",
                "别太满",
                "不想太赶",
                "不要太赶",
                "慢一点",
                "悠闲",
            )
        ):
            constraints.append("avoid overly packed days")

        if any(
            token in lower_text
            for token in (
                "avoid long queues",
                "long queues",
                "skip long queues",
                "don't want long queues",
                "do not want long queues",
                "不想排队",
                "不要排队",
                "少排队",
                "避免排队",
                "很多排队",
            )
        ):
            constraints.append("avoid long queues")

        if any(
            token in lower_text
            for token in (
                "safety",
                "safe",
                "security",
                "治安",
                "安全",
                "注意安全",
            )
        ):
            constraints.append("safety-conscious planning")

        dietary_match = re.findall(r"(vegetarian|vegan|halal|kosher|gluten[- ]free|素食|清真|过敏)", normalized_text, re.IGNORECASE)
        if dietary_match:
            constraints.append("dietary restrictions noted")

        return constraints
