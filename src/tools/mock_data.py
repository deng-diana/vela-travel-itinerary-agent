from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from src.tools.schemas import (
    DailyStructureInput,
    DayItem,
    DayPlan,
    ExperienceOption,
    ExperienceSearchInput,
    HotelOption,
    HotelSearchInput,
    Pace,
    RestaurantOption,
    RestaurantSearchInput,
    WeatherInput,
    WeatherSummary,
)

T = TypeVar("T")


@dataclass(frozen=True)
class DestinationProfile:
    name: str
    weather_by_month: dict[str, WeatherSummary]
    hotels: list[HotelOption]
    restaurants: list[RestaurantOption]
    experiences: list[ExperienceOption]


TOKYO = DestinationProfile(
    name="Tokyo",
    weather_by_month={
        "august": WeatherSummary(
            destination="Tokyo",
            month="August",
            avg_temp_c=29,
            rainfall_mm=155,
            conditions_summary="Warm, humid, and often rainy in short bursts.",
            packing_notes=[
                "Pack breathable layers and a compact umbrella.",
                "Plan shaded or indoor activities for mid-afternoon.",
                "Choose comfortable walking shoes for humid days.",
            ],
        ),
    },
    hotels=[
        HotelOption(
            id="tokyo-aoyama-terrace",
            name="Aoyama Terrace Hotel",
            neighborhood="Aoyama",
            category="mid",
            nightly_rate_usd=220,
            affiliate_link="https://travel.vela.example/hotels/aoyama-terrace",
            key_highlights=["Quiet boutique feel", "Easy evening dining access", "Strong design aesthetic"],
            short_description="A calm mid-range boutique stay close to food-forward neighborhoods.",
        ),
        HotelOption(
            id="tokyo-shibuya-house",
            name="Shibuya House Hotel",
            neighborhood="Shibuya",
            category="mid",
            nightly_rate_usd=245,
            affiliate_link="https://travel.vela.example/hotels/shibuya-house",
            key_highlights=["Very central", "Good nightlife access", "Fast rail connections"],
            short_description="An energetic stay for travellers who want easy access to Tokyo's busiest zones.",
        ),
        HotelOption(
            id="tokyo-ueno-pocket",
            name="Ueno Pocket Stay",
            neighborhood="Ueno",
            category="budget",
            nightly_rate_usd=128,
            affiliate_link="https://travel.vela.example/hotels/ueno-pocket-stay",
            key_highlights=["Affordable", "Near museums", "Simple and efficient"],
            short_description="A compact budget option with easy cultural access and strong value.",
        ),
    ],
    restaurants=[
        RestaurantOption(
            id="tokyo-aoyama-counter",
            name="Aoyama Ember Counter",
            cuisine="Modern Japanese",
            price_range="$$$",
            neighborhood="Aoyama",
            must_order_dish="Binchotan grilled seasonal fish",
            reservation_link="https://travel.vela.example/restaurants/aoyama-ember-counter",
            why_it_fits="Ideal for a memorable couple dinner without becoming overly formal.",
        ),
        RestaurantOption(
            id="tokyo-kiyosumi-kissaten",
            name="Kiyosumi Morning Kissaten",
            cuisine="Coffee and light breakfast",
            price_range="$$",
            neighborhood="Kiyosumi",
            must_order_dish="Thick-cut toast with whipped butter",
            reservation_link="https://travel.vela.example/restaurants/kiyosumi-morning-kissaten",
            why_it_fits="Matches food-focused travellers who like slower local mornings.",
        ),
        RestaurantOption(
            id="tokyo-yanaka-izakaya",
            name="Yanaka Lantern Izakaya",
            cuisine="Izakaya",
            price_range="$$",
            neighborhood="Yanaka",
            must_order_dish="Charcoal chicken skewers",
            reservation_link="https://travel.vela.example/restaurants/yanaka-lantern-izakaya",
            why_it_fits="A hidden-gem neighborhood dinner with a more local, less polished feel.",
        ),
        RestaurantOption(
            id="tokyo-nakameguro-soba",
            name="Nakameguro River Soba",
            cuisine="Soba",
            price_range="$$",
            neighborhood="Nakameguro",
            must_order_dish="Cold yuzu soba",
            reservation_link="https://travel.vela.example/restaurants/nakameguro-river-soba",
            why_it_fits="A lighter meal option that fits a balanced itinerary.",
        ),
    ],
    experiences=[
        ExperienceOption(
            id="tokyo-tsukiji-crawl",
            name="Tsukiji Side-Street Food Crawl",
            category="food tour",
            duration_hours=3.0,
            estimated_cost_usd=65,
            neighborhood="Tsukiji",
            booking_link="https://travel.vela.example/experiences/tsukiji-side-street-food-crawl",
            best_time="Morning",
            why_it_fits="Directly matches food-focused travellers and creates a strong early-trip anchor.",
        ),
        ExperienceOption(
            id="tokyo-yanaka-walk",
            name="Yanaka Hidden Lanes Walk",
            category="hidden gem",
            duration_hours=2.5,
            estimated_cost_usd=25,
            neighborhood="Yanaka",
            booking_link="https://travel.vela.example/experiences/yanaka-hidden-lanes-walk",
            best_time="Afternoon",
            why_it_fits="Gives the trip texture beyond tourist hotspots and keeps the pace human.",
        ),
        ExperienceOption(
            id="tokyo-kiyosumi-coffee",
            name="Kiyosumi Coffee and Gallery Circuit",
            category="local culture",
            duration_hours=3.0,
            estimated_cost_usd=30,
            neighborhood="Kiyosumi",
            booking_link="https://travel.vela.example/experiences/kiyosumi-coffee-and-gallery-circuit",
            best_time="Morning",
            why_it_fits="Combines slower pacing with strong local flavor.",
        ),
        ExperienceOption(
            id="tokyo-meiji-evening",
            name="Meiji Shrine Evening Reset",
            category="outdoor",
            duration_hours=1.5,
            estimated_cost_usd=0,
            neighborhood="Harajuku",
            booking_link="https://travel.vela.example/experiences/meiji-shrine-evening-reset",
            best_time="Evening",
            why_it_fits="A low-cost, low-friction decompression block between busier food stops.",
        ),
    ],
)


