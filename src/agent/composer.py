"""Itinerary composition, verification, and repair functions.

Handles: daily structure generation with Claude, quality verification,
repair loop, copy polish, and itinerary building.
"""
from __future__ import annotations

import json
import re
from typing import Any

from src.agent.llm_helpers import extract_text, normalize_blocks, parse_json_block
from src.agent.research import _hidden_gem_score, _normalize_text
from src.tools.schemas import (
    DailyStructureInput,
    DayItem,
    DayPlan,
    ExperienceOption,
    HotelOption,
    ItineraryDraft,
    PlanningBrief,
    RestaurantOption,
    WeatherSummary,
)


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def build_daily_structure_input(
    brief: PlanningBrief,
    tool_payloads: dict[str, Any],
    previous: ItineraryDraft | None,
    day_swap_request: str | None = None,
    planning_context: dict[str, Any] | None = None,
) -> DailyStructureInput:
    """Build the input payload for daily-structure generation."""
    from src.agent.research import prepare_candidate_context

    context = planning_context or prepare_candidate_context(brief, tool_payloads, previous)
    selected_hotel = context["selected_hotel"]
    ranked_restaurants = context["ranked_restaurants"]
    ranked_experiences = context["ranked_experiences"]

    restaurant_names = [r.name for r in ranked_restaurants[: max((brief.trip_length_days or 1) + 2, 5)]]
    experience_names = [e.name for e in ranked_experiences[: max(brief.trip_length_days or 1, 4)]]

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


def generate_daily_structure_with_claude(
    client: Any,
    model: str,
    system_prompt: str,
    brief: PlanningBrief,
    daily_input: DailyStructureInput,
    planning_context: dict[str, Any],
    weather_payload: Any,
) -> list[DayPlan] | None:
    """Ask Claude to generate a multi-day itinerary structure."""
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1800,
            system=(
                f"{system_prompt}\n\n"
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
                "- Write in English.\n"
            ),
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "planning_brief": brief.model_dump(mode="json"),
                            "weather": weather_payload,
                            "selected_hotel": planning_context["selected_hotel"].model_dump(mode="json")
                            if planning_context["selected_hotel"]
                            else None,
                            "candidate_hotels": [
                                _hotel_brief_for_planning(hotel) for hotel in planning_context["ranked_hotels"][:3]
                            ],
                            "candidate_restaurants": [
                                _restaurant_brief_for_planning(restaurant, brief)
                                for restaurant in planning_context["ranked_restaurants"][:10]
                            ],
                            "candidate_experiences": [
                                _experience_brief_for_planning(experience, brief)
                                for experience in planning_context["ranked_experiences"][:10]
                            ],
                            "restaurant_names": [
                                restaurant.name for restaurant in planning_context["ranked_restaurants"][:10]
                            ],
                            "experience_names": [
                                experience.name for experience in planning_context["ranked_experiences"][:10]
                            ],
                            "daily_input": daily_input.model_dump(mode="json"),
                        },
                        ensure_ascii=False,
                    ),
                }
            ],
        )
        text = extract_text(normalize_blocks(response.content))
        payload = parse_json_block(text)
        days = [DayPlan.model_validate(day) for day in payload.get("days", [])]
        return days or None
    except Exception:  # pragma: no cover - graceful fallback
        return None


def verify_itinerary_quality(
    client: Any,
    model: str,
    system_prompt: str,
    brief: PlanningBrief,
    itinerary: ItineraryDraft,
) -> dict[str, Any]:
    """Run code-level and LLM-level quality checks on the itinerary."""
    code_issues = _code_quality_findings(brief, itinerary)
    llm_issues: list[dict[str, Any]] = []

    try:
        response = client.messages.create(
            model=model,
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
                "- Write issue messages in English.\n"
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
        text = extract_text(normalize_blocks(response.content))
        payload = parse_json_block(text)
        llm_issues = [_normalize_issue(issue) for issue in payload.get("issues", [])]
    except Exception:  # pragma: no cover - graceful fallback
        llm_issues = []

    merged_issues = code_issues + llm_issues
    return {
        "approved": _issue_score(merged_issues) <= 2,
        "issues": merged_issues,
    }


def repair_daily_structure_with_claude(
    client: Any,
    model: str,
    system_prompt: str,
    brief: PlanningBrief,
    itinerary: ItineraryDraft,
    planning_context: dict[str, Any],
    issues: list[dict[str, Any]],
) -> list[DayPlan] | None:
    """Ask Claude to repair an itinerary draft based on quality issues."""
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1800,
            system=(
                f"{system_prompt}\n\n"
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
                "- Write in English.\n"
            ),
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "planning_brief": brief.model_dump(mode="json"),
                            "issues": issues,
                            "current_days": [day.model_dump(mode="json") for day in itinerary.days],
                            "selected_hotel": _hotel_brief_for_planning(planning_context["selected_hotel"])
                            if planning_context["selected_hotel"]
                            else None,
                            "candidate_restaurants": [
                                _restaurant_brief_for_planning(restaurant, brief)
                                for restaurant in planning_context["ranked_restaurants"][:10]
                            ],
                            "candidate_experiences": [
                                _experience_brief_for_planning(experience, brief)
                                for experience in planning_context["ranked_experiences"][:10]
                            ],
                            "restaurant_names": [
                                restaurant.name for restaurant in planning_context["ranked_restaurants"][:10]
                            ],
                            "experience_names": [
                                experience.name for experience in planning_context["ranked_experiences"][:10]
                            ],
                        },
                        ensure_ascii=False,
                    ),
                }
            ],
        )
        text = extract_text(normalize_blocks(response.content))
        payload = parse_json_block(text)
        days = [DayPlan.model_validate(day) for day in payload.get("days", [])]
        return days or None
    except Exception:  # pragma: no cover - graceful fallback
        return None


