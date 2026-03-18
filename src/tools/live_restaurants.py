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
        must_order_dish=None,
        reservation_link=maps_url,
        why_it_fits=build_why_it_fits(input_data, neighborhood, cuisine),
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


def build_why_it_fits(input_data: RestaurantSearchInput, neighborhood: str, cuisine: str) -> str:
    if input_data.neighborhoods and neighborhood in input_data.neighborhoods:
        return f"A strong fit for your plan in {neighborhood}, with a {cuisine.lower()} angle."
    if input_data.interests:
        return f"Matches the trip's focus on {', '.join(input_data.interests[:2])} while staying practical for the route."
    return f"A useful local option in {input_data.destination} that can anchor one part of the itinerary."
