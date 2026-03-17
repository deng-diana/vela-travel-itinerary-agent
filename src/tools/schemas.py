from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


BudgetTier = Literal["budget", "mid", "luxury"]
Pace = Literal["slow", "balanced", "packed"]


class ToolResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    data: Any
    meta: dict[str, Any] = Field(default_factory=dict)


class WeatherInput(BaseModel):
    destination: str = Field(..., min_length=2)
    month: str = Field(..., min_length=3)


class HotelSearchInput(BaseModel):
    destination: str = Field(..., min_length=2)
    budget: BudgetTier = "mid"
    preferred_neighborhood: str | None = None
    accommodation_type: str | None = None


class RestaurantSearchInput(BaseModel):
    destination: str = Field(..., min_length=2)
    neighborhoods: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    budget: BudgetTier = "mid"
    dietary_preferences: list[str] = Field(default_factory=list)


class ExperienceSearchInput(BaseModel):
    destination: str = Field(..., min_length=2)
    interests: list[str] = Field(default_factory=list)
    travel_party: str | None = None
    pace: Pace = "balanced"


class DailyStructureInput(BaseModel):
    destination: str = Field(..., min_length=2)
    month: str = Field(..., min_length=3)
    trip_length_days: int = Field(..., ge=1, le=14)
    travel_party: str | None = None
    budget: BudgetTier = "mid"
    interests: list[str] = Field(default_factory=list)
    hotel_name: str = Field(..., min_length=2)
    restaurant_names: list[str] = Field(default_factory=list)
    experience_names: list[str] = Field(default_factory=list)
    pace: Pace = "balanced"


class WeatherSummary(BaseModel):
    destination: str
    month: str
    avg_temp_c: int | None = None
    rainfall_mm: int | None = None
    conditions_summary: str
    packing_notes: list[str] = Field(default_factory=list)


class HotelOption(BaseModel):
    id: str
    name: str
    neighborhood: str
    category: BudgetTier
    nightly_rate_usd: int
    affiliate_link: HttpUrl
    key_highlights: list[str] = Field(default_factory=list)
    short_description: str
    maps_url: HttpUrl | None = None
    photo_name: str | None = None
    photo_attribution: str | None = None


class RestaurantOption(BaseModel):
    id: str
    name: str
    cuisine: str
    price_range: str
    neighborhood: str
    must_order_dish: str | None = None
    reservation_link: HttpUrl
    why_it_fits: str
    maps_url: HttpUrl | None = None
    photo_name: str | None = None
    photo_attribution: str | None = None



class ExperienceOption(BaseModel):
    id: str
    name: str
    category: str
    duration_hours: float
    estimated_cost_usd: int
    neighborhood: str
    booking_link: HttpUrl
    best_time: str
    why_it_fits: str
    maps_url: HttpUrl | None = None
    photo_name: str | None = None
    photo_attribution: str | None = None


class DayItem(BaseModel):
    time_label: str
    kind: Literal["hotel", "restaurant", "experience", "note"]
    title: str
    neighborhood: str | None = None
    description: str
    booking_link: HttpUrl | None = None


class DayPlan(BaseModel):
    day_number: int
    theme: str
    summary: str
    items: list[DayItem] = Field(default_factory=list)


class ItineraryDraft(BaseModel):
    destination: str
    month: str
    trip_length_days: int
    travel_party: str | None = None
    budget: BudgetTier = "mid"
    interests: list[str] = Field(default_factory=list)
    weather: WeatherSummary | None = None
    selected_hotel: HotelOption | None = None
    hotels: list[HotelOption] = Field(default_factory=list)
    restaurants: list[RestaurantOption] = Field(default_factory=list)
    experiences: list[ExperienceOption] = Field(default_factory=list)
    days: list[DayPlan] = Field(default_factory=list)
    summary: str
