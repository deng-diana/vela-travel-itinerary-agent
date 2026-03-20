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
        queries = build_text_queries(input_data)
        places = search_places(queries=queries, api_key=api_key)
        experiences = [map_place_to_experience(place, input_data) for place in places]
        experiences = [experience for experience in experiences if experience is not None]
        return experiences or get_mock_experiences(input_data)
    except Exception:
        return get_mock_experiences(input_data)


def build_text_queries(input_data: ExperienceSearchInput) -> list[str]:
    dest = input_data.destination
    queries: list[str] = []

    # 1. Always search for iconic landmarks and must-see attractions first
    queries.append(f"top iconic landmarks and must-see attractions in {dest}")

    # 2. Interest-based search
    if input_data.interests:
        interest_text = ", ".join(input_data.interests)
        queries.append(f"best {interest_text} experiences in {dest}")

    # 3. Famous museums and cultural sites (most cities have these)
    queries.append(f"famous museums and cultural sites in {dest}")

    # 4. Interest-specific deep dives
    joined_interest_text = " ".join(input_data.interests).lower()

    if any(token in joined_interest_text for token in ("hidden", "local", "gem", "independent", "neighborhood")):
        queries.append(f"hidden gems and local favorites in {dest}")

    if any(token in joined_interest_text for token in ("art", "design", "culture", "museum", "gallery")):
        queries.append(f"best art galleries and design spots in {dest}")

    if any(token in joined_interest_text for token in ("food", "dining", "culinary", "gastronomy")):
        queries.append(f"food tours and culinary experiences in {dest}")

    if any(token in joined_interest_text for token in ("night", "nightlife", "bar", "club")):
        queries.append(f"best nightlife and evening experiences in {dest}")

    if any(token in joined_interest_text for token in ("nature", "outdoor", "hiking", "park")):
        queries.append(f"best parks and outdoor activities in {dest}")

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


def map_place_to_experience(place: dict, input_data: ExperienceSearchInput) -> ExperienceOption | None:
    place_id = place.get("id")
    display_name = ((place.get("displayName") or {}).get("text") or "").strip()
    maps_url = place.get("googleMapsUri")
    if not place_id or not display_name or not maps_url:
        return None

    raw_category = ((place.get("primaryTypeDisplayName") or {}).get("text") or "Experience").strip()
    category = normalize_category(raw_category)
    neighborhood = infer_neighborhood(place)
    photo_name, photo_attribution = extract_photo_metadata(place)

    rating = place.get("rating")
    user_rating_count = place.get("userRatingCount")

    return ExperienceOption(
        id=place_id,
        name=display_name,
        category=category,
        duration_hours=estimate_duration_hours(category, input_data.pace),
        estimated_cost_usd=estimate_cost_usd(category),
        neighborhood=neighborhood,
        booking_link=maps_url,
        best_time=estimate_best_time(category),
        why_it_fits=build_why_it_fits(input_data, display_name, category, neighborhood, rating, user_rating_count),
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


def normalize_category(raw: str) -> str:
    """Map raw Google Places type to clean PDF-aligned categories.

    PDF requires: food tour, temple, hidden gem, outdoor, etc.
    Google returns: Tourist attraction, Museum, Park, etc.
    """
    lower = raw.lower()
    mapping: list[tuple[list[str], str]] = [
        (["temple", "shrine", "pagoda", "mosque", "church", "cathedral", "basilica"], "Temple & Shrine"),
        (["museum", "gallery"], "Museum & Gallery"),
        (["park", "garden", "botanical"], "Park & Garden"),
        (["market", "bazaar", "souk"], "Market & Shopping"),
        (["food", "culinary", "cooking"], "Food Tour"),
        (["tour", "walking"], "Guided Tour"),
        (["outdoor", "hiking", "trek", "trail", "beach", "lake", "mountain"], "Outdoor & Nature"),
        (["night", "bar", "club", "entertainment"], "Nightlife"),
        (["spa", "wellness", "onsen", "bath"], "Wellness & Spa"),
        (["historic", "heritage", "castle", "palace", "fort"], "Historic Site"),
        (["landmark", "monument", "memorial"], "Landmark"),
        (["theatre", "theater", "show", "performance"], "Performance & Arts"),
        (["zoo", "aquarium", "animal"], "Wildlife & Nature"),
        (["adventure", "sport", "kayak", "surf", "dive", "climb"], "Adventure & Sports"),
    ]
    for keywords, label in mapping:
        if any(kw in lower for kw in keywords):
            return label

    # If it's a generic "Tourist attraction", try to keep it but cleaner
    if "tourist" in lower or "attraction" in lower:
        return "Local Attraction"
    if "point of interest" in lower:
        return "Hidden Gem"

    return raw  # Keep original if no match


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


def build_why_it_fits(
    input_data: ExperienceSearchInput,
    name: str,
    category: str,
    neighborhood: str,
    rating: float | None,
    user_rating_count: int | None,
) -> str:
    """Build a specific, compelling reason to visit this place."""
    parts: list[str] = []

    # Rating-based credibility
    if rating and rating >= 4.5 and user_rating_count and user_rating_count > 5000:
        parts.append(f"Rated {rating:.1f} by {user_rating_count:,}+ visitors")
    elif rating and rating >= 4.0 and user_rating_count and user_rating_count > 1000:
        parts.append(f"Highly rated ({rating:.1f}) with {user_rating_count:,}+ reviews")

    # Category-specific context
    cat_lower = category.lower()
    if "museum" in cat_lower or "gallery" in cat_lower:
        parts.append(f"{category.lower()} in {neighborhood}")
    elif "landmark" in cat_lower or "historic" in cat_lower or "local attraction" in cat_lower:
        parts.append(f"iconic {input_data.destination} landmark")
    elif "park" in cat_lower or "garden" in cat_lower:
        parts.append(f"green space in {neighborhood} — good for a slower-paced break")
    else:
        parts.append(f"{category.lower()} experience in {neighborhood}")

    # Interest alignment
    if input_data.interests:
        matching = [i for i in input_data.interests if i.lower() in name.lower() or i.lower() in cat_lower]
        if matching:
            parts.append(f"aligns with your interest in {', '.join(matching)}")

    return ". ".join(parts) + "." if parts else f"{category} in {neighborhood}."
