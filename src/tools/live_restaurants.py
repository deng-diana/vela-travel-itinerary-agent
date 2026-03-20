from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

from src.tools.mock_data import get_restaurants as get_mock_restaurants
from src.tools.schemas import RestaurantOption, RestaurantSearchInput


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


def get_restaurants(input_data: RestaurantSearchInput) -> list[RestaurantOption]:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return get_mock_restaurants(input_data)

    try:
        queries = build_text_queries(input_data)
        places = search_places(queries=queries, api_key=api_key)
        restaurants = [map_place_to_restaurant(place, input_data) for place in places]
        restaurants = [restaurant for restaurant in restaurants if restaurant is not None]
        return restaurants or get_mock_restaurants(input_data)
    except Exception:
        return get_mock_restaurants(input_data)


def build_text_queries(input_data: RestaurantSearchInput) -> list[str]:
    parts: list[str] = []

    if input_data.interests:
        parts.append(", ".join(input_data.interests))
    if input_data.dietary_preferences:
        parts.append(", ".join(input_data.dietary_preferences))

    parts.append("restaurants")

    if input_data.neighborhoods:
        parts.append(f"near {', '.join(input_data.neighborhoods)}")

    parts.append(f"in {input_data.destination}")

    queries = [" ".join(parts)]

    joined_interest_text = " ".join(input_data.interests).lower()
    if any(token in joined_interest_text for token in ("hidden", "local", "gem", "independent", "neighborhood")):
        neighborhood = f" near {', '.join(input_data.neighborhoods)}" if input_data.neighborhoods else ""
        queries.append(f"hidden gem restaurants{neighborhood} in {input_data.destination}")
        queries.append(f"local restaurants{neighborhood} in {input_data.destination}")

    return list(dict.fromkeys(query for query in queries if query.strip()))


def search_places(queries: list[str], api_key: str) -> list[dict]:
    all_places: list[dict] = []
    seen_ids: set[str] = set()

    for query in queries:
        response = httpx.post(
            TEXT_SEARCH_URL,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": ",".join(
                    [
                        "places.id",
                        "places.displayName",
                        "places.formattedAddress",
                        "places.shortFormattedAddress",
                        "places.priceLevel",
                        "places.googleMapsUri",
                        "places.primaryTypeDisplayName",
                        "places.rating",
                        "places.userRatingCount",
                        "places.photos",
                    ]
                ),
            },
            json={
                "textQuery": query,
                "languageCode": "en",
                "maxResultCount": 8,
            },
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()
        for place in payload.get("places", []):
            place_id = place.get("id")
            if not place_id or place_id in seen_ids:
                continue
            seen_ids.add(place_id)
            all_places.append(place)

    return all_places


def map_place_to_restaurant(place: dict, input_data: RestaurantSearchInput) -> RestaurantOption | None:
    place_id = place.get("id")
    display_name = ((place.get("displayName") or {}).get("text") or "").strip()
    maps_url = place.get("googleMapsUri")
    if not place_id or not display_name or not maps_url:
        return None

    cuisine = ((place.get("primaryTypeDisplayName") or {}).get("text") or "Restaurant").strip()
    neighborhood = infer_neighborhood(place)
    price_range = map_price_level(place.get("priceLevel"))

    photo_name = None
    photo_attribution = None
    photos = place.get("photos") or []
    if photos:
        first_photo = photos[0]
        photo_name = first_photo.get("name")

        attributions = first_photo.get("authorAttributions") or []
        if attributions:
            first_attr = attributions[0]
            display_name_attr = first_attr.get("displayName")
            uri_attr = first_attr.get("uri")
            if display_name_attr and uri_attr:
                photo_attribution = f"{display_name_attr} ({uri_attr})"
            elif display_name_attr:
                photo_attribution = display_name_attr

    return RestaurantOption(
        id=place_id,
        name=display_name,
        cuisine=cuisine,
        price_range=price_range,
        neighborhood=neighborhood,
        must_order_dish=suggest_signature_dish(cuisine, display_name, input_data.destination),
        reservation_link=maps_url,
        why_it_fits=build_why_it_fits(input_data, display_name, neighborhood, cuisine,
                                      place.get("rating"), place.get("userRatingCount")),
        rating=place.get("rating"),
        user_rating_count=place.get("userRatingCount"),
        maps_url=maps_url,
        photo_name=photo_name,
        photo_attribution=photo_attribution,
    )


def infer_neighborhood(place: dict) -> str:
    short_address = place.get("shortFormattedAddress")
    if short_address:
        return short_address.split(",")[0].strip()

    formatted_address = place.get("formattedAddress")
    if formatted_address:
        return formatted_address.split(",")[0].strip()

    return "Local area"


def map_price_level(price_level: str | None) -> str:
    mapping = {
        "PRICE_LEVEL_FREE": "$",
        "PRICE_LEVEL_INEXPENSIVE": "$",
        "PRICE_LEVEL_MODERATE": "$$",
        "PRICE_LEVEL_EXPENSIVE": "$$$",
        "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$",
    }
    return mapping.get(price_level, "$$")


