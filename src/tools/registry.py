from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel

from src.tools.live_budget import estimate_budget
from src.tools.live_daily_structure import get_daily_structure
from src.tools.live_experiences import get_experiences
from src.tools.live_hotels import get_hotels
from src.tools.live_packing import get_packing_suggestions
from src.tools.live_restaurants import get_restaurants
from src.tools.live_visa import get_visa_requirements
from src.tools.live_weather import get_weather
from src.tools.schemas import (
    BudgetInput,
    DailyStructureInput,
    ExperienceSearchInput,
    HotelSearchInput,
    PackingInput,
    RestaurantSearchInput,
    VisaInput,
    WeatherInput,
)


ToolHandler = Callable[[BaseModel], Any]


class ToolSpec(BaseModel):
    name: str
    description: str
    input_model: type[BaseModel]


TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        name="get_weather",
        description="Return a live destination weather snapshot, including current temperature, short-term precipitation outlook, summary, and packing notes.",
        input_model=WeatherInput,
    ),
    ToolSpec(
        name="get_hotels",
        description="Return hotel options near a destination, including budget tier, nightly rate, highlights, and affiliate booking link.",
        input_model=HotelSearchInput,
    ),
    ToolSpec(
        name="get_restaurants",
        description="Return restaurant recommendations that match destination, interests, budget, neighborhoods, and dietary preferences.",
        input_model=RestaurantSearchInput,
    ),
    ToolSpec(
        name="get_experiences",
        description="Return activities and experiences that match destination, interests, travel party, and pace.",
        input_model=ExperienceSearchInput,
    ),
    ToolSpec(
        name="get_daily_structure",
        description="Build a sequenced day-by-day itinerary using the selected hotel, restaurants, and experiences.",
        input_model=DailyStructureInput,
    ),
    ToolSpec(
        name="estimate_budget",
        description=(
            "Compute a realistic trip cost breakdown. "
            "IMPORTANT: Call this ONLY after get_hotels has returned results so you can pass the "
            "actual hotel nightly rate. Provides line-item totals for accommodation, food, "
            "activities, transport, and miscellaneous."
        ),
        input_model=BudgetInput,
    ),
    ToolSpec(
        name="get_visa_requirements",
        description=(
            "Return entry visa requirements for the destination country based on the traveller's "
            "nationality. Includes visa type, max stay, required documents, processing time, fees, "
            "and the official government link."
        ),
        input_model=VisaInput,
    ),
    ToolSpec(
        name="get_packing_suggestions",
        description=(
            "Generate a tailored packing list. "
            "IMPORTANT: Call this ONLY after get_weather has returned results so you can pass the "
            "actual temperature and conditions. Categories: clothing, documents, toiletries, tech, extras."
        ),
        input_model=PackingInput,
    ),
]


TOOL_HANDLERS: dict[str, ToolHandler] = {
    "get_weather": get_weather,
    "get_hotels": get_hotels,
    "get_restaurants": get_restaurants,
    "get_experiences": get_experiences,
    "get_daily_structure": get_daily_structure,
    "estimate_budget": estimate_budget,
    "get_visa_requirements": get_visa_requirements,
    "get_packing_suggestions": get_packing_suggestions,
}

# Tool names available for gather phase (all except get_daily_structure)
GATHER_TOOL_NAMES: set[str] = {spec.name for spec in TOOL_SPECS if spec.name != "get_daily_structure"}


def get_claude_tools(names: set[str] | None = None) -> list[dict[str, Any]]:
    """Return Claude tool schemas. Pass `names` to restrict to a subset."""
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "input_schema": spec.input_model.model_json_schema(),
        }
        for spec in TOOL_SPECS
        if names is None or spec.name in names
    ]


def run_tool(name: str, input_payload: dict[str, Any]) -> Any:
    if name not in TOOL_HANDLERS:
        raise ValueError(f"Unknown tool: {name}")

    spec = next(spec for spec in TOOL_SPECS if spec.name == name)
    validated_input = spec.input_model.model_validate(input_payload)
    result = TOOL_HANDLERS[name](validated_input)
    return _to_jsonable(result)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value