def build_itinerary(
    tool_inputs: dict[str, dict[str, Any]],
    tool_payloads: dict[str, Any],
    previous: ItineraryDraft | None,
    planning_context: dict[str, Any] | None = None,
) -> ItineraryDraft | None:
    """Assemble an ItineraryDraft from tool outputs and daily structure."""
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
        days = align_days_to_candidates(
            days,
            selected_hotel,
            planning_context["ranked_restaurants"],
            planning_context["ranked_experiences"],
        )

    days = enrich_days(days, selected_hotel, restaurants, experiences)

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


def enrich_days(
    days: list[DayPlan],
    selected_hotel: HotelOption | None,
    restaurants: list[RestaurantOption],
    experiences: list[ExperienceOption],
) -> list[DayPlan]:
    """Enrich day items with full details from matched options."""
    enriched_days: list[DayPlan] = []
    for day in days:
        enriched_items = []
        for item in day.items:
            if (
                item.kind == "hotel"
                and selected_hotel
                and _normalize_text(item.title) == _normalize_text(selected_hotel.name)
            ):
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
                restaurant = _find_option_by_title(item.title, restaurants)
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
                experience = _find_option_by_title(item.title, experiences)
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


def align_days_to_candidates(
    days: list[DayPlan],
    selected_hotel: HotelOption | None,
    ranked_restaurants: list[RestaurantOption],
    ranked_experiences: list[ExperienceOption],
) -> list[DayPlan]:
    """Snap day items to the best matching candidate, balancing usage."""
    restaurant_uses: dict[str, int] = {}
    experience_uses: dict[str, int] = {}

    aligned_days: list[DayPlan] = []
    for day in days:
        aligned_items: list[DayItem] = []
        for item in day.items:
            if item.kind == "hotel" and selected_hotel:
                aligned_items.append(
                    item.model_copy(update={"title": selected_hotel.name, "neighborhood": selected_hotel.neighborhood})
                )
                continue

            if item.kind == "restaurant":
                restaurant = _choose_balanced_candidate(item.title, ranked_restaurants, restaurant_uses)
                if restaurant:
                    restaurant_uses[restaurant.id] = restaurant_uses.get(restaurant.id, 0) + 1
                    aligned_items.append(
                        item.model_copy(update={"title": restaurant.name, "neighborhood": restaurant.neighborhood})
                    )
                    continue

            if item.kind == "experience":
                experience = _choose_balanced_candidate(item.title, ranked_experiences, experience_uses)
                if experience:
                    experience_uses[experience.id] = experience_uses.get(experience.id, 0) + 1
                    aligned_items.append(
                        item.model_copy(update={"title": experience.name, "neighborhood": experience.neighborhood})
                    )
                    continue

            aligned_items.append(item)

        aligned_days.append(day.model_copy(update={"items": aligned_items}))

    return aligned_days


