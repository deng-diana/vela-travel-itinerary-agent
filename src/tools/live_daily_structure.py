"""Daily structure builder — creates rich, multi-activity day plans.

Each time slot (morning, afternoon, evening) gets 2-3 experiences rather than
just one, making the itinerary feel like a real travel guide. Experiences are
distributed to give each day a full, actionable schedule.
"""
from __future__ import annotations

from src.tools.schemas import DailyStructureInput, DayItem, DayPlan


# How many experiences per time slot by pace
_SLOT_COUNTS: dict[str, dict[str, int]] = {
    "slow":     {"morning": 1, "afternoon": 1, "evening": 0},
    "balanced": {"morning": 2, "afternoon": 2, "evening": 1},
    "packed":   {"morning": 2, "afternoon": 3, "evening": 2},
}


def get_daily_structure(input_data: DailyStructureInput) -> list[DayPlan]:
    hotel_name = input_data.hotel_name
    restaurant_names = _dedupe_preserving_order(input_data.restaurant_names)
    experience_names = _dedupe_preserving_order(input_data.experience_names)

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
    style_notes: list[str],
    must_do: list[str],
    pace: str,
) -> DayPlan:
    used_today: set[str] = set()
    dinner = _pick_next(restaurants, restaurant_uses, exclude=used_today)
    if dinner:
        used_today.add(dinner)

    # Even on arrival day, give 1-2 evening experiences if pace allows
    evening_count = 1 if pace == "slow" else 2
    evening_picks = _pick_multiple(experiences, experience_uses, count=evening_count, exclude=used_today)
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
        items.append(
            DayItem(
                time_label="Dinner",
                kind="restaurant",
                title=dinner,
                description="Start close to your base with a dinner worth planning around.",
            )
        )

    if evening_picks:
        for i, exp in enumerate(evening_picks):
            desc = "A light first-night anchor to ease into the city." if i == 0 else "Nearby — easy to combine with the previous stop."
            items.append(
                DayItem(
                    time_label="Evening",
                    kind="experience",
                    title=exp,
                    description=desc,
                )
            )
    else:
        items.append(
            DayItem(
                time_label="Evening",
                kind="note",
                title="Soft landing",
                description="Keep the first night easy so the rest of the trip starts with energy.",
            )
        )

    if must_do:
        items.append(
            DayItem(
                time_label="Planning note",
                kind="note",
                title="Keep one must-do visible",
                description=f"Protect time later in the trip for {must_do[0]}.",
            )
        )

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
    pace: str,
    style_notes: list[str],
    must_do: list[str],
) -> DayPlan:
    slot_counts = _SLOT_COUNTS.get(pace, _SLOT_COUNTS["balanced"])
    used_today: set[str] = set()

    # ── Morning experiences ──
    morning_picks = _pick_multiple(
        experiences, experience_uses,
        count=slot_counts["morning"], exclude=used_today,
    )
    for e in morning_picks:
        used_today.add(e)

    # ── Lunch ──
    lunch = _pick_next(restaurants, restaurant_uses, exclude=used_today)
    if lunch:
        used_today.add(lunch)

    # ── Afternoon experiences ──
    afternoon_picks = _pick_multiple(
        experiences, experience_uses,
        count=slot_counts["afternoon"], exclude=used_today,
    )
    for e in afternoon_picks:
        used_today.add(e)

    # ── Dinner ──
    dinner = _pick_next(restaurants, restaurant_uses, exclude=used_today)
    if dinner:
        used_today.add(dinner)

    # ── Evening experiences ──
    evening_picks = _pick_multiple(
        experiences, experience_uses,
        count=slot_counts["evening"], exclude=used_today,
    )
    for e in evening_picks:
        used_today.add(e)

    # ── Build items ──
    items: list[DayItem] = []

    # Morning
    if morning_picks:
        for i, exp in enumerate(morning_picks):
            desc = (
                "Start the day here while energy is high."
                if i == 0 else "Close by — combine with the previous stop before lunch."
            )
            items.append(DayItem(time_label="Morning", kind="experience", title=exp, description=desc))
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
        for i, exp in enumerate(afternoon_picks):
            if i == 0:
                desc = "Main afternoon anchor."
            elif i == 1:
                desc = "Nearby — easy to walk to from the previous stop."
            else:
                desc = "If time allows, squeeze in one more highlight in the area."
            items.append(DayItem(time_label="Afternoon", kind="experience", title=exp, description=desc))
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
        for i, exp in enumerate(evening_picks):
            desc = (
                "Evening highlight — a memorable way to end the day."
                if i == 0 else "Combine with the previous evening stop if energy holds up."
            )
            items.append(DayItem(time_label="Evening", kind="experience", title=exp, description=desc))

    if must_do and day_number == 2:
        items.append(DayItem(
            time_label="Planning note", kind="note", title="Must-do checkpoint",
            description=f"Make sure {must_do[0]} stays protected as the plan evolves.",
        ))

    # Count experiences for summary
    total_exp = len(morning_picks) + len(afternoon_picks) + len(evening_picks)
    return DayPlan(
        day_number=day_number,
        theme=_theme_for_day(day_number, pace, style_notes),
        summary=_summary_for_day(pace, style_notes, total_exp),
        items=items,
    )


def _pick_multiple(
    options: list[str],
    uses: dict[str, int],
    count: int,
    exclude: set[str] | None = None,
) -> list[str]:
    """Pick up to `count` distinct items from options, least-used first."""
    if not options or count <= 0:
        return []

    excluded = exclude or set()
    picks: list[str] = []
    for _ in range(count):
        available = [o for o in options if o not in excluded and o not in picks]
        if not available:
            break
        selected = min(available, key=lambda o: (uses.get(o, 0), options.index(o)))
        uses[selected] = uses.get(selected, 0) + 1
        picks.append(selected)
    return picks


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
) -> str:
    notes = " ".join(style_notes).lower()
    if "romantic" in notes:
        return "A gentler day with more atmosphere, fewer hard pivots, and room for one memorable dinner."
    if "hidden" in notes or "local" in notes:
        return "A day designed to feel more local, with stronger texture and less generic stop-hopping."
    if pace == "slow":
        return "A slower day with clear anchors and enough room to linger when something clicks."
    if pace == "packed":
        return f"A packed day with {experience_count} experiences plus meals — bring your walking shoes."
    if experience_count >= 4:
        return f"A full day with {experience_count} highlights grouped by area, plus meals."
    return "A balanced day built to feel structured without becoming rigid."


def _arrival_summary(style_notes: list[str]) -> str:
    notes = " ".join(style_notes).lower()
    if "romantic" in notes:
        return "Settle in slowly, keep the first evening atmospheric, and let the trip open with one easy highlight."
    if "hidden" in notes or "local" in notes:
        return "Start gently and use the first night to get a local read on the area around your base."
    return "Settle in, protect your energy, and begin with one clear first-night anchor."
