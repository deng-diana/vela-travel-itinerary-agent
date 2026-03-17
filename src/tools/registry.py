from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel

from src.tools.mock_data import (
    get_daily_structure,
    get_experiences,
    get_hotels,
    get_restaurants,
    get_weather,
)
from src.tools.schemas import (
    DailyStructureInput,
    ExperienceSearchInput,
    HotelSearchInput,
    RestaurantSearchInput,
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
        description="Return typical weather for a destination and month, including temperature, rainfall, summary, and packing notes.",
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
]


TOOL_HANDLERS: dict[str, ToolHandler] = {
    "get_weather": get_weather,
    "get_hotels": get_hotels,
    "get_restaurants": get_restaurants,
    "get_experiences": get_experiences,
    "get_daily_structure": get_daily_structure,
}


def get_claude_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "input_schema": spec.input_model.model_json_schema(),
        }
        for spec in TOOL_SPECS
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
