from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

from src.tools.mock_data import get_hotels as get_mock_hotels
from src.tools.schemas import BudgetTier, HotelOption, HotelSearchInput


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


def get_hotels(input_data: HotelSearchInput) -> list[HotelOption]:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return get_mock_hotels(input_data)

    try:
        query = build_text_query(input_data)
        places = search_places(query=query, api_key=api_key)
        hotels = [map_place_to_hotel(place, input_data) for place in places]
        hotels = [hotel for hotel in hotels if hotel is not None]
        return hotels or get_mock_hotels(input_data)
    except Exception as exc:
        logger.exception("Google Places hotel search failed: %s", exc)
        return get_mock_hotels(input_data)


def build_text_query(input_data: HotelSearchInput) -> str:
    parts: list[str] = []

    if input_data.budget == "budget":
        parts.append("budget")
    elif input_data.budget == "luxury":
        parts.append("luxury")
    else:
        parts.append("mid-range")

    if input_data.accommodation_type:
        parts.append(input_data.accommodation_type)
    else:
        parts.append("boutique hotels")

    if input_data.preferred_neighborhood:
        parts.append(f"near {input_data.preferred_neighborhood}")

    parts.append(f"in {input_data.destination}")
    return " ".join(parts)


def search_places(query: str, api_key: str) -> list[dict]:
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
                    "places.googleMapsUri",
                    "places.primaryTypeDisplayName",
                    "places.priceLevel",
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
    return payload.get("places", [])


def map_place_to_hotel(place: dict, input_data: HotelSearchInput) -> HotelOption | None:
    place_id = place.get("id")
    display_name = ((place.get("displayName") or {}).get("text") or "").strip()
    maps_url = place.get("googleMapsUri")
    if not place_id or not display_name or not maps_url:
        return None

    neighborhood = infer_neighborhood(place)
    category = infer_budget_tier(input_data.budget, place.get("priceLevel"))
    rating = place.get("rating")
    user_rating_count = place.get("userRatingCount")
    photo_name, photo_attribution = extract_photo_metadata(place)

    return HotelOption(
        id=place_id,
        name=display_name,
        neighborhood=neighborhood,
        category=category,
        nightly_rate_usd=estimate_nightly_rate_usd(category),
        affiliate_link=maps_url,
        key_highlights=build_key_highlights(neighborhood, rating, user_rating_count, input_data),
        short_description=build_short_description(input_data, neighborhood, rating),
        rating=rating,
        user_rating_count=user_rating_count,
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


def infer_budget_tier(requested_budget: BudgetTier, price_level: str | None) -> BudgetTier:
    mapping: dict[str, BudgetTier] = {
        "PRICE_LEVEL_INEXPENSIVE": "budget",
        "PRICE_LEVEL_MODERATE": "mid",
        "PRICE_LEVEL_EXPENSIVE": "luxury",
        "PRICE_LEVEL_VERY_EXPENSIVE": "luxury",
    }
    return mapping.get(price_level, requested_budget)


_price_call_count = 0

def estimate_nightly_rate_usd(category: BudgetTier) -> int:
    """Return varied nightly rates based on budget tier, rotating through price bands."""
    global _price_call_count
    _price_call_count += 1
    idx = _price_call_count % 3  # cycle through low/mid/high within tier

    if category == "budget":
        return [95, 120, 145][idx]
    if category == "luxury":
        return [320, 385, 450][idx]
    # mid-range
    return [155, 195, 230][idx]


def extract_photo_metadata(place: dict) -> tuple[str | None, str | None]:
    photos = place.get("photos") or []
    if not photos:
        return None, None

    first_photo = photos[0]
    photo_name = first_photo.get("name")

    attributions = first_photo.get("authorAttributions") or []
    if not attributions:
        return photo_name, None

    first_attr = attributions[0]
    display_name = first_attr.get("displayName")
    uri = first_attr.get("uri")
    if display_name and uri:
        return photo_name, f"{display_name} ({uri})"
    if display_name:
        return photo_name, display_name
    return photo_name, None


def build_key_highlights(
    neighborhood: str,
    rating: float | None,
    user_rating_count: int | None,
    input_data: HotelSearchInput,
) -> list[str]:
    highlights = [f"Located around {neighborhood}"]
    if rating is not None:
        highlights.append(f"Google rating {rating:.1f}")
    if user_rating_count:
        highlights.append(f"{user_rating_count}+ guest ratings")
    if input_data.accommodation_type:
        highlights.append(f"{input_data.accommodation_type.title()}-leaning stay")
    return highlights[:3]


def build_short_description(input_data: HotelSearchInput, neighborhood: str, rating: float | None) -> str:
    budget_phrase = {
        "budget": "a practical value-led base",
        "mid": "a balanced mid-range base",
        "luxury": "a more elevated stay",
    }[input_data.budget]

    rating_phrase = f" with a Google rating around {rating:.1f}" if rating is not None else ""
    return f"{budget_phrase} around {neighborhood}{rating_phrase}, suitable for a live-planned itinerary."