LISBON = DestinationProfile(
    name="Lisbon",
    weather_by_month={
        "august": WeatherSummary(
            destination="Lisbon",
            month="August",
            avg_temp_c=28,
            rainfall_mm=8,
            conditions_summary="Hot, dry, and bright with cooler evenings near the water.",
            packing_notes=[
                "Bring breathable clothing and sun protection.",
                "Plan hill-heavy walks in the morning or late afternoon.",
            ],
        ),
    },
    hotels=[
        HotelOption(
            id="lisbon-alfama-courtyard",
            name="Alfama Courtyard House",
            neighborhood="Alfama",
            category="mid",
            nightly_rate_usd=205,
            affiliate_link="https://travel.vela.example/hotels/alfama-courtyard-house",
            key_highlights=["Historic atmosphere", "Walkable old town access", "Romantic courtyard"],
            short_description="A warm boutique base for travellers who want texture and atmosphere.",
        ),
    ],
    restaurants=[
        RestaurantOption(
            id="lisbon-bairro-tasca",
            name="Bairro Alto Tile Tasca",
            cuisine="Portuguese",
            price_range="$$",
            neighborhood="Bairro Alto",
            must_order_dish="Garlic prawns with vinho verde",
            reservation_link="https://travel.vela.example/restaurants/bairro-alto-tile-tasca",
            why_it_fits="A lively but approachable dinner that feels local rather than formal.",
        ),
    ],
    experiences=[
        ExperienceOption(
            id="lisbon-alfama-fado",
            name="Alfama Twilight Fado Walk",
            category="music and culture",
            duration_hours=2.5,
            estimated_cost_usd=42,
            neighborhood="Alfama",
            booking_link="https://travel.vela.example/experiences/alfama-twilight-fado-walk",
            best_time="Evening",
            why_it_fits="Creates a memorable evening anchor with strong local character.",
        ),
    ],
)


PARIS = DestinationProfile(
    name="Paris",
    weather_by_month={
        "august": WeatherSummary(
            destination="Paris",
            month="August",
            avg_temp_c=26,
            rainfall_mm=47,
            conditions_summary="Warm days, mild evenings, and occasional summer showers.",
            packing_notes=[
                "Carry a light layer for evenings.",
                "Keep one flexible indoor option for rain.",
            ],
        ),
    },
    hotels=[
        HotelOption(
            id="paris-marais-salon",
            name="Le Marais Salon Hotel",
            neighborhood="Le Marais",
            category="mid",
            nightly_rate_usd=240,
            affiliate_link="https://travel.vela.example/hotels/le-marais-salon",
            key_highlights=["Central but charming", "Great café access", "Boutique scale"],
            short_description="A design-led base for travellers who want centrality without generic business-hotel energy.",
        ),
    ],
    restaurants=[
        RestaurantOption(
            id="paris-canal-bistro",
            name="Canal St Martin Bistro",
            cuisine="French bistro",
            price_range="$$$",
            neighborhood="Canal Saint-Martin",
            must_order_dish="Roast chicken with tarragon jus",
            reservation_link="https://travel.vela.example/restaurants/canal-st-martin-bistro",
            why_it_fits="Strong for a couple-focused dinner in a neighborhood with evening atmosphere.",
        ),
    ],
    experiences=[
        ExperienceOption(
            id="paris-left-bank-bookshops",
            name="Left Bank Bookshops and Passages Walk",
            category="hidden gem",
            duration_hours=3.0,
            estimated_cost_usd=18,
            neighborhood="Saint-Germain",
            booking_link="https://travel.vela.example/experiences/left-bank-bookshops-and-passages-walk",
            best_time="Afternoon",
            why_it_fits="Builds a slower, more editorial day instead of rushing landmark to landmark.",
        ),
    ],
)


