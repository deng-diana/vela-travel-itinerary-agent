"""Daily structure builder — creates rich, time-based day plans.

Instead of fixed experience counts per slot, each time slot has a **time budget**
(e.g. morning = 3.5 hours). Experiences are filled in by their estimated duration
until the slot is full. This means a quick viewpoint (0.5h) and a landmark (1.5h)
can share a morning, while a full museum visit (3h) takes the slot on its own.
"""
from __future__ import annotations

from src.tools.schemas import DailyStructureInput, DayItem, DayPlan


# Time budget per slot (hours) by pace
_SLOT_HOURS: dict[str, dict[str, float]] = {
    "slow":     {"morning": 3.0, "afternoon": 2.5, "evening": 0.0},
    "balanced": {"morning": 3.5, "afternoon": 4.0, "evening": 2.0},
    "packed":   {"morning": 4.0, "afternoon": 4.5, "evening": 3.0},
}

# Default duration when not provided (hours)
_DEFAULT_DURATION = 1.5


def get_daily_structure(input_data: DailyStructureInput) -> list[DayPlan]:
    hotel_name = input_data.hotel_name
    restaurant_names = _dedupe_preserving_order(input_data.restaurant_names)
    experience_names = _dedupe_preserving_order(input_data.experience_names)
    durations = input_data.experience_durations or {}

    restaurant_uses: dict[str, int] = {}
    experience_uses: dict[str, int] = {}
    days: list[DayPlan] = []

    for day_number in range(1, input_data.trip_length_days + 1):
        if day_number == 1:
            days.append(
                _build_arrival_day(
                    hotel_name=hotel_name,
                    restaurants=restaurant_names,
                    restaurant_uses=restaurant_uses,
                    experiences=experience_names,
                    experience_uses=experience_uses,
                    durations=durations,
                    style_notes=input_data.style_notes,
                    must_do=input_data.must_do,
                    pace=input_data.pace,
                )
            )
            continue

        days.append(
            _build_full_day(
                day_number=day_number,
                restaurants=restaurant_names,
                experiences=experience_names,
                restaurant_uses=restaurant_uses,
                experience_uses=experience_uses,
                durations=durations,
                pace=input_data.pace,
                style_notes=input_data.style_notes,
                must_do=input_data.must_do,
            )
        )

    return days


def _build_arrival_day(
    hotel_name: str,
    restaurants: list[str],
    restaurant_uses: dict[str, int],
    experiences: list[str],
    experience_uses: dict[str, int],
    durations: dict[str, float],
    style_notes: list[str],
    must_do: list[str],
    pace: str,
) -> DayPlan:
    used_today: set[str] = set()
    dinner = _pick_next(restaurants, restaurant_uses, exclude=used_today)
    if dinner:
        used_today.add(dinner)

    # Arrival evening: 2h budget regardless of pace
    evening_budget = 2.0 if pace != "slow" else 1.5
    evening_picks = _fill_slot_by_time(
        experiences, experience_uses, durations,
        time_budget=evening_budget, exclude=used_today,
    )
    for e in evening_picks:
        used_today.add(e)

    items: list[DayItem] = [
        DayItem(
            time_label="Afternoon",
            kind="hotel",
            title=hotel_name,
            description="Check in, settle down, and use the first hours to get oriented.",
        )
    ]

    if dinner:
        items.append(DayItem(
            time_label="Dinner", kind="restaurant", title=dinner,
            description="Start close to your base with a dinner worth planning around.",
        ))

    if evening_picks:
        for i, exp in enumerate(evening_picks):
            dur = durations.get(exp, _DEFAULT_DURATION)
            desc = (
                f"A light first-night anchor (~{_fmt_dur(dur)})."
                if i == 0 else f"Nearby — easy to combine (~{_fmt_dur(dur)})."
            )
            items.append(DayItem(time_label="Evening", kind="experience", title=exp, description=desc))
    else:
        items.append(DayItem(
            time_label="Evening", kind="note", title="Soft landing",
            description="Keep the first night easy so the rest of the trip starts with energy.",
        ))

    if must_do:
        items.append(DayItem(
            time_label="Planning note", kind="note", title="Keep one must-do visible",
            description=f"Protect time later in the trip for {must_do[0]}.",
        ))

    return DayPlan(
        day_number=1,
        theme="Arrival + soft landing",
        summary=_arrival_summary(style_notes),
        items=items,
    )


