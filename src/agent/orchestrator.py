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

        daily_input = self._build_daily_structure_input(
            brief,
            tool_payloads,
            state.last_itinerary,
            patch.day_swap_request,
        )
        tool_inputs["get_daily_structure"] = daily_input.model_dump(mode="json")
        yield AgentEvent(type="tool_started", tool_name="get_daily_structure", message="Running get_daily_structure")
        day_output = run_tool("get_daily_structure", tool_inputs["get_daily_structure"])
        tool_payloads["get_daily_structure"] = day_output
        yield AgentEvent(type="tool_completed", tool_name="get_daily_structure", payload=day_output)

        itinerary = self._build_itinerary(tool_inputs, tool_payloads, state.last_itinerary)
        if itinerary and patch.day_swap_request:
            itinerary = self._apply_day_swap_request(itinerary, patch.day_swap_request)
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
        return PlanningBriefPatch.model_validate(payload)

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
        if response_language == "zh":
            return self._build_clarifying_reply_zh(brief, missing_fields)
        return self._build_clarifying_reply_en(brief, missing_fields)

    def _build_clarifying_reply_zh(self, brief: PlanningBrief, missing_fields: list[str]) -> str:
        questions: list[str] = []

        if any(field in missing_fields for field in ("destination", "dates_or_month", "trip_length_days")):
            questions.append("先告诉我这次要去哪里、什么时候去，以及准备玩几天。比如“巴黎，1月底，3天”。")
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

        if any(field in missing_fields for field in ("destination", "dates_or_month", "trip_length_days")):
            questions.append("First, tell me where you're going, when you're going, and how many days you have. For example: \"Paris, late January, 3 days.\"")
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
    ) -> DailyStructureInput:
        hotels = [HotelOption.model_validate(item) for item in tool_payloads.get("get_hotels", [])]
        restaurants = [RestaurantOption.model_validate(item) for item in tool_payloads.get("get_restaurants", [])]
        experiences = [ExperienceOption.model_validate(item) for item in tool_payloads.get("get_experiences", [])]

        ranked_hotels = sorted(hotels, key=lambda hotel: self._score_hotel(hotel, brief), reverse=True)
        ranked_restaurants = sorted(restaurants, key=lambda restaurant: self._score_restaurant(restaurant, brief), reverse=True)
        ranked_experiences = sorted(experiences, key=lambda experience: self._score_experience(experience, brief), reverse=True)

        selected_hotel = ranked_hotels[0] if ranked_hotels else (previous.selected_hotel if previous else None)
        restaurant_names = [restaurant.name for restaurant in ranked_restaurants[: max(brief.trip_length_days or 1, 3)]]
        experience_names = [experience.name for experience in ranked_experiences[: max(brief.trip_length_days or 1, 3)]]

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
        return score

    def _normalize_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^\w\s]+", " ", value.lower())).strip()

    def _build_itinerary(
        self,
        tool_inputs: dict[str, dict[str, Any]],
        tool_payloads: dict[str, Any],
        previous: ItineraryDraft | None,
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
        restaurant_by_name = {restaurant.name.lower(): restaurant for restaurant in restaurants}
        experience_by_name = {experience.name.lower(): experience for experience in experiences}

        enriched_days: list[DayPlan] = []
        for day in days:
            enriched_items = []
            for item in day.items:
                lowered_title = item.title.lower()

                if item.kind == "hotel" and selected_hotel and lowered_title == selected_hotel.name.lower():
                    enriched_items.append(
                        item.model_copy(
                            update={
                                "neighborhood": selected_hotel.neighborhood,
                                "description": selected_hotel.short_description,
                                "booking_link": selected_hotel.affiliate_link,
                            }
                        )
                    )
                    continue

                if item.kind == "restaurant" and lowered_title in restaurant_by_name:
                    restaurant = restaurant_by_name[lowered_title]
                    description = (
                        f"{restaurant.cuisine} in {restaurant.neighborhood}."
                        if not restaurant.must_order_dish
                        else f"{restaurant.cuisine} in {restaurant.neighborhood}. Signature: {restaurant.must_order_dish}."
                    )
                    enriched_items.append(
                        item.model_copy(
                            update={
                                "neighborhood": restaurant.neighborhood,
                                "description": description,
                                "booking_link": restaurant.reservation_link,
                            }
                        )
                    )
                    continue

                if item.kind == "experience" and lowered_title in experience_by_name:
                    experience = experience_by_name[lowered_title]
                    enriched_items.append(
                        item.model_copy(
                            update={
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