DESTINATIONS = {
    "tokyo": TOKYO,
    "lisbon": LISBON,
    "paris": PARIS,
}


def get_weather(input_data: WeatherInput) -> WeatherSummary:
    profile = _get_destination_profile(input_data.destination)
    return profile.weather_by_month.get(input_data.month.lower(), next(iter(profile.weather_by_month.values())))


def get_hotels(input_data: HotelSearchInput) -> list[HotelOption]:
    profile = _get_destination_profile(input_data.destination)
    ranked = []
    for hotel in profile.hotels:
        score = 0
        if hotel.category == input_data.budget:
            score += 2
        if input_data.preferred_neighborhood and hotel.neighborhood.lower() == input_data.preferred_neighborhood.lower():
            score += 3
        if input_data.accommodation_type and input_data.accommodation_type.lower() in hotel.short_description.lower():
            score += 1
        ranked.append((score, hotel))
    ranked.sort(key=lambda item: (-item[0], item[1].nightly_rate_usd))
    return [hotel for _, hotel in ranked]


def get_restaurants(input_data: RestaurantSearchInput) -> list[RestaurantOption]:
    profile = _get_destination_profile(input_data.destination)
    ranked = []
    for restaurant in profile.restaurants:
        score = 0
        if input_data.neighborhoods and restaurant.neighborhood in input_data.neighborhoods:
            score += 2
        if _matches_interests(restaurant.why_it_fits, input_data.interests):
            score += 2
        if input_data.dietary_preferences and _matches_interests(restaurant.must_order_dish, input_data.dietary_preferences):
            score += 1
        if input_data.budget == "mid" and restaurant.price_range in {"$$", "$$$"}:
            score += 1
        ranked.append((score, restaurant))
    ranked.sort(key=lambda item: -item[0])
    return [restaurant for _, restaurant in ranked]


def get_experiences(input_data: ExperienceSearchInput) -> list[ExperienceOption]:
    profile = _get_destination_profile(input_data.destination)
    ranked = []
    for experience in profile.experiences:
        score = 0
        if _matches_interests(experience.category, input_data.interests):
            score += 2
        if _matches_interests(experience.why_it_fits, input_data.interests):
            score += 2
        if input_data.travel_party and input_data.travel_party.lower() in experience.why_it_fits.lower():
            score += 1
        if _pace_matches(experience.duration_hours, input_data.pace):
            score += 1
        ranked.append((score, experience))
    ranked.sort(key=lambda item: -item[0])
    return [experience for _, experience in ranked]


def get_daily_structure(input_data: DailyStructureInput) -> list[DayPlan]:
    profile = _get_destination_profile(input_data.destination)
    hotel = _find_by_name(profile.hotels, input_data.hotel_name)
    restaurants = _find_many_by_name(profile.restaurants, input_data.restaurant_names) or profile.restaurants[:3]
    experiences = _find_many_by_name(profile.experiences, input_data.experience_names) or profile.experiences[:3]

    days: list[DayPlan] = []
    for day_number in range(1, input_data.trip_length_days + 1):
        if day_number == 1:
            dinner = restaurants[0] if restaurants else None
            items = [
                DayItem(
                    time_label="Afternoon",
                    kind="hotel",
                    title=f"Check in at {hotel.name}",
                    neighborhood=hotel.neighborhood,
                    description=hotel.short_description,
                    booking_link=hotel.affiliate_link,
                ),
                DayItem(
                    time_label="Early evening",
                    kind="note",
                    title="Ease into the city",
                    neighborhood=hotel.neighborhood,
                    description="Keep the first evening light to absorb jet lag and protect the rest of the trip.",
                ),
            ]
            if dinner:
                items.append(
                    DayItem(
                        time_label="Dinner",
                        kind="restaurant",
                        title=dinner.name,
                        neighborhood=dinner.neighborhood,
                        description=f"{dinner.cuisine} dinner. Order the {dinner.must_order_dish}.",
                        booking_link=dinner.reservation_link,
                    )
                )
            days.append(
                DayPlan(
                    day_number=1,
                    theme="Arrival + soft landing",
                    summary="Settle in, stay close to the hotel, and begin with one strong meal.",
                    items=items,
                )
            )
            continue

        experience = experiences[(day_number - 2) % len(experiences)] if experiences else None
        lunch = restaurants[(day_number - 1) % len(restaurants)] if restaurants else None
        dinner = restaurants[(day_number) % len(restaurants)] if len(restaurants) > 1 else lunch

        neighborhood = experience.neighborhood if experience else (lunch.neighborhood if lunch else hotel.neighborhood)
        items = [
            DayItem(
                time_label="Morning",
                kind="note",
                title="Start in one neighborhood",
                neighborhood=neighborhood,
                description="Group the day geographically to reduce transit drag and make the pace feel intentional.",
            )
        ]
        if experience:
            items.append(
                DayItem(
                    time_label=experience.best_time,
                    kind="experience",
                    title=experience.name,
                    neighborhood=experience.neighborhood,
                    description=experience.why_it_fits,
                    booking_link=experience.booking_link,
                )
            )
        if lunch:
            items.append(
                DayItem(
                    time_label="Lunch",
                    kind="restaurant",
                    title=lunch.name,
                    neighborhood=lunch.neighborhood,
                    description=f"{lunch.cuisine}. Signature: {lunch.must_order_dish}.",
                    booking_link=lunch.reservation_link,
                )
            )
        if dinner and dinner.name != lunch.name:
            items.append(
                DayItem(
                    time_label="Dinner",
                    kind="restaurant",
                    title=dinner.name,
                    neighborhood=dinner.neighborhood,
                    description=dinner.why_it_fits,
                    booking_link=dinner.reservation_link,
                )
            )
        days.append(
            DayPlan(
                day_number=day_number,
                theme=_theme_for_day(day_number, input_data.pace),
                summary=f"A {input_data.pace} day centered around {neighborhood}.",
                items=items,
            )
        )
    return days


