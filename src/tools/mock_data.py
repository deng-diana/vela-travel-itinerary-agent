from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Hotel:
    name: str
    city: str
    price_per_night: int


@dataclass(frozen=True)
class Restaurant:
    name: str
    city: str
    cuisine: str


_HOTELS = [
    Hotel(name="Vela Grand", city="Shanghai", price_per_night=980),
    Hotel(name="Harbor View", city="Shanghai", price_per_night=720),
    Hotel(name="Old Town Inn", city="Hangzhou", price_per_night=560),
]

_RESTAURANTS = [
    Restaurant(name="Noodle House", city="Shanghai", cuisine="Chinese"),
    Restaurant(name="Sushi Zen", city="Shanghai", cuisine="Japanese"),
    Restaurant(name="Lake Bistro", city="Hangzhou", cuisine="Fusion"),
]

_WEATHER = {
    "Shanghai": {"temp_c": 18, "condition": "Cloudy"},
    "Hangzhou": {"temp_c": 20, "condition": "Sunny"},
}


def search_hotels(city: str) -> list[dict]:
    city_norm = city.strip()
    return [
        {"name": h.name, "city": h.city, "price_per_night": h.price_per_night}
        for h in _HOTELS
        if h.city.lower() == city_norm.lower()
    ]


def search_restaurants(city: str) -> list[dict]:
    city_norm = city.strip()
    return [
        {"name": r.name, "city": r.city, "cuisine": r.cuisine}
        for r in _RESTAURANTS
        if r.city.lower() == city_norm.lower()
    ]


def get_weather(city: str) -> dict:
    city_norm = city.strip()
    for k, v in _WEATHER.items():
        if k.lower() == city_norm.lower():
            return {"city": k, **v}
    return {"city": city_norm, "temp_c": None, "condition": "Unknown"}

