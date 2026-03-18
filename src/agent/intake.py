"""Intake module: brief extraction, slot detection, clarifying question generation.

Extracted from orchestrator.py to keep intake-related logic cohesive and testable.
All functions are standalone; pass `client` and `model` where Claude API calls are needed.
"""

from __future__ import annotations

import json
import re
from typing import Any

from src.agent.llm_helpers import extract_text, normalize_blocks, parse_json_block
from src.tools.schemas import ItineraryDraft, PlanningBrief, PlanningBriefPatch

# ---------------------------------------------------------------------------
# Required brief fields
# ---------------------------------------------------------------------------

REQUIRED_BRIEF_FIELDS = (
    "destination",
    "dates_or_month",
    "trip_length_days",
    "travel_party",
    "budget",
    "priorities",
    "constraints_confirmed",
)

# ---------------------------------------------------------------------------
# Core intake functions
# ---------------------------------------------------------------------------


def extract_brief_patch(
    client: Any,
    model: str,
    existing_brief: PlanningBrief,
    user_message: str,
    current_itinerary: ItineraryDraft | None,
) -> PlanningBriefPatch:
    """Use Claude to parse user input into a PlanningBriefPatch."""
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
    response = client.messages.create(
        model=model,
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
    text = extract_text(normalize_blocks(response.content))
    payload = parse_json_block(text)
    patch = PlanningBriefPatch.model_validate(payload)
    return supplement_patch_from_text(existing_brief, patch, user_message)


def supplement_patch_from_text(
    existing_brief: PlanningBrief,
    patch: PlanningBriefPatch,
    user_message: str,
) -> PlanningBriefPatch:
    """Regex-based fallback extraction to fill slots Claude may have missed."""
    patch_data = patch.model_dump(exclude_none=True)
    normalized_text = user_message.strip()
    lower_text = normalized_text.lower()

    if not existing_brief.trip_length_days and patch.trip_length_days is None:
        trip_length = _extract_trip_length(normalized_text)
        if trip_length:
            patch_data["trip_length_days"] = trip_length

    if not existing_brief.travel_party and patch.travel_party is None:
        travel_party = _extract_travel_party(lower_text)
        if travel_party:
            patch_data["travel_party"] = travel_party

    if not existing_brief.destination and patch.destination is None:
        destination = _extract_destination(normalized_text)
        if destination:
            patch_data["destination"] = destination

    if not existing_brief.dates_or_month and patch.dates_or_month is None:
        dates_or_month = _extract_dates_or_month(normalized_text)
        if dates_or_month:
            patch_data["dates_or_month"] = dates_or_month

    if not existing_brief.budget and patch.budget is None:
        budget = _extract_budget(lower_text)
        if budget:
            patch_data["budget"] = budget

    inferred_constraints = _extract_constraints_from_text(lower_text)
    if inferred_constraints:
        existing_constraints = list(patch_data.get("constraints") or [])
        for constraint in inferred_constraints:
            if constraint not in existing_constraints:
                existing_constraints.append(constraint)
        patch_data["constraints"] = existing_constraints

    if patch.pace is None:
        inferred_pace = _extract_pace_from_text(lower_text)
        if inferred_pace:
            patch_data["pace"] = inferred_pace

    if not existing_brief.constraints and not existing_brief.constraints_confirmed:
        if patch.constraints is None and patch.constraints_confirmed is None:
            if any(token in lower_text for token in ("no special restrictions", "no restrictions")):
                patch_data["constraints_confirmed"] = True

    return PlanningBriefPatch.model_validate(patch_data)


def merge_brief(existing: PlanningBrief, patch: PlanningBriefPatch) -> PlanningBrief:
    """Merge a patch into an existing brief, returning a new PlanningBrief."""
    merged = existing.model_dump(mode="python")
    patch_data = patch.model_dump(exclude_none=True)
    for key, value in patch_data.items():
        merged[key] = value
    return PlanningBrief.model_validate(merged)


def missing_fields(brief: PlanningBrief) -> list[str]:
    """Check which required fields are still missing from the brief."""
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


def build_clarifying_reply(
    client: Any,
    model: str,
    brief: PlanningBrief,
    missing: list[str],
) -> str:
    """Generate a clarifying message for the user, asking about missing fields."""
    generated = _generate_clarifying_reply_with_claude(client, model, brief, missing)
    if generated:
        return generated
    return _build_clarifying_reply_fallback(brief, missing)


# ---------------------------------------------------------------------------
# Claude-powered clarifying reply
# ---------------------------------------------------------------------------


def _generate_clarifying_reply_with_claude(
    client: Any,
    model: str,
    brief: PlanningBrief,
    missing: list[str],
) -> str | None:
    """Ask Claude to write a warm clarifying message; returns None on failure."""
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
        response = client.messages.create(
            model=model,
            max_tokens=500,
            system=(
                "You write a warm, concise clarifying message for a travel-planning assistant.\n"
                "Reply in plain text only.\n"
                "Reply in the same language the user is writing in.\n"
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
                            "missing_fields": missing,
                            "field_guidance": {field: field_guidance[field] for field in missing if field in field_guidance},
                        },
                        ensure_ascii=False,
                    ),
                }
            ],
        )
        text = extract_text(normalize_blocks(response.content)).strip()
        return text or None
    except Exception:  # pragma: no cover - graceful fallback
        return None


