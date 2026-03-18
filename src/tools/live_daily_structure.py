from __future__ import annotations

from src.tools.schemas import DailyStructureInput, DayItem, DayPlan


def get_daily_structure(input_data: DailyStructureInput) -> list[DayPlan]:
    hotel_name = input_data.hotel_name
    restaurant_names = input_data.restaurant_names[:]
    experience_names = input_data.experience_names[:]
    style_notes = input_data.style_notes[:]
    must_do = input_data.must_do[:]

    days: list[DayPlan] = []
    for day_number in range(1, input_data.trip_length_days + 1):
        if day_number == 1:
            items = [
                DayItem(
                    time_label="Afternoon",
                    kind="hotel",
                    title=hotel_name,
                    description="Check in, settle down, and use the first hours to get oriented without over-scheduling.",
                ),
                DayItem(
                    time_label="Early evening",
                    kind="note",
                    title="Soft landing",
                    description="Keep the first evening light so the rest of the trip starts with energy instead of drag.",
                ),
            ]
            if restaurant_names:
                items.append(
                    DayItem(
                        time_label="Dinner",
                        kind="restaurant",
                        title=restaurant_names[0],
                        description="Start with one strong meal near your base rather than crossing the city on arrival day.",
                    )
                )

            if must_do:
                items.append(
                    DayItem(
                        time_label="Planning note",
                        kind="note",
                        title="Keep one must-do in view",
                        description=f"Make room for {must_do[0]} so the trip still feels personally meaningful.",
                    )
                )

            days.append(
                DayPlan(
                    day_number=1,
                    theme="Arrival + soft landing",
                    summary=_arrival_summary(style_notes),
                    items=items,
                )
            )
            continue

        experience = experience_names[(day_number - 2) % len(experience_names)] if experience_names else None
        lunch = restaurant_names[(day_number - 1) % len(restaurant_names)] if restaurant_names else None
        dinner = restaurant_names[day_number % len(restaurant_names)] if len(restaurant_names) > 1 else lunch

        items = [
            DayItem(
                time_label="Morning",
                kind="note",
                title="Stay geographically tight",
                description="Cluster the day so movement feels efficient and the plan leaves space for spontaneous detours.",
            )
        ]

        if experience:
            items.append(
                DayItem(
                    time_label=_best_time_for_day(day_number, input_data.pace),
                    kind="experience",
                    title=experience,
                    description="Use this as the main experiential anchor for the day.",
                )
            )

        if lunch:
            items.append(
                DayItem(
                    time_label="Lunch",
                    kind="restaurant",
                    title=lunch,
                    description="A reliable midday stop that supports the neighborhood flow instead of interrupting it.",
                )
            )

        if dinner and dinner != lunch:
            items.append(
                DayItem(
                    time_label="Dinner",
                    kind="restaurant",
                    title=dinner,
                    description="Close the day with a meal that fits the mood and keeps the pacing coherent.",
                )
            )

        days.append(
            DayPlan(
                day_number=day_number,
                theme=_theme_for_day(day_number, input_data.pace, style_notes),
                summary=_summary_for_day(input_data.pace, style_notes),
                items=items,
            )
        )

    return days


def _theme_for_day(day_number: int, pace: str, style_notes: list[str]) -> str:
    if day_number == 2:
        return "Neighborhood immersion"
    if any("romantic" in note.lower() for note in style_notes):
        return "Romantic city rhythm"
    if pace == "slow":
        return "Slow discovery"
    if pace == "packed":
        return "High-energy coverage"
    return "Balanced exploration"


def _summary_for_day(pace: str, style_notes: list[str]) -> str:
    if any("romantic" in note.lower() for note in style_notes):
        return "A gentler day with more atmosphere, fewer hard pivots, and room for memorable pauses."
    if any("local" in note.lower() or "hidden" in note.lower() for note in style_notes):
        return "A day shaped to feel more local, with fewer generic stops and stronger neighborhood texture."
    if pace == "slow":
        return "A slower day with room to linger and adjust in the moment."
    if pace == "packed":
        return "A denser day built to cover more ground without becoming chaotic."
    return "A balanced day built around one area and a few strong anchors."


def _best_time_for_day(day_number: int, pace: str) -> str:
    if pace == "slow":
        return "Afternoon"
    if pace == "packed":
        return "Morning"
    return "Afternoon" if day_number % 2 == 0 else "Morning"


def _arrival_summary(style_notes: list[str]) -> str:
    if any("romantic" in note.lower() for note in style_notes):
        return "Settle in slowly, protect your energy, and start with one atmospheric first anchor."
    return "Settle in, protect your energy, and begin with a clear first anchor."