def _build_full_day(
    day_number: int,
    restaurants: list[str],
    experiences: list[str],
    restaurant_uses: dict[str, int],
    experience_uses: dict[str, int],
    durations: dict[str, float],
    pace: str,
    style_notes: list[str],
    must_do: list[str],
) -> DayPlan:
    slot_hours = _SLOT_HOURS.get(pace, _SLOT_HOURS["balanced"])
    used_today: set[str] = set()

    # ── Morning: fill by time ──
    morning_picks = _fill_slot_by_time(
        experiences, experience_uses, durations,
        time_budget=slot_hours["morning"], exclude=used_today,
    )
    for e in morning_picks:
        used_today.add(e)

    # ── Lunch ──
    lunch = _pick_next(restaurants, restaurant_uses, exclude=used_today)
    if lunch:
        used_today.add(lunch)

    # ── Afternoon: fill by time ──
    afternoon_picks = _fill_slot_by_time(
        experiences, experience_uses, durations,
        time_budget=slot_hours["afternoon"], exclude=used_today,
    )
    for e in afternoon_picks:
        used_today.add(e)

    # ── Dinner ──
    dinner = _pick_next(restaurants, restaurant_uses, exclude=used_today)
    if dinner:
        used_today.add(dinner)

    # ── Evening: fill by time ──
    evening_picks = _fill_slot_by_time(
        experiences, experience_uses, durations,
        time_budget=slot_hours["evening"], exclude=used_today,
    )
    for e in evening_picks:
        used_today.add(e)

    # ── Build items ──
    items: list[DayItem] = []

    # Morning
    if morning_picks:
        _append_experience_items(items, "Morning", morning_picks, durations)
    else:
        items.append(DayItem(
            time_label="Morning", kind="note", title="Slow neighborhood start",
            description="Start nearby and keep the first block flexible.",
        ))

    # Lunch
    if lunch:
        items.append(DayItem(
            time_label="Lunch", kind="restaurant", title=lunch,
            description="Midday reset — refuel before the afternoon.",
        ))

    # Afternoon
    if afternoon_picks:
        _append_experience_items(items, "Afternoon", afternoon_picks, durations)
    elif pace != "slow":
        items.append(DayItem(
            time_label="Afternoon", kind="note", title="Protected wandering time",
            description="Leave room for cafes, shops, or a slower neighborhood drift.",
        ))

    # Dinner
    if dinner:
        items.append(DayItem(
            time_label="Dinner", kind="restaurant", title=dinner,
            description="Close the day with a dinner that feels like a real anchor.",
        ))

    # Evening
    if evening_picks:
        _append_experience_items(items, "Evening", evening_picks, durations)

    if must_do and day_number == 2:
        items.append(DayItem(
            time_label="Planning note", kind="note", title="Must-do checkpoint",
            description=f"Make sure {must_do[0]} stays protected as the plan evolves.",
        ))

    total_exp = len(morning_picks) + len(afternoon_picks) + len(evening_picks)
    total_hours = sum(
        durations.get(e, _DEFAULT_DURATION)
        for e in morning_picks + afternoon_picks + evening_picks
    )
    return DayPlan(
        day_number=day_number,
        theme=_theme_for_day(day_number, pace, style_notes),
        summary=_summary_for_day(pace, style_notes, total_exp, total_hours),
        items=items,
    )


# ---------------------------------------------------------------------------
# Slot filler: picks experiences until time budget is spent
# ---------------------------------------------------------------------------