def _get_destination_profile(destination: str) -> DestinationProfile:
    normalized = destination.strip().lower()
    if normalized in DESTINATIONS:
        return DESTINATIONS[normalized]
    return _generic_profile(destination.strip().title())


def _generic_profile(destination: str) -> DestinationProfile:
    return DestinationProfile(
        name=destination,
        weather_by_month={
            "august": WeatherSummary(
                destination=destination,
                month="August",
                avg_temp_c=27,
                rainfall_mm=45,
                conditions_summary="Seasonally warm with a mix of sun and occasional showers.",
                packing_notes=["Pack comfortable walking shoes.", "Keep one light rain layer handy."],
            )
        },
        hotels=[
            HotelOption(
                id=f"{destination.lower()}-central-house",
                name=f"{destination} Central House",
                neighborhood="Central District",
                category="mid",
                nightly_rate_usd=210,
                affiliate_link="https://travel.vela.example/hotels/generic-central-house",
                key_highlights=["Central", "Good transit access", "Balanced value"],
                short_description="A flexible mid-range base that works well for first-time visitors.",
            )
        ],
        restaurants=[
            RestaurantOption(
                id=f"{destination.lower()}-market-bistro",
                name=f"{destination} Market Bistro",
                cuisine="Local cuisine",
                price_range="$$",
                neighborhood="Old Quarter",
                must_order_dish="House seasonal special",
                reservation_link="https://travel.vela.example/restaurants/generic-market-bistro",
                why_it_fits="A safe anchor meal that adds local character without overcomplicating the trip.",
            )
        ],
        experiences=[
            ExperienceOption(
                id=f"{destination.lower()}-hidden-walk",
                name=f"{destination} Hidden Streets Walk",
                category="hidden gem",
                duration_hours=2.5,
                estimated_cost_usd=20,
                neighborhood="Old Quarter",
                booking_link="https://travel.vela.example/experiences/generic-hidden-streets-walk",
                best_time="Afternoon",
                why_it_fits="Adds local texture and keeps the trip from feeling too generic.",
            )
        ],
    )


def _find_by_name(items: list[T], name: str) -> T:
    for item in items:
        if getattr(item, "name", "").lower() == name.lower():
            return item
    return items[0]


def _find_many_by_name(items: list[T], names: list[str]) -> list[T]:
    if not names:
        return []
    name_set = {name.lower() for name in names}
    return [item for item in items if getattr(item, "name", "").lower() in name_set]


def _matches_interests(text: str, interests: list[str]) -> bool:
    lowered = text.lower()
    return any(interest.lower() in lowered for interest in interests)


def _pace_matches(duration_hours: float, pace: Pace) -> bool:
    if pace == "slow":
        return duration_hours <= 2.5
    if pace == "packed":
        return duration_hours <= 4
    return duration_hours <= 3.5


def _theme_for_day(day_number: int, pace: Pace) -> str:
    if day_number == 2:
        return "Food-first neighborhood immersion"
    if pace == "slow":
        return "Slow discovery and recovery time"
    if pace == "packed":
        return "High-energy city coverage"
    return "Balanced exploration"
