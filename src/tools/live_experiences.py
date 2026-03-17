from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

from src.tools.mock_data import get_experiences as get_mock_experiences
from src.tools.schemas import ExperienceOption, ExperienceSearchInput


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


def get_experiences(input_data: ExperienceSearchInput) -> list[ExperienceOption]:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return get_mock_experiences(input_data)

    try:
        query = build_text_query(input_data)
        places = search_places(query=query, api_key=api_key)
        experiences = [map_place_to_experience(place, input_data) for place in places]
        experiences = [experience for experience in experiences if experience is not None]
        return experiences or get_mock_experiences(input_data)
    except Exception:
        return get_mock_experiences(input_data)


def build_text_query(input_data: ExperienceSearchInput) -> str:
    parts: list[str] = []

    if input_data.interests:
        parts.append(", ".join(input_data.interests))

    parts.append("things to do")

    if input_data.travel_party:
        parts.append(f"for {input_data.travel_party}")

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


def map_place_to_experience(place: dict, input_data: ExperienceSearchInput) -> ExperienceOption | None:
    place_id = place.get("id")
    display_name = ((place.get("displayName") or {}).get("text") or "").strip()
    maps_url = place.get("googleMapsUri")
    if not place_id or not display_name or not maps_url:
        return None

    category = ((place.get("primaryTypeDisplayName") or {}).get("text") or "Experience").strip()
    neighborhood = infer_neighborhood(place)
    photo_name, photo_attribution = extract_photo_metadata(place)

    return ExperienceOption(
        id=place_id,
        name=display_name,
        category=category,
        duration_hours=estimate_duration_hours(category, input_data.pace),
        estimated_cost_usd=estimate_cost_usd(category),
        neighborhood=neighborhood,
        booking_link=maps_url,
        best_time=estimate_best_time(category),
        why_it_fits=build_why_it_fits(input_data, category, neighborhood),
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


def estimate_duration_hours(category: str, pace: str) -> float:
    category_lower = category.lower()
    if "museum" in category_lower or "gallery" in category_lower:
        return 2.5 if pace != "packed" else 2.0
    if "park" in category_lower or "walking" in category_lower:
        return 2.0 if pace == "slow" else 1.5
    if "landmark" in category_lower or "tourist" in category_lower:
        return 1.5
    return 2.0 if pace == "balanced" else (2.5 if pace == "slow" else 1.5)


def estimate_cost_usd(category: str) -> int:
    category_lower = category.lower()
    if "museum" in category_lower or "gallery" in category_lower:
        return 25
    if "park" in category_lower or "church" in category_lower or "cathedral" in category_lower:
        return 0
    if "tour" in category_lower:
        return 35
    return 20


def estimate_best_time(category: str) -> str:
    category_lower = category.lower()
    if "museum" in category_lower or "gallery" in category_lower:
        return "Afternoon"
    if "park" in category_lower or "garden" in category_lower:
        return "Morning"
    if "night" in category_lower or "bar" in category_lower:
        return "Evening"
    return "Afternoon"


def build_why_it_fits(input_data: ExperienceSearchInput, category: str, neighborhood: str) -> str:
    if input_data.interests:
        return (
            f"Fits the trip's focus on {', '.join(input_data.interests[:2])} while giving you a usable stop around "
            f"{neighborhood}."
        )
    if input_data.travel_party:
        return f"A practical {category.lower()} stop for a {input_data.travel_party} trip in {input_data.destination}."
    return f"A strong local experience in {neighborhood} that helps the itinerary feel less generic."
