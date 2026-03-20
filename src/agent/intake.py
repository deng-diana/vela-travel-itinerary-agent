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

# All 8 fields must be collected before planning can start.
ESSENTIAL_FIELDS = (
    "destination",
    "trip_length_days",
    "dates_or_month",
    "travel_party",
    "budget",
    "priorities",
    "dietary_preferences",
    "hotel_preference",
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
        "Schema keys: destination, dates_or_month, trip_length_days, travel_party, budget, "
        "total_budget_amount, total_budget_currency, priorities, "
        "constraints, constraints_confirmed, style_notes, pace, hotel_preference, neighborhood_preference, "
        "dietary_preferences, must_do, must_avoid, day_swap_request, notes.\n"
        "Rules:\n"
        "- destination: the TARGET city/country of the trip. If the user says 'from London to Paris', "
        "destination is Paris (not London, not 'London to Paris'). Extract only the destination city/country.\n"
        "- Map budget to one of: budget, mid, luxury. Compute daily rate using trip_length_days from the existing brief (or estimate 3 days if unknown). <$120/day → budget; $120–400/day → mid; >$400/day → luxury. Example: '$1500 total for 3 days' = $500/day → luxury.\n"
        "- total_budget_amount: if the user states a numeric budget (e.g. '£500', '$2000'), extract the raw integer. null if not stated.\n"
        "- total_budget_currency: the currency code (GBP, USD, EUR). null if not stated.\n"
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

    if not existing_brief.total_budget_amount and patch.total_budget_amount is None:
        amount, currency = _extract_budget_amount(lower_text)
        if amount:
            patch_data["total_budget_amount"] = amount
            patch_data["total_budget_currency"] = currency

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


def missing_essential_fields(brief: PlanningBrief) -> list[str]:
    """Check which of the 8 essential fields are still missing."""
    missing: list[str] = []
    if not brief.destination:
        missing.append("destination")
    if not brief.trip_length_days:
        missing.append("trip_length_days")
    if not brief.dates_or_month:
        missing.append("dates_or_month")
    if not brief.travel_party:
        missing.append("travel_party")
    if not brief.budget:
        missing.append("budget")
    if not brief.priorities:
        missing.append("priorities")
    # dietary_preferences: [] or ["none"] both count as filled per spec.
    # The clarifying question logic will mention dietary when asking about other fields.
    if not brief.hotel_preference:
        missing.append("hotel_preference")
    return missing


def validate_brief_ready(brief: PlanningBrief) -> tuple[bool, list[str]]:
    """Final gate check: returns (True, []) if all 8 fields are filled.

    Returns (False, [list of missing field names]) otherwise.
    dietary_preferences=[] or ["none"] both count as filled.
    priorities with at least one item counts as filled.
    """
    missing = missing_essential_fields(brief)
    return (len(missing) == 0, missing)


def apply_pace_default(brief: PlanningBrief) -> PlanningBrief:
    """Apply default pace if not set. Only pace gets a default (not in required 8)."""
    if not brief.pace:
        data = brief.model_dump(mode="python")
        data["pace"] = "balanced"
        return PlanningBrief.model_validate(data)
    return brief


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


FIELD_GUIDANCE = {
    "destination": "Ask which city or region they'd like to visit.",
    "trip_length_days": "Ask how many days they have for the trip.",
    "dates_or_month": "Ask when they're planning to go (specific dates or just a month).",
    "travel_party": "Ask who's coming along. Options: Solo / Couple / Family with kids / Group of friends.",
    "budget": (
        "Ask about their budget style. Options: "
        "Budget (hostels, street food) / Mid-range (boutique hotels, local restaurants) / Luxury (5-star, fine dining)."
    ),
    "priorities": (
        "Ask what matters most on this trip. Example interests: "
        "Food & dining / Culture & history / Nature & outdoors / Shopping / Nightlife / "
        "Art & museums / Adventure / Relaxation."
    ),
    "dietary_preferences": (
        "Ask about dietary needs or restrictions. Options: "
        "Vegetarian / Vegan / Halal / Kosher / Gluten-free / Seafood allergy / No restrictions."
    ),
    "hotel_preference": (
        "Ask what type of accommodation they prefer. Options: "
        "Boutique hotel / Resort / Airbnb / Hostel / 5-star luxury / Traditional (ryokan, riad, etc.)."
    ),
}


def _generate_clarifying_reply_with_claude(
    client: Any,
    model: str,
    brief: PlanningBrief,
    missing: list[str],
) -> str | None:
    """Ask Claude to write a warm clarifying message about missing fields.

    Groups related fields together and provides concrete options/examples.
    No limit on clarifying rounds — keeps asking until all 8 fields are filled.
    """
    try:
        response = client.messages.create(
            model=model,
            max_tokens=500,
            system=(
                "You write a concise clarifying message for a travel-planning assistant.\n"
                "Reply in the same language the user is writing in.\n"
                "FORMAT — follow this structure exactly:\n"
                "1. One short sentence acknowledging what you already know (max 15 words). No exclamation marks.\n"
                "2. A brief transition like 'Just need a few more details:' or 'One quick thing:'\n"
                "3. Each missing field on its own line, starting with a dash (—). "
                "Include concrete options in parentheses so the user can pick easily.\n"
                "4. Do NOT add a closing sentence like 'Once you answer...' or 'Let me know...'. "
                "End after the last field line.\n\n"
                "RULES:\n"
                "- Do NOT repeat back information the user already gave.\n"
                "- Do NOT use exclamation marks or overly enthusiastic language.\n"
                "- Each field line should be self-contained and scannable.\n"
                "- If only 1 field is missing, skip the dash format — just ask in one natural sentence.\n\n"
                "EXAMPLE (2 fields missing):\n"
                "Got it — 3 days in Paris as a couple, mid-range budget.\n\n"
                "Just need two more details:\n"
                "— Accommodation preference (boutique hotel / Airbnb / hostel)\n"
                "— Any dietary needs (vegetarian, halal, gluten-free, or none)\n"
            ),
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "known_brief": brief.model_dump(mode="json"),
                            "missing_fields": missing,
                            "field_guidance": {
                                field: FIELD_GUIDANCE[field]
                                for field in missing
                                if field in FIELD_GUIDANCE
                            },
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
    field_lines: dict[str, str] = {
        "destination": "— Destination (which city or region)",
        "trip_length_days": "— Trip length (how many days)",
        "dates_or_month": "— When you're going (dates or month)",
        "travel_party": "— Who's coming (solo / couple / family / friends)",
        "budget": "— Budget style (budget / mid-range / luxury)",
        "priorities": "— Interests (food, culture, nature, shopping, nightlife, art, adventure)",
        "dietary_preferences": "— Dietary needs (vegetarian, halal, gluten-free, or none)",
        "hotel_preference": "— Stay preference (boutique hotel / Airbnb / hostel / resort)",
    }

    lines = [field_lines[f] for f in missing if f in field_lines]

    if not lines:
        return "I have enough to get started — building your itinerary now."

    # Build a brief acknowledgement of what we already know
    known_parts: list[str] = []
    if brief.destination:
        known_parts.append(brief.destination)
    if brief.trip_length_days:
        known_parts.append(f"{brief.trip_length_days} days")
    if brief.travel_party:
        known_parts.append(brief.travel_party)

    if len(lines) == 1:
        ack = f"Got it — {', '.join(known_parts)}." if known_parts else "Almost there."
        field_desc = lines[0].lstrip("— ")
        return f"{ack} Just need to know: {field_desc.lower()}."

    ack = f"Got it — {', '.join(known_parts)}." if known_parts else "Thanks for sharing."
    header = "Just need a few more details:" if len(lines) > 2 else "Just need two more details:"
    return f"{ack}\n\n{header}\n" + "\n".join(lines)



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
    stop_words = {"the", "a", "an", "my", "me", "i", "you", "we", "us", "it", "is", "am",
                  "go", "make", "plan", "create", "build", "see", "do", "get", "have"}

    # Patterns that rely on city being capitalised — run WITHOUT re.IGNORECASE
    capital_patterns = [
        # "from London to Paris for ..."
        r"(?:from\s+[A-Z]\w[\w\s]{0,20}\s+to)\s+([A-Z][a-zA-Z\s'&.-]{1,30}?)(?:\s+(?:for|in|next|this|,|on)|[,.]|$)",
        # "to Paris for/next/this ..."  (only when followed immediately by a keyword)
        r"\bto\s+([A-Z][a-zA-Z]{2,30}(?:\s[A-Z][a-zA-Z]{2,20})?)\s+(?:for|in|next|this)\b",
    ]
    for pattern in capital_patterns:
        match = re.search(pattern, user_text)  # case-sensitive → city must be capitalised
        if match:
            destination = match.group(1).strip(" ,.")
            if destination and destination.lower() not in stop_words:
                return destination.title()

    # Patterns that use keyword anchors — safe with re.IGNORECASE
    keyword_patterns = [
        r"(?:go(?:ing)? to|trip to|visit(?:ing)?|travel(?:l?ing)? to)\s+([a-zA-Z][a-zA-Z\s'&.-]{1,40}?)(?:\s+(?:for|next|this|in|on|with|alone|as)|[,.]|$)",
        r"(?:in)\s+([A-Z][a-zA-Z\s'&.-]{1,40}?)(?:\s+(?:for|next|this|on|with|alone|,|$))",
    ]
    for pattern in keyword_patterns:
        match = re.search(pattern, user_text, re.IGNORECASE)
        if match:
            destination = match.group(1).strip(" ,.")
            if destination and destination.lower() not in stop_words:
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


def _extract_budget_amount(lower_text: str) -> tuple[int | None, str | None]:
    """Extract the raw numeric budget and currency from user text."""
    currency_map = {
        "gbp": "GBP", "pounds": "GBP", "pound": "GBP", "£": "GBP",
        "usd": "USD", "dollars": "USD", "dollar": "USD", "$": "USD",
        "eur": "EUR", "euros": "EUR", "euro": "EUR", "€": "EUR",
    }
    # Match patterns like "£500", "$1,500", "500 pounds", "1500 usd"
    # Symbol-first: £500, $1500, €800
    match = re.search(r"([£$€])\s*([\d,]+)", lower_text)
    if match:
        symbol = match.group(1)
        amount = int(match.group(2).replace(",", ""))
        return amount, currency_map.get(symbol, "USD")

    # Number-first: 500 pounds, 1500 usd
    match = re.search(r"([\d,]+)\s*(gbp|pounds?|usd|dollars?|eur|euros?)", lower_text)
    if match:
        amount = int(match.group(1).replace(",", ""))
        currency_word = match.group(2).lower()
        return amount, currency_map.get(currency_word, "USD")

    return None, None


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
