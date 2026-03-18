"""Research helpers: tool planning, parallel execution, candidate ranking and scoring.

Extracted from AgentOrchestrator so the logic can be used (and tested) independently.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from src.tools.registry import run_tool
from src.tools.schemas import (
    ExperienceOption,
    HotelOption,
    ItineraryDraft,
    PlanningBrief,
    RestaurantOption,
    WeatherSummary,
)

# ---------------------------------------------------------------------------
# Tool planning
# ---------------------------------------------------------------------------

FIELD_TOOL_DEPENDENCIES: dict[str, set[str]] = {
    "destination": {"get_weather", "get_hotels", "get_restaurants", "get_experiences",
                    "get_visa_requirements", "estimate_budget", "get_packing_suggestions"},
    "dates_or_month": {"get_weather", "get_packing_suggestions"},
    "travel_party": {"get_experiences", "estimate_budget"},
    "budget": {"get_hotels", "get_restaurants", "estimate_budget"},
    "hotel_preference": {"get_hotels"},
    "neighborhood_preference": {"get_hotels", "get_restaurants"},
    "priorities": {"get_restaurants", "get_experiences"},
    "dietary_preferences": {"get_restaurants"},
    "must_do": {"get_restaurants", "get_experiences"},
    "style_notes": {"get_restaurants", "get_experiences"},
    "pace": {"get_experiences"},
    "notes": {"get_restaurants", "get_experiences"},
}


def build_tool_plan(changed_fields: set[str], has_existing_plan: bool) -> dict[str, Any]:
    """Decide which gather-tools to (re)run based on what changed in the brief."""
    if not has_existing_plan:
        return {"gather_tools": ["get_weather", "get_hotels", "get_restaurants", "get_experiences"]}

    gather_tools: set[str] = set()
    for field in changed_fields:
        gather_tools.update(FIELD_TOOL_DEPENDENCIES.get(field, set()))

    return {"gather_tools": sorted(gather_tools)}


def build_tool_input(
    tool_name: str,
    brief: PlanningBrief,
    previous: ItineraryDraft | None,
) -> dict[str, Any] | None:
    """Build the input dict for a single gather-tool, or *None* if unsupported."""
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


# ---------------------------------------------------------------------------
# Parallel tool execution
# ---------------------------------------------------------------------------


def execute_tools_parallel(
    gather_specs: list[tuple[str, dict[str, Any]]],
    timeout_seconds: float = 30.0,
) -> dict[str, tuple[str, Any]]:
    """Run gather-tools in parallel via *ThreadPoolExecutor*.

    Returns a dict mapping ``tool_name -> (status, result_or_error)`` where
    *status* is ``"ok"`` or ``"error"``.
    """
    results: dict[str, tuple[str, Any]] = {}
    if not gather_specs:
        return results

    with ThreadPoolExecutor(max_workers=min(4, len(gather_specs))) as executor:
        future_map = {executor.submit(run_tool, name, inp): name for name, inp in gather_specs}
        for future in as_completed(future_map, timeout=timeout_seconds):
            name = future_map[future]
            try:
                results[name] = ("ok", future.result())
            except Exception as exc:
                results[name] = ("error", str(exc))
        # Mark any tools that didn't finish within the timeout
        for future, name in future_map.items():
            if name not in results:
                future.cancel()
                results[name] = ("error", f"Tool {name} timed out after {timeout_seconds}s")
    return results


# ---------------------------------------------------------------------------
# Candidate ranking / context
# ---------------------------------------------------------------------------


def prepare_candidate_context(
    brief: PlanningBrief,
    tool_payloads: dict[str, Any],
    previous: ItineraryDraft | None,
) -> dict[str, Any]:
    """Parse, rank and select the best candidates from raw tool payloads."""
    hotels = [HotelOption.model_validate(item) for item in tool_payloads.get("get_hotels", [])]
    if not hotels and previous:
        hotels = previous.hotels

    restaurants = [RestaurantOption.model_validate(item) for item in tool_payloads.get("get_restaurants", [])]
    if not restaurants and previous:
        restaurants = previous.restaurants

    experiences = [ExperienceOption.model_validate(item) for item in tool_payloads.get("get_experiences", [])]
    if not experiences and previous:
        experiences = previous.experiences

    ranked_hotels = sorted(hotels, key=lambda hotel: score_hotel(hotel, brief), reverse=True)
    ranked_restaurants = sorted(restaurants, key=lambda restaurant: score_restaurant(restaurant, brief), reverse=True)
    ranked_experiences = sorted(experiences, key=lambda experience: score_experience(experience, brief), reverse=True)

    selected_hotel = ranked_hotels[0] if ranked_hotels else (previous.selected_hotel if previous else None)

    geo_clusters = compute_neighborhood_clusters(
        selected_hotel,
        ranked_restaurants,
        ranked_experiences,
        brief.trip_length_days or 1,
    )

    return {
        "hotels": hotels,
        "restaurants": restaurants,
        "experiences": experiences,
        "ranked_hotels": ranked_hotels,
        "ranked_restaurants": ranked_restaurants,
        "ranked_experiences": ranked_experiences,
        "selected_hotel": selected_hotel,
        "geo_clusters": geo_clusters,
    }


def compute_neighborhood_clusters(
    selected_hotel: HotelOption | None,
    ranked_restaurants: list[RestaurantOption],
    ranked_experiences: list[ExperienceOption],
    trip_length_days: int,
) -> dict[str, Any]:
    """Group venues by neighborhood and suggest a day-by-day geographic routing plan.

    Returns a mapping that guides Claude to cluster each day around one or two
    neighborhoods — minimising unnecessary travel across the city.
    """
    if not selected_hotel:
        return {}

    hotel_neighborhood = selected_hotel.neighborhood

    # Tally venue counts per neighborhood
    neighborhood_tally: dict[str, int] = {}
    neighborhood_venues: dict[str, list[dict[str, str]]] = {}

    for r in ranked_restaurants:
        n = r.neighborhood or "unknown"
        neighborhood_tally[n] = neighborhood_tally.get(n, 0) + 1
        neighborhood_venues.setdefault(n, []).append({"type": "restaurant", "name": r.name})

    for e in ranked_experiences:
        n = e.neighborhood or "unknown"
        neighborhood_tally[n] = neighborhood_tally.get(n, 0) + 1
        neighborhood_venues.setdefault(n, []).append({"type": "experience", "name": e.name})

    # Sort neighborhoods richest first, hotel neighborhood always first on Day 1
    sorted_neighborhoods = sorted(
        neighborhood_tally.items(),
        key=lambda kv: (0 if kv[0] == hotel_neighborhood else -kv[1]),
    )
    distinct_areas = [n for n, _ in sorted_neighborhoods]

    # Build a day-by-day neighborhood plan
    day_plan: list[dict[str, Any]] = []
    for day_num in range(1, trip_length_days + 1):
        if day_num == 1:
            anchor = hotel_neighborhood
            note = "Arrival day — stay close to hotel, light schedule."
        else:
            idx = (day_num - 1) % max(len(distinct_areas), 1)
            anchor = distinct_areas[idx]
            note = f"Cluster activities in {anchor} and adjacent areas."

        day_plan.append({"day": day_num, "anchor_neighborhood": anchor, "note": note})

    return {
        "hotel_neighborhood": hotel_neighborhood,
        "day_neighborhood_plan": day_plan,
        "neighborhood_venue_counts": neighborhood_tally,
    }


def payloads_from_previous(itinerary: ItineraryDraft | None) -> dict[str, Any]:
    """Extract tool payloads from an existing itinerary so unchanged tools can be skipped."""
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
    if itinerary.budget_estimate:
        payloads["estimate_budget"] = itinerary.budget_estimate.model_dump(mode="json")
    if itinerary.visa_requirements:
        payloads["get_visa_requirements"] = itinerary.visa_requirements.model_dump(mode="json")
    if itinerary.packing_suggestions:
        payloads["get_packing_suggestions"] = itinerary.packing_suggestions.model_dump(mode="json")
    return payloads


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


def score_hotel(hotel: HotelOption, brief: PlanningBrief) -> int:
    """Score a hotel candidate against the planning brief."""
    score = 0
    text = _normalize_text(
        " ".join([hotel.name, hotel.neighborhood, hotel.short_description, " ".join(hotel.key_highlights)])
    )

    if brief.neighborhood_preference and _normalize_text(brief.neighborhood_preference) in text:
        score += 4
    if brief.hotel_preference and _normalize_text(brief.hotel_preference) in text:
        score += 4
    for note in brief.style_notes:
        if _normalize_text(note) in text:
            score += 2
    for avoid in brief.must_avoid:
        if _normalize_text(avoid) in text:
            score -= 6
    score += _rating_score(hotel.rating, hotel.user_rating_count)
    if brief.budget == hotel.category:
        score += 3
    if hotel.photo_name:
        score += 1
    return score


def score_restaurant(restaurant: RestaurantOption, brief: PlanningBrief) -> int:
    """Score a restaurant candidate against the planning brief."""
    score = 0
    text = _normalize_text(
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

    if brief.neighborhood_preference and _normalize_text(brief.neighborhood_preference) in text:
        score += 3
    for token in brief.priorities + brief.style_notes + brief.must_do + brief.dietary_preferences:
        if _normalize_text(token) in text:
            score += 2
    for avoid in brief.must_avoid:
        if _normalize_text(avoid) in text:
            score -= 6
    score += _rating_score(restaurant.rating, restaurant.user_rating_count)
    score += _hidden_gem_score(
        title=restaurant.name,
        category=restaurant.cuisine,
        neighborhood=restaurant.neighborhood,
        rating_count=restaurant.user_rating_count,
        brief=brief,
    )
    if restaurant.photo_name:
        score += 1
    return score


def score_experience(experience: ExperienceOption, brief: PlanningBrief) -> int:
    """Score an experience candidate against the planning brief."""
    score = 0
    text = _normalize_text(
        " ".join([experience.name, experience.category, experience.neighborhood, experience.why_it_fits])
    )

    if brief.neighborhood_preference and _normalize_text(brief.neighborhood_preference) in text:
        score += 3
    for token in brief.priorities + brief.style_notes + brief.must_do:
        if _normalize_text(token) in text:
            score += 2
    for avoid in brief.must_avoid:
        if _normalize_text(avoid) in text:
            score -= 6
    score += _rating_score(experience.rating, experience.user_rating_count)
    score += _hidden_gem_score(
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


def _rating_score(rating: float | None, rating_count: int | None) -> int:
    """Weighted score based on average rating (4.0 baseline) and review count."""
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
    title: str,
    category: str,
    neighborhood: str,
    rating_count: int | None,
    brief: PlanningBrief,
) -> int:
    """Boost score when the user's preferences lean toward hidden/local gems."""
    preference_text = " ".join(brief.priorities + brief.style_notes + brief.must_do).lower()
    if not any(token in preference_text for token in ("hidden", "local", "gem", "independent", "quiet", "neighborhood")):
        return 0

    score = 0
    combined = f"{title} {category} {neighborhood}".lower()
    if any(
        token in combined
        for token in ("independent", "bookstore", "gallery", "kissaten", "market", "backstreet", "local", "quiet", "neighborhood", "garden")
    ):
        score += 3
    if rating_count:
        if rating_count < 400:
            score += 2
        elif rating_count > 5000:
            score -= 2
    return score


def _normalize_text(value: str) -> str:
    """Lower-case, strip punctuation, and collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]+", " ", value.lower())).strip()