def _fill_slot_by_time(
    options: list[str],
    uses: dict[str, int],
    durations: dict[str, float],
    time_budget: float,
    exclude: set[str] | None = None,
) -> list[str]:
    """Fill a time slot with experiences until the budget runs out.

    Picks least-used experiences first.  A 3.5h morning might get:
      - Museum (2.5h) + nearby viewpoint (0.5h), or
      - Three 1h walking-scale experiences
    """
    if time_budget <= 0 or not options:
        return []

    excluded = exclude or set()
    picks: list[str] = []
    remaining = time_budget

    while remaining > 0:
        available = [o for o in options if o not in excluded and o not in picks]
        if not available:
            break

        # Pick least-used, and among ties prefer those that fit the remaining time
        def sort_key(o: str) -> tuple[int, int, float]:
            dur = durations.get(o, _DEFAULT_DURATION)
            fits = 0 if dur <= remaining else 1  # prefer items that fit
            return (fits, uses.get(o, 0), options.index(o))

        selected = min(available, key=sort_key)
        dur = durations.get(selected, _DEFAULT_DURATION)

        # If this item doesn't fit and we already have picks, stop
        if dur > remaining and picks:
            break

        uses[selected] = uses.get(selected, 0) + 1
        picks.append(selected)
        remaining -= dur

    return picks


def _append_experience_items(
    items: list[DayItem],
    time_label: str,
    picks: list[str],
    durations: dict[str, float],
) -> None:
    """Append experience DayItems with duration-aware descriptions."""
    for i, exp in enumerate(picks):
        dur = durations.get(exp, _DEFAULT_DURATION)
        if i == 0:
            desc = f"Start here (~{_fmt_dur(dur)})."
            if time_label == "Afternoon":
                desc = f"Main afternoon anchor (~{_fmt_dur(dur)})."
            elif time_label == "Evening":
                desc = f"Evening highlight (~{_fmt_dur(dur)})."
        else:
            desc = f"Nearby — easy to combine (~{_fmt_dur(dur)})."
        items.append(DayItem(time_label=time_label, kind="experience", title=exp, description=desc))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_dur(hours: float) -> str:
    """Format duration: 1.5 → '1.5h', 0.5 → '30 min', 2.0 → '2h'."""
    if hours < 1:
        return f"{int(hours * 60)} min"
    if hours == int(hours):
        return f"{int(hours)}h"
    return f"{hours:.1f}h"


def _pick_next(
    options: list[str],
    uses: dict[str, int],
    exclude: set[str] | None = None,
) -> str | None:
    if not options:
        return None
    excluded = exclude or set()
    available = [option for option in options if option not in excluded]
    if not available:
        available = options[:]
    selected = min(available, key=lambda option: (uses.get(option, 0), options.index(option)))
    uses[selected] = uses.get(selected, 0) + 1
    return selected


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def _theme_for_day(day_number: int, pace: str, style_notes: list[str]) -> str:
    notes = " ".join(style_notes).lower()
    if "romantic" in notes:
        return "Romantic city rhythm"
    if "hidden" in notes or "local" in notes:
        return "Local texture day"
    if day_number == 2:
        return "Core city day"
    if pace == "slow":
        return "Slow discovery"
    if pace == "packed":
        return "High-energy sweep"
    return "Layered exploration"


def _summary_for_day(
    pace: str,
    style_notes: list[str],
    experience_count: int,
    total_hours: float = 0,
) -> str:
    notes = " ".join(style_notes).lower()
    if "romantic" in notes:
        return "A gentler day with more atmosphere, fewer hard pivots, and room for one memorable dinner."
    if "hidden" in notes or "local" in notes:
        return "A day designed to feel more local, with stronger texture and less generic stop-hopping."
    if pace == "slow":
        return "A slower day with clear anchors and enough room to linger when something clicks."
    hours_str = f" (~{total_hours:.0f}h of activities)" if total_hours else ""
    if pace == "packed":
        return f"A packed day with {experience_count} experiences{hours_str} plus meals."
    if experience_count >= 4:
        return f"A full day with {experience_count} highlights grouped by area{hours_str}, plus meals."
    return f"A balanced day with {experience_count} experiences{hours_str}, meals, and room to breathe."


def _arrival_summary(style_notes: list[str]) -> str:
    notes = " ".join(style_notes).lower()
    if "romantic" in notes:
        return "Settle in slowly, keep the first evening atmospheric, and let the trip open with one easy highlight."
    if "hidden" in notes or "local" in notes:
        return "Start gently and use the first night to get a local read on the area around your base."
    return "Settle in, protect your energy, and begin with one clear first-night anchor."
