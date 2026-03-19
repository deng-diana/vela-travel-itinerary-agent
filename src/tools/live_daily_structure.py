from __future__ import annotations

from src.tools.schemas import DailyStructureInput, DayItem, DayPlan


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
    dinner = _pick_next(restaurants, restaurant_uses)
    evening_anchor = _pick_next(experiences, experience_uses) if pace in {"balanced", "packed"} else None

    items = [
        DayItem(
            time_label="Afternoon",
            kind="hotel",
            title=hotel_name,
            description="Check in, settle down, and use the first hours to get oriented without over-scheduling.",
        )
    ]

    if dinner:
        items.append(
            DayItem(
                time_label="Dinner",
                kind="restaurant",
                title=dinner,
                description="Start close to your base with one dinner worth planning around, rather than stretching arrival day too far.",
            )
        )

    if evening_anchor:
        items.append(
            DayItem(
                time_label="Evening",
                kind="experience",
                title=evening_anchor,
                description="If energy holds up, use this as a light first-night anchor instead of forcing a full sightseeing block.",
            )
        )
    else:
        items.append(
            DayItem(
                time_label="Evening",
                kind="note",
                title="Soft landing",
                description="Keep the first night easy so the rest of the trip starts with energy instead of drag.",
            )
        )

    if must_do:
        items.append(
            DayItem(
                time_label="Planning note",
                kind="note",
                title="Keep one must-do visible",
                description=f"Protect time later in the trip for {must_do[0]} so the plan still feels personal, not generic.",
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
    used_today: set[str] = set()
    morning = _pick_next(experiences, experience_uses, exclude=used_today)
    if morning:
        used_today.add(morning)

    lunch = _pick_next(restaurants, restaurant_uses, exclude=used_today)
    if lunch:
        used_today.add(lunch)

    afternoon = None
    if pace in {"balanced", "packed"}:
        afternoon = _pick_next(experiences, experience_uses, exclude=used_today)
        if afternoon:
            used_today.add(afternoon)

    dinner = _pick_next(restaurants, restaurant_uses, exclude=used_today)
    if dinner:
        used_today.add(dinner)

    evening = None
    if pace == "packed":
        evening = _pick_next(experiences, experience_uses, exclude=used_today)
        if evening:
            used_today.add(evening)

    items: list[DayItem] = []

    if morning:
        items.append(
            DayItem(
                time_label="Morning",
                kind="experience",
                title=morning,
                description="Use this as the first strong anchor while energy is high and the day still feels open.",
            )
        )
    else:
        items.append(
            DayItem(
                time_label="Morning",
                kind="note",
                title="Slow neighborhood start",
                description="Start nearby and keep the first block flexible so the route can tighten around what feels best on the ground.",
            )
        )

    if lunch:
        items.append(
            DayItem(
                time_label="Lunch",
                kind="restaurant",
                title=lunch,
                description="Use lunch as the midday reset, not just a filler stop, so the afternoon still has shape.",
            )
        )

    if afternoon:
        items.append(
            DayItem(
                time_label="Afternoon",
                kind="experience",
                title=afternoon,
                description="This keeps the second half of the day purposeful without sending the plan into a city-wide zigzag.",
            )
        )
    elif pace != "slow":
        items.append(
            DayItem(
                time_label="Afternoon",
                kind="note",
                title="Protected wandering time",
                description="Leave room here for cafés, shops, or a slower neighborhood drift instead of over-programming every hour.",
            )
        )

    if dinner:
        items.append(
            DayItem(
                time_label="Dinner",
                kind="restaurant",
                title=dinner,
                description="Close the day with a dinner that feels like a real anchor, not an afterthought.",
            )
        )

    if evening:
        items.append(
            DayItem(
                time_label="Evening",
                kind="experience",
                title=evening,
                description="Use this as the late-day payoff if you still want one more memorable stop.",
            )
        )

    if must_do and day_number == 2:
        items.append(
            DayItem(
                time_label="Planning note",
                kind="note",
                title="Must-do checkpoint",
                description=f"Make sure {must_do[0]} stays protected as the plan evolves.",
            )
        )

    return DayPlan(
        day_number=day_number,
        theme=_theme_for_day(day_number, pace, style_notes),
        summary=_summary_for_day(pace, style_notes, morning, afternoon, dinner),
        items=items,
    )


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
    morning: str | None,
    afternoon: str | None,
    dinner: str | None,
) -> str:
    notes = " ".join(style_notes).lower()
    if "romantic" in notes:
        return "A gentler day with more atmosphere, fewer hard pivots, and room for one memorable dinner."
    if "hidden" in notes or "local" in notes:
        return "A day designed to feel more local, with stronger texture and less generic stop-hopping."
    if pace == "slow":
        return "A slower day with one main anchor, a proper meal break, and enough room to linger when something clicks."
    if pace == "packed":
        return "A denser day that still keeps clear anchors from morning through evening."
    if morning and afternoon and dinner:
        return "A balanced day with a clear morning anchor, a second strong stop later on, and a dinner worth holding onto."
    return "A balanced day built to feel structured without becoming rigid."


def _arrival_summary(style_notes: list[str]) -> str:
    notes = " ".join(style_notes).lower()
    if "romantic" in notes:
        return "Settle in slowly, keep the first evening atmospheric, and let the trip open with one easy highlight."
    if "hidden" in notes or "local" in notes:
        return "Start gently and use the first night to get a local read on the area around your base."
    return "Settle in, protect your energy, and begin with one clear first-night anchor."
