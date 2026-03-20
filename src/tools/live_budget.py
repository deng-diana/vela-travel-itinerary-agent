"""Budget estimation tool.

Computes a realistic trip cost breakdown using actual hotel nightly rate (from get_hotels
results) plus tier-based estimates for food, activities, and transport.
"""
from __future__ import annotations

from src.tools.schemas import BudgetEstimate, BudgetInput, BudgetLineItem, BudgetTier

# Per-day food spend by budget tier (USD, per person)
_DAILY_FOOD: dict[BudgetTier, dict[str, int]] = {
    "budget": {"lunch": 12, "dinner": 20, "snacks": 8},
    "mid":    {"lunch": 28, "dinner": 55, "snacks": 15},
    "luxury": {"lunch": 60, "dinner": 110, "snacks": 25},
}

# Per-day local transport (metro, taxis, buses)
_DAILY_TRANSPORT: dict[BudgetTier, int] = {
    "budget": 8,
    "mid":    18,
    "luxury": 40,
}

# Per-day activities (museums, tours, entry fees)
_DAILY_ACTIVITIES: dict[BudgetTier, int] = {
    "budget": 12,
    "mid":    35,
    "luxury": 85,
}

# Default nightly hotel rates when not provided
_DEFAULT_NIGHTLY: dict[BudgetTier, int] = {
    "budget": 75,
    "mid":    170,
    "luxury": 380,
}


def estimate_budget(inp: BudgetInput) -> BudgetEstimate:
    tier = inp.budget
    days = inp.trip_length_days

    nightly = inp.hotel_nightly_rate_usd or _DEFAULT_NIGHTLY[tier]
    accommodation = nightly * days

    food_rates = _DAILY_FOOD[tier]
    daily_food = food_rates["lunch"] + food_rates["dinner"] + food_rates["snacks"]
    food_total = daily_food * days

    activity_daily = inp.experience_daily_cost_usd or _DAILY_ACTIVITIES[tier]
    # Day 1 is lighter (arrival); last day may be departure — reduce by ~30%
    activity_days = max(days - 1, 1)
    activities_total = activity_daily * activity_days

    transport_daily = _DAILY_TRANSPORT[tier]
    transport_total = transport_daily * days

    subtotal = accommodation + food_total + activities_total + transport_total
    misc_total = int(subtotal * 0.07)  # tips, incidentals, small souvenirs
    grand_total = subtotal + misc_total
    daily_average = grand_total // days

    notes: list[str] = []
    if inp.travel_party:
        party_lower = inp.travel_party.lower()
        if "couple" in party_lower or "2" in party_lower:
            notes.append(f"Total for 2 people: ~${grand_total * 2:,} USD")
        elif "family" in party_lower:
            notes.append("Family pricing: multiply by number of adults; children ~60% of adult cost.")
    notes.append("Flights not included. Prices are estimates in USD.")

    line_items = [
        BudgetLineItem(
            category="Accommodation",
            amount_usd=accommodation,
            detail=f"{days} nights × ~${nightly}/night",
        ),
        BudgetLineItem(
            category="Food & Drinks",
            amount_usd=food_total,
            detail=f"~${daily_food}/day (lunch + dinner + snacks)",
        ),
        BudgetLineItem(
            category="Activities & Experiences",
            amount_usd=activities_total,
            detail=f"~${activity_daily}/day × {activity_days} days",
        ),
        BudgetLineItem(
            category="Local Transport",
            amount_usd=transport_total,
            detail=f"~${transport_daily}/day (metro, bus, taxi)",
        ),
        BudgetLineItem(
            category="Miscellaneous",
            amount_usd=misc_total,
            detail="Tips, incidentals, light shopping (~7%)",
        ),
    ]

    # Compare against user-stated budget cap (approximate conversion to USD)
    user_amount = inp.user_budget_amount
    user_currency = inp.user_budget_currency
    over_budget = False
    if user_amount:
        _fx_to_usd = {"GBP": 1.27, "EUR": 1.08, "USD": 1.0}
        user_budget_usd = int(user_amount * _fx_to_usd.get(user_currency or "USD", 1.0))
        if grand_total > user_budget_usd:
            over_budget = True
            overage = grand_total - user_budget_usd
            notes.insert(0,
                f"⚠️ Estimated cost (~${grand_total:,}) exceeds your stated "
                f"{user_currency or 'USD'} {user_amount:,} budget (~${user_budget_usd:,} USD) "
                f"by ~${overage:,}. Consider shorter stay or budget-tier options."
            )

    return BudgetEstimate(
        destination=inp.destination,
        trip_length_days=days,
        budget_tier=tier,
        currency="USD",
        accommodation_total_usd=accommodation,
        food_total_usd=food_total,
        activities_total_usd=activities_total,
        transport_total_usd=transport_total,
        misc_total_usd=misc_total,
        grand_total_usd=grand_total,
        daily_average_usd=daily_average,
        line_items=line_items,
        notes=notes,
        user_budget_amount=user_amount,
        user_budget_currency=user_currency,
        over_budget=over_budget,
    )