def polish_itinerary_days(
    client: Any,
    model: str,
    system_prompt: str,
    brief: PlanningBrief,
    itinerary: ItineraryDraft,
) -> ItineraryDraft:
    """Ask Claude to rewrite day copy for warmth and clarity."""
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1200,
            system=(
                f"{system_prompt}\n\n"
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
        text = extract_text(normalize_blocks(response.content))
        payload = parse_json_block(text)
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


def apply_day_swap_request(itinerary: ItineraryDraft, request: str) -> ItineraryDraft:
    """Swap two days in the itinerary based on a user request string."""
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


def compose_final_reply(
    client: Any,
    model: str,
    system_prompt: str,
    brief: PlanningBrief,
    itinerary: ItineraryDraft | None,
    changed_fields: set[str],
) -> str:
    """Generate a warm, concise final reply summarizing the itinerary."""
    if not itinerary:
        return (
            "I have enough to start. If you want, you can still tell me to slow the pace down, "
            "stay more centrally, or make the trip more food-focused."
        )

    response = client.messages.create(
        model=model,
        max_tokens=700,
        system=(
            f"{system_prompt}\n\n"
            "You are Vela, a thoughtful travel concierge. "
            "Write a short final reply in plain text, not markdown. "
            "Keep it warm, concrete, and concise. "
            "Reply in English. "
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
    return extract_text(normalize_blocks(response.content))


def compact_reply(reply: str, itinerary: ItineraryDraft | None) -> str:
    """Produce a shorter fallback reply if the original is too long."""
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

    return (
        f"I've updated your {itinerary.trip_length_days}-day {itinerary.destination} plan for "
        f"{', '.join(itinerary.interests) if itinerary.interests else 'your trip goals'}. "
        f"I {standout}, with {pace_hint.lower()}. "
        f"If you want, I can now refine it for romance, budget, pace, or neighborhood preference."
    )


# ---------------------------------------------------------------------------
# Helper functions (private)
# ---------------------------------------------------------------------------


def _code_quality_findings(brief: PlanningBrief, itinerary: ItineraryDraft) -> list[dict[str, Any]]:
    """Run deterministic quality checks on the itinerary structure."""
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
            if not _matches_restaurant_candidate(item.title, itinerary.restaurants):
                issues.append(
                    {
                        "code": f"invalid_restaurant_{day.day_number}_{_normalize_text(item.title)}",
                        "severity": 3,
                        "message": f'"{item.title}" is being used as a restaurant, but it is not in the restaurant shortlist.',
                        "repair_hint": "Replace it with an actual restaurant from the shortlisted dining options.",
                    }
                )

        for item in experiences:
            if not _matches_experience_candidate(item.title, itinerary.experiences):
                issues.append(
                    {
                        "code": f"invalid_experience_{day.day_number}_{_normalize_text(item.title)}",
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
            [
                day.theme + " " + day.summary + " " + " ".join(item.description for item in day.items)
                for day in itinerary.days
            ]
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
            tuple(sorted({item.neighborhood or "" for item in day.items if item.kind != "note"}))
            for day in itinerary.days
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


def _normalize_issue(issue: dict[str, Any]) -> dict[str, Any]:
    """Normalize an LLM-produced issue dict to a consistent shape."""
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


def _issue_score(issues: list[dict[str, Any]]) -> int:
    """Sum severity scores across all issues."""
    return sum(int(issue.get("severity", 1)) for issue in issues)


def _hotel_brief_for_planning(hotel: HotelOption) -> dict[str, Any]:
    """Create a compact hotel summary for Claude planning prompts."""
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


def _restaurant_brief_for_planning(restaurant: RestaurantOption, brief: PlanningBrief) -> dict[str, Any]:
    """Create a compact restaurant summary for Claude planning prompts."""
    return {
        "name": restaurant.name,
        "cuisine": restaurant.cuisine,
        "neighborhood": restaurant.neighborhood,
        "price_range": restaurant.price_range,
        "rating": restaurant.rating,
        "user_rating_count": restaurant.user_rating_count,
        "why_it_fits": restaurant.why_it_fits,
        "hidden_gem_bias": _hidden_gem_score(
            restaurant.name,
            restaurant.cuisine,
            restaurant.neighborhood,
            restaurant.user_rating_count,
            brief,
        ),
    }


def _experience_brief_for_planning(experience: ExperienceOption, brief: PlanningBrief) -> dict[str, Any]:
    """Create a compact experience summary for Claude planning prompts."""
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
        "hidden_gem_bias": _hidden_gem_score(
            experience.name,
            experience.category,
            experience.neighborhood,
            experience.user_rating_count,
            brief,
        ),
    }


def _find_option_by_title(title: str, options: list[Any]) -> Any | None:
    """Find an option whose name fuzzy-matches the given title."""
    normalized_title = _normalize_text(title)
    for option in options:
        candidate_title = _normalize_text(option.name)
        if candidate_title == normalized_title or candidate_title in normalized_title or normalized_title in candidate_title:
            return option
    return None


def _choose_balanced_candidate(title: str, candidates: list[Any], usage: dict[str, int]) -> Any | None:
    """Pick a candidate that matches the title, preferring less-used ones."""
    if not candidates:
        return None

    matched = _find_option_by_title(title, candidates)
    minimum_use = min((usage.get(candidate.id, 0) for candidate in candidates), default=0)

    if matched and usage.get(matched.id, 0) <= minimum_use:
        return matched

    ranked = sorted(candidates, key=lambda candidate: (usage.get(candidate.id, 0), candidates.index(candidate)))
    return ranked[0] if ranked else matched


def _matches_restaurant_candidate(title: str, restaurants: list[RestaurantOption]) -> bool:
    """Check whether a title matches any restaurant in the list."""
    return _find_option_by_title(title, restaurants) is not None


def _matches_experience_candidate(title: str, experiences: list[ExperienceOption]) -> bool:
    """Check whether a title matches any experience in the list."""
    return _find_option_by_title(title, experiences) is not None
