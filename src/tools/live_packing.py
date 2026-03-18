"""Packing suggestions tool.

Generates a tailored packing list based on destination, weather conditions, planned
activities, and trip length. Uses actual weather data from get_weather when available.
"""
from __future__ import annotations

from src.tools.schemas import PackingCategory, PackingInput, PackingSuggestions


def get_packing_suggestions(inp: PackingInput) -> PackingSuggestions:
    temp = inp.avg_temp_c
    conditions = (inp.conditions_summary or "").lower()
    activities_lower = [a.lower() for a in inp.activities]
    days = inp.trip_length_days
    party_lower = (inp.travel_party or "").lower()

    # Determine climate profile
    is_hot = temp is not None and temp >= 25
    is_cold = temp is not None and temp <= 10
    is_rainy = any(w in conditions for w in ("rain", "wet", "humid", "shower", "monsoon", "typhoon"))
    is_snowy = any(w in conditions for w in ("snow", "icy", "freezing")) or (temp is not None and temp <= 0)
    is_mixed = not is_hot and not is_cold and not is_snowy

    # ── Clothing ────────────────────────────────────────────────────────────
    clothing: list[str] = []

    if is_hot:
        clothing += ["Light breathable shirts (1 per day)", "Shorts or light trousers", "Sundress or summer outfit (optional)"]
    elif is_cold:
        clothing += ["Thermal base layers", "Mid-layer fleece or sweater", "Warm insulated jacket", "Warm trousers"]
    elif is_snowy:
        clothing += ["Heavy winter coat", "Thermal base layers (top & bottom)", "Waterproof trousers", "Warm jumpers (2-3)"]
    else:
        clothing += [f"T-shirts or light tops ({min(days, 5)} items)", "Light jacket or cardigan for evenings"]

    # Universal
    clothing += [
        "Comfortable walking shoes (broken in)",
        "Underwear & socks (1 per day + 2 spare)",
        "Pyjamas / sleepwear",
    ]

    if is_rainy:
        clothing += ["Compact travel umbrella", "Waterproof jacket or poncho"]
    if any(w in " ".join(activities_lower) for w in ("temple", "shrine", "mosque", "church", "religious")):
        clothing.append("Modest cover-up for religious sites (shoulders + knees covered)")
    if any(w in " ".join(activities_lower) for w in ("beach", "pool", "swim", "snorkel", "dive")):
        clothing += ["Swimwear (1-2 sets)", "Quick-dry travel towel", "Flip-flops / sandals"]
    if any(w in " ".join(activities_lower) for w in ("hike", "trek", "outdoor", "nature", "mountain")):
        clothing += ["Sturdy hiking shoes or trail runners", "Moisture-wicking socks"]
    if any(w in " ".join(activities_lower) for w in ("dinner", "restaurant", "fine", "show", "theatre")):
        clothing.append("One smart-casual outfit for nicer restaurants or evenings out")
    if is_cold or is_snowy:
        clothing += ["Hat / beanie", "Gloves", "Scarf", "Wool or thermal socks"]

    # ── Documents ───────────────────────────────────────────────────────────
    documents = [
        "Passport (valid 6+ months beyond travel dates)",
        "Printed or digital copies of all bookings (hotel, flights, tours)",
        "Travel insurance documents",
        "Local currency or debit card that waives foreign fees",
        "Emergency contacts (hotel, embassy, home)",
    ]
    if days >= 7:
        documents.append("Physical backup of passport photo page")

    # ── Toiletries ───────────────────────────────────────────────────────────
    toiletries = [
        "Toothbrush + toothpaste",
        "Deodorant",
        "Shampoo / conditioner (travel sizes or solid bars)",
        "Face wash & moisturiser",
        "Sunscreen SPF 30+",
        "Lip balm with SPF",
        "Personal medications (clearly labelled, in carry-on)",
        "Basic first aid: plasters, pain relief, stomach tablets, antihistamine",
    ]
    if is_hot:
        toiletries += ["Extra sunscreen (hard to find abroad)", "Insect repellent"]
    if is_rainy or is_hot:
        toiletries.append("Antifungal powder or spray")
    if days >= 7:
        toiletries.append("Travel laundry detergent sheets or small bottle")

    # ── Tech ────────────────────────────────────────────────────────────────
    tech = [
        "Universal travel adapter",
        "Phone + charging cable",
        "Portable power bank (10,000+ mAh)",
        "Earbuds / headphones",
        "Camera (if not using phone)",
    ]
    if days >= 5:
        tech.append("Laptop or tablet (if working/streaming)")
    if any(w in " ".join(activities_lower) for w in ("hike", "trek", "outdoor", "map", "navigation")):
        tech.append("Offline maps downloaded (Google Maps / Maps.me)")

    # ── Extras ───────────────────────────────────────────────────────────────
    extras = [
        "Reusable water bottle",
        "Day pack / small backpack for sightseeing",
        "Luggage locks",
    ]
    if is_hot or is_rainy:
        extras.append("Ziplock bags (protect electronics + wet swimwear)")
    if "couple" in party_lower:
        extras.append("Shared packing cube set to consolidate luggage")
    if "family" in party_lower:
        extras += ["Snacks for kids", "Small foldable bag for souvenirs"]
    if days >= 7:
        extras.append("Packing cubes for organised luggage")
    extras.append("Reusable shopping bag (many destinations charge for carrier bags)")

    # Build weather note
    if temp is not None:
        temp_desc = f"{temp}°C average"
    elif is_hot:
        temp_desc = "warm weather"
    elif is_cold:
        temp_desc = "cool/cold weather"
    else:
        temp_desc = "mild weather"

    rain_note = " Expect rain — pack waterproofs." if is_rainy else ""
    snow_note = " Freezing conditions — heavy winter layers essential." if is_snowy else ""
    weather_note = f"{inp.destination} in {inp.month}: {temp_desc}.{rain_note}{snow_note}"

    categories = [
        PackingCategory(category="Clothing", items=clothing),
        PackingCategory(category="Documents & Money", items=documents),
        PackingCategory(category="Toiletries & Health", items=toiletries),
        PackingCategory(category="Tech & Gadgets", items=tech),
        PackingCategory(category="Extras & Travel Comfort", items=extras),
    ]

    return PackingSuggestions(
        destination=inp.destination,
        month=inp.month,
        weather_note=weather_note,
        categories=categories,
    )
