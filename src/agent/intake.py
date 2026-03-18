"""Intake module: brief extraction, slot detection, clarifying question generation.

Extracted from orchestrator.py to keep intake-related logic cohesive and testable.
All functions are standalone; pass `client` and `model` where Claude API calls are needed.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from src.agent.llm_helpers import extract_text, normalize_blocks, parse_json_block
from src.tools.schemas import ItineraryDraft, PlanningBrief, PlanningBriefPatch

# ---------------------------------------------------------------------------
# Required brief fields
# ---------------------------------------------------------------------------

# Fields we truly need before planning can start (bare minimum).
ESSENTIAL_FIELDS = ("destination", "trip_length_days")

# These are filled via smart defaults if the user doesn't mention them.
# We do NOT ask about them upfront — the user can refine after seeing the first draft.
NICE_TO_HAVE_FIELDS = (
    "dates_or_month",
    "travel_party",
    "budget",
    "pace",
)

# Smart defaults applied when user doesn't provide nice-to-have info
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
        "- destination: the TARGET city/country of the trip. If the user says 'from London to Paris', "
        "destination is Paris (not London, not 'London to Paris'). Extract only the destination city/country.\n"
        "- Map budget to one of: budget, mid, luxury. '£1000' or '$1500' for a few days → mid.\n"
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


def missing_essential_fields(brief: PlanningBrief) -> list[str]:
    """Check which essential (blocking) fields are still missing."""
    missing: list[str] = []
    if not brief.destination:
        missing.append("destination")
    if not brief.trip_length_days:
        missing.append("trip_length_days")
    return missing


def missing_nice_to_have_fields(brief: PlanningBrief) -> list[str]:
    """Nice-to-have fields we ask about in the first follow-up (non-blocking)."""
    missing: list[str] = []
    if not brief.dates_or_month:
        missing.append("dates_or_month")
    if not brief.travel_party:
        missing.append("travel_party")
    if not brief.budget:
        missing.append("budget")
    if not brief.priorities:
        missing.append("priorities")
    # constraints/must-avoid intentionally excluded — user raises these during planning
    return missing


def missing_landing_followup_fields(brief: PlanningBrief) -> list[str]:
    """Fields to ask about in the single landing follow-up.

    Includes essential + nice-to-have (dates, party, budget, priorities).
    constraints/must-avoid are excluded — user can mention them any time during planning.
    """
    return missing_essential_fields(brief) + missing_nice_to_have_fields(brief)


def apply_smart_defaults(brief: PlanningBrief) -> PlanningBrief:
    """Fill in sensible defaults for missing non-essential fields."""
    data = brief.model_dump(mode="python")
    smart_defaults = {
        "dates_or_month": _default_dates_or_month(),
        "travel_party": "solo",
        "budget": "mid",
        "pace": "balanced",
    }
    for field, default in smart_defaults.items():
        if not data.get(field):
            data[field] = default
    return PlanningBrief.model_validate(data)


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


def build_landing_followup_reply(_brief: PlanningBrief, missing: list[str], user_message: str) -> str:
    """Ask for the bare minimum needed to start — destination and/or trip length only."""
    joined = _join_field_labels(missing, user_message)
    if _looks_like_chinese(user_message):
        return f"告诉我{joined}，我马上开始规划！"
    return f"Just tell me {joined} and I'll start building your itinerary right away!"


def build_workspace_handoff_reply(_brief: PlanningBrief, missing: list[str], user_message: str) -> str:
    """Move the conversation into the workspace without staying stuck in landing."""
    joined = _join_field_labels(missing, user_message)
    if _looks_like_chinese(user_message):
        return (
            f"我先把工作区打开继续往下推进，不过在我真正排出路线前，还需要你补一下：{joined}。"
            "你直接在左边继续回我，我一拿到这些信息就接着更新。"
        )
    return (
        f"I've opened the workspace so we can keep moving, but I still need {joined} "
        "before I can build a real itinerary. Reply here on the left and I'll update it as soon as I have that."
    )


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
        "destination": "Ask which city or region they'd like to visit.",
        "trip_length_days": "Ask how many days they have for the trip.",
    }
    try:
        response = client.messages.create(
            model=model,
            max_tokens=300,
            system=(
                "You write a very short, warm clarifying message for a travel-planning assistant.\n"
                "Reply in plain text only.\n"
                "Reply in the same language the user is writing in.\n"
                "Rules:\n"
                "- Only ask for the ESSENTIAL missing fields listed (destination and/or trip length).\n"
                "- Do NOT repeat any information the user already gave.\n"
                "- Keep it to 1-2 short sentences max. No bullet lists.\n"
                "- Sound warm, casual, and eager to start planning.\n"
                "- Make it clear that once you know these basics, you'll start building immediately.\n"
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
    parts: list[str] = []
    if "destination" in missing:
        parts.append("which city you'd like to visit")
    if "trip_length_days" in missing:
        parts.append("how many days you have")

    if not parts:
        return "I have enough to get started — building your itinerary now!"

    joined = " and ".join(parts)
    return f"I'm almost ready to start planning! Just need to know {joined}, and I'll get right to it."


# ---------------------------------------------------------------------------
# Field-label helpers
# ---------------------------------------------------------------------------


def _join_field_labels(fields: list[str], user_message: str) -> str:
    labels = [_field_label(field, user_message) for field in fields]
    if not labels:
        return "a couple more trip details"
    if len(labels) == 1:
        return labels[0]
    if _looks_like_chinese(user_message):
        return "、".join(labels[:-1]) + f"和{labels[-1]}"
    if len(labels) == 2:
        return " and ".join(labels)
    return ", ".join(labels[:-1]) + f", and {labels[-1]}"


def _field_label(field: str, user_message: str) -> str:
    chinese = _looks_like_chinese(user_message)
    labels = {
        "destination": ("想去哪里", "where you'd like to go"),
        "trip_length_days": ("玩几天", "how many days you have"),
        "dates_or_month": ("大概什么时候或几月", "rough dates or month"),
        "travel_party": ("几个人一起去", "who's traveling"),
        "budget": ("预算大概什么范围", "your budget range"),
        "priorities": ("这趟最看重什么", "what matters most on this trip"),
    }
    zh_label, en_label = labels.get(field, ("补充偏好", "a missing trip detail"))
    return zh_label if chinese else en_label


def _looks_like_chinese(user_message: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in user_message)


def _default_dates_or_month() -> str:
    return datetime.now().strftime("%B")


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