def suggest_signature_dish(cuisine: str, restaurant_name: str, destination: str) -> str:
    """Heuristic signature dish suggestion based on cuisine type and destination.

    Since Google Places API doesn't return menu data, we use cuisine + destination
    to suggest a realistic signature dish that adds specificity to the recommendation.
    """
    cuisine_lower = cuisine.lower()
    dest_lower = destination.lower()

    # Destination-specific regional dishes
    regional_dishes: dict[str, list[str]] = {
        "tokyo": ["Omakase sushi selection", "Tonkotsu ramen with chashu", "Tempura course with seasonal vegetables",
                   "Wagyu beef don", "Matcha parfait", "Yakitori tasting set"],
        "kyoto": ["Kaiseki multi-course meal", "Yudofu (hot tofu)", "Matcha soba noodles",
                   "Obanzai home-style platter", "Sakura mochi"],
        "osaka": ["Takoyaki platter", "Okonomiyaki with pork belly", "Kushikatsu assortment",
                   "Kitsune udon", "Negiyaki scallion pancake"],
        "paris": ["Duck confit with pommes sarladaises", "Steak tartare", "Croque monsieur",
                   "Bouillabaisse", "Tarte tatin", "Soufflé au chocolat"],
        "london": ["Sunday roast with Yorkshire pudding", "Fish and chips with mushy peas",
                    "Beef Wellington", "Sticky toffee pudding", "Full English breakfast"],
        "rome": ["Cacio e pepe", "Carbonara with guanciale", "Supplì al telefono",
                  "Saltimbocca alla romana", "Tiramisu"],
        "barcelona": ["Paella valenciana", "Patatas bravas", "Jamón ibérico with pan con tomate",
                       "Fideuà", "Crema catalana"],
        "bangkok": ["Pad Thai with river prawns", "Green curry with roti", "Tom yum goong",
                     "Mango sticky rice", "Som tum (papaya salad)"],
        "singapore": ["Hainanese chicken rice", "Chilli crab", "Laksa",
                       "Char kway teow", "Kaya toast set"],
        "istanbul": ["Kebab platter with hummus", "Lahmacun", "Baklava assortment",
                      "Pide with sucuk", "Turkish breakfast spread"],
        "seoul": ["Korean BBQ galbi set", "Bibimbap in hot stone pot", "Kimchi jjigae",
                   "Tteokbokki", "Samgyeopsal set"],
        "bali": ["Nasi goreng with fried egg", "Babi guling (suckling pig)", "Satay lilit",
                  "Lawar salad", "Bebek betutu (slow-cooked duck)"],
    }

    # Check destination-specific dishes first
    for city, dishes in regional_dishes.items():
        if city in dest_lower:
            import random
            return random.choice(dishes)

    # Cuisine-type fallback
    cuisine_dishes: dict[str, list[str]] = {
        "japanese": ["Chef's omakase selection", "Seasonal sashimi platter"],
        "sushi": ["Chef's omakase selection", "Seasonal nigiri set"],
        "ramen": ["House special tonkotsu ramen", "Spicy miso ramen with chashu"],
        "italian": ["Handmade pasta of the day", "Wood-fired margherita pizza"],
        "french": ["Duck confit with seasonal vegetables", "Bouillabaisse"],
        "chinese": ["Peking duck", "Xiao long bao (soup dumplings)"],
        "thai": ["Green curry with jasmine rice", "Pad Thai with prawns"],
        "indian": ["Butter chicken with garlic naan", "Thali platter"],
        "mexican": ["Tacos al pastor", "Mole negro with chicken"],
        "korean": ["Korean BBQ set", "Bibimbap in hot stone pot"],
        "vietnamese": ["Pho bo (beef noodle soup)", "Banh mi with lemongrass chicken"],
        "mediterranean": ["Grilled seafood platter", "Mezze sharing board"],
        "seafood": ["Grilled catch of the day", "Seafood platter for two"],
        "steakhouse": ["Dry-aged ribeye steak", "Wagyu tasting cut"],
        "café": ["Signature coffee with house pastry", "Seasonal brunch plate"],
        "bakery": ["House sourdough with seasonal preserves", "Pain au chocolat"],
        "bar": ["Signature cocktail with bar snacks", "Craft beer tasting flight"],
        "pizza": ["Wood-fired margherita with buffalo mozzarella", "Truffle pizza"],
    }

    for keyword, dishes in cuisine_dishes.items():
        if keyword in cuisine_lower:
            import random
            return random.choice(dishes)

    # Generic fallback
    return "Chef's signature dish"


def build_why_it_fits(
    input_data: RestaurantSearchInput,
    name: str,
    neighborhood: str,
    cuisine: str,
    rating: float | None,
    user_rating_count: int | None,
) -> str:
    """Build a specific, compelling reason to dine here."""
    parts: list[str] = []

    # Rating credibility
    if rating and rating >= 4.5 and user_rating_count and user_rating_count > 1000:
        parts.append(f"Rated {rating:.1f} by {user_rating_count:,}+ diners")
    elif rating and rating >= 4.0:
        parts.append(f"{rating:.1f}-star {cuisine.lower()}")

    # Location context
    parts.append(f"in {neighborhood}")

    # Cuisine description
    cuisine_lower = cuisine.lower()
    if "french" in cuisine_lower or "bistro" in cuisine_lower:
        parts.append("classic French dining")
    elif "italian" in cuisine_lower:
        parts.append("authentic Italian kitchen")
    elif "japanese" in cuisine_lower or "sushi" in cuisine_lower:
        parts.append("Japanese culinary tradition")
    elif "café" in cuisine_lower or "coffee" in cuisine_lower:
        parts.append("perfect for a relaxed stop between sights")

    # Budget alignment
    price_map = {"budget": "budget-friendly", "luxury": "upscale"}
    budget_label = price_map.get(input_data.budget)
    if budget_label:
        parts.append(f"{budget_label} option")

    return ". ".join(p.capitalize() if i == 0 else p for i, p in enumerate(parts)) + "."
