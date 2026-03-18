"""Preference update: changed-field detection, planning preface, selective rerun logic.

Handles what happens when a user changes preferences mid-conversation.
"""

from __future__ import annotations

from typing import Any

from src.tools.schemas import ItineraryDraft, PlanningBrief, PlanningBriefPatch


def detect_changed_fields(
    previous: PlanningBrief,
    current: PlanningBrief,
    patch: PlanningBriefPatch,
) -> set[str]:
    """Detect which fields changed between the previous and current brief."""
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


def build_planning_preface(changed_fields: set[str], has_existing_plan: bool) -> str:
    """Build a short status message for the user about what the agent is doing."""
    if not has_existing_plan:
        return "I have enough to start. I will check weather, stays, dining, and experiences in parallel, then turn them into a usable plan."
    if not changed_fields:
        return "I will lightly refine the current plan without rebuilding it from scratch."
    if changed_fields == {"pace"}:
        return "I will adjust the pacing first and keep the rest of the plan as intact as possible."
    return "I will update the current plan selectively and only recalculate the parts your change affects."
