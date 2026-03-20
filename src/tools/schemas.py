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


class PlanningBrief(BaseModel):
    destination: str | None = None
    dates_or_month: str | None = None
    trip_length_days: int | None = None
    travel_party: str | None = None
    budget: BudgetTier | None = None
    total_budget_amount: int | None = None  # user-stated cap, e.g. 500
    total_budget_currency: str | None = None  # e.g. "GBP", "USD", "EUR"
    priorities: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    constraints_confirmed: bool = False
    style_notes: list[str] = Field(default_factory=list)
    pace: Pace | None = None
    hotel_preference: str | None = None
    neighborhood_preference: str | None = None
    dietary_preferences: list[str] = Field(default_factory=list)
    must_do: list[str] = Field(default_factory=list)
    must_avoid: list[str] = Field(default_factory=list)


class PlanningBriefPatch(BaseModel):
    destination: str | None = None
    dates_or_month: str | None = None
    trip_length_days: int | None = None
    travel_party: str | None = None
    budget: BudgetTier | None = None
    total_budget_amount: int | None = None
    total_budget_currency: str | None = None
    priorities: list[str] | None = None
    constraints: list[str] | None = None
    constraints_confirmed: bool | None = None
    style_notes: list[str] | None = None
    pace: Pace | None = None
    hotel_preference: str | None = None
    neighborhood_preference: str | None = None
    dietary_preferences: list[str] | None = None
    must_do: list[str] | None = None
    must_avoid: list[str] | None = None
    day_swap_request: str | None = None
    notes: str | None = None


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
    style_notes: list[str] = Field(default_factory=list)
    must_do: list[str] = Field(default_factory=list)
    must_avoid: list[str] = Field(default_factory=list)
    day_swap_request: str | None = None


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
    rating: float | None = None
    user_rating_count: int | None = None
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
    rating: float | None = None
    user_rating_count: int | None = None
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
    rating: float | None = None
    user_rating_count: int | None = None
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
    transport_note: str | None = None  # e.g. "10-min walk from hotel" / "Subway Marunouchi Line, 3 stops"


class DayPlan(BaseModel):
    day_number: int
    theme: str
    summary: str
    items: list[DayItem] = Field(default_factory=list)
    practical_tips: list[str] = Field(default_factory=list)  # e.g. ["Book ahead", "Cash only", "Opens 9am"]
    day_estimated_cost_usd: int | None = None


class BudgetInput(BaseModel):
    destination: str = Field(..., min_length=2)
    trip_length_days: int = Field(..., ge=1, le=30)
    budget: BudgetTier = "mid"
    travel_party: str | None = None
    hotel_nightly_rate_usd: int | None = None
    experience_daily_cost_usd: int | None = None
    user_budget_amount: int | None = None
    user_budget_currency: str | None = None


class BudgetLineItem(BaseModel):
    category: str
    amount_usd: int
    detail: str


class BudgetEstimate(BaseModel):
    destination: str
    trip_length_days: int
    budget_tier: BudgetTier
    currency: str = "USD"
    accommodation_total_usd: int
    food_total_usd: int
    activities_total_usd: int
    transport_total_usd: int
    misc_total_usd: int
    grand_total_usd: int
    daily_average_usd: int
    line_items: list[BudgetLineItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    user_budget_amount: int | None = None  # original stated cap
    user_budget_currency: str | None = None
    over_budget: bool = False


class VisaInput(BaseModel):
    destination: str = Field(..., min_length=2)
    nationality: str = "US"


class VisaRequirements(BaseModel):
    destination: str
    nationality: str
    visa_type: str
    max_stay_days: int | None = None
    required_docs: list[str] = Field(default_factory=list)
    processing_days: int | None = None
    fee_usd: int | None = None
    notes: str = ""
    official_link: str | None = None


class PackingInput(BaseModel):
    destination: str = Field(..., min_length=2)
    month: str = Field(..., min_length=3)
    avg_temp_c: int | None = None
    conditions_summary: str | None = None
    trip_length_days: int = Field(default=7, ge=1, le=30)
    activities: list[str] = Field(default_factory=list)
    travel_party: str | None = None


class PackingCategory(BaseModel):
    category: str
    items: list[str]


class PackingSuggestions(BaseModel):
    destination: str
    month: str
    weather_note: str = ""
    categories: list[PackingCategory] = Field(default_factory=list)


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
    budget_estimate: BudgetEstimate | None = None
    visa_requirements: VisaRequirements | None = None
    packing_suggestions: PackingSuggestions | None = None
    trip_tone: str | None = None          # e.g. "romantic & foodie" / "cultural & packed"
    key_moments: list[str] = Field(default_factory=list)    # 3-5 standout trip highlights
    cultural_notes: list[str] = Field(default_factory=list) # etiquette / local customs
    summary: str