# ---------------------------------------------------------------------------
# Template-based clarifying reply (fallback)
# ---------------------------------------------------------------------------


def _build_clarifying_reply_fallback(brief: PlanningBrief, missing: list[str]) -> str:
    questions: list[str] = []

    if "destination" in missing:
        questions.append('First, tell me which city you want to go to. For example: "Paris" or "Tokyo."')
    if "dates_or_month" in missing:
        questions.append('When are you going? For example: "next Friday," "late January," or "mid April."')
    if "trip_length_days" in missing:
        questions.append('How many days do you have for this trip? For example: "3 days" or "5 days."')
    if "travel_party" in missing:
        questions.append("Who is this trip for: solo, couple, friends, or family? That changes pacing and hotel choices.")
    if "budget" in missing:
        questions.append("Is your budget closer to budget, mid-range, or more premium? You can also give me a rough amount.")
    if "priorities" in missing:
        questions.append("What are the top 2 to 3 goals for this trip? For example: food, art, classic landmarks, shopping, nightlife, or hidden gems.")
    if "constraints" in missing:
        questions.append('Do you have anything I should avoid or plan around, like dietary restrictions, very packed days, long queues, or mobility needs? If not, just say "no special restrictions."')

    opener = "I want to get the shape of this trip right before I build the first draft. I still need a few key details:"
    closing = "You can answer in order, or just reply with the parts you already know."
    return opener + "\n\n" + "\n".join(f"- {question}" for question in questions[:4]) + "\n\n" + closing


# ---------------------------------------------------------------------------
# Regex-based slot extractors
# ---------------------------------------------------------------------------


def _extract_trip_length(user_text: str) -> int | None:
    match = re.search(r"(\d+)\s*(?:days?|nights?)", user_text, re.IGNORECASE)
    if not match:
        return None
    value = int(match.group(1))
    return value if 1 <= value <= 14 else None


def _extract_travel_party(lower_text: str) -> str | None:
    if any(token in lower_text for token in ("solo", "alone", "by myself", "single traveler")):
        return "solo"
    if any(token in lower_text for token in ("couple", "romantic", "partner", "honeymoon")):
        return "couple"
    if any(token in lower_text for token in ("family", "kids", "children")):
        return "family"
    if any(token in lower_text for token in ("friends", "with friends", "group")):
        return "friends"
    return None


def _extract_destination(user_text: str) -> str | None:
    patterns = [
        r"(?:go(?:ing)? to|trip to|visit(?:ing)?|travel(?:l?ing)? to)\s+([a-zA-Z][a-zA-Z\s'&.-]{1,40}?)(?:\s+(?:for|next|this|in|on|with|alone|as|,|$))",
        r"(?:in)\s+([A-Z][a-zA-Z\s'&.-]{1,40}?)(?:\s+(?:for|next|this|on|with|alone|,|$))",
    ]
    for pattern in patterns:
        match = re.search(pattern, user_text, re.IGNORECASE)
        if match:
            destination = match.group(1).strip(" ,.")
            if destination:
                return destination.title()
    return None


def _extract_dates_or_month(user_text: str) -> str | None:
    match = re.search(
        r"(next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|weekend)|"
        r"this\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|weekend)|"
        r"(?:late|mid|early)\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)|"
        r"(?:january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+\d{1,2})?)",
        user_text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1)
    return None


def _extract_budget(lower_text: str) -> str | None:
    if any(token in lower_text for token in ("budget", "cheap", "affordable")):
        return "budget"
    if any(token in lower_text for token in ("luxury", "premium", "high-end", "splurge")):
        return "luxury"
    if any(token in lower_text for token in ("mid-range", "mid range", "moderate", "mid")):
        return "mid"

    amount_match = re.search(r"(\d[\d,\.]*)\s*(?:gbp|pounds?|usd|dollars?|eur|euros?)", lower_text)
    if not amount_match:
        return None
    amount = float(amount_match.group(1).replace(",", ""))
    if amount < 800:
        return "budget"
    if amount > 2500:
        return "luxury"
    return "mid"


def _extract_pace_from_text(lower_text: str) -> str | None:
    slow_tokens = (
        "not too packed",
        "not too busy",
        "don't want it too packed",
        "do not want it too packed",
        "slower pace",
        "slow pace",
        "take it easy",
        "relaxed",
        "leisurely",
    )
    packed_tokens = (
        "packed",
        "see as much as possible",
        "fit in a lot",
        "high density",
        "action-packed",
        "jam-packed",
    )

    if any(token in lower_text for token in slow_tokens):
        return "slow"
    if any(token in lower_text for token in packed_tokens):
        return "packed"
    return None


def _extract_constraints_from_text(lower_text: str) -> list[str]:
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
        )
    ):
        constraints.append("avoid long queues")

    if any(token in lower_text for token in ("safety", "safe", "security")):
        constraints.append("safety-conscious planning")

    dietary_match = re.findall(r"(vegetarian|vegan|halal|kosher|gluten[- ]free)", lower_text, re.IGNORECASE)
    if dietary_match:
        constraints.append("dietary restrictions noted")

    return constraints
