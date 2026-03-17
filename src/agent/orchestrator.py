from __future__ import annotations

from dataclasses import dataclass

from src.agent.prompts import SYSTEM_PROMPT
from src.tools.mock_data import get_weather, search_hotels, search_restaurants
from src.tools.schemas import ToolResult


@dataclass
class AgentOrchestrator:
    """
    Minimal orchestrator:
    - Detects simple intents (weather/hotel/restaurant) and calls local mock tools.
    - Otherwise falls back to a deterministic assistant response.
    """

    system_prompt: str = SYSTEM_PROMPT

    def run(self, message: str) -> tuple[str, list[ToolResult]]:
        msg = (message or "").strip()
        used: list[ToolResult] = []

        city = _extract_city(msg)
        if city and ("天气" in msg or "weather" in msg.lower()):
            data = get_weather(city)
            used.append(ToolResult(name="get_weather", data=data))
            reply = f"{data['city']}：{data['condition']}，{data['temp_c']}°C"
            return reply, used

        if city and ("酒店" in msg or "hotel" in msg.lower()):
            data = search_hotels(city)
            used.append(ToolResult(name="search_hotels", data=data))
            if not data:
                return f"没找到 {city} 的酒店数据。", used
            top = data[0]
            return f"{city} 推荐：{top['name']}（¥{top['price_per_night']}/晚）", used

        if city and ("餐厅" in msg or "restaurant" in msg.lower()):
            data = search_restaurants(city)
            used.append(ToolResult(name="search_restaurants", data=data))
            if not data:
                return f"没找到 {city} 的餐厅数据。", used
            top = data[0]
            return f"{city} 推荐：{top['name']}（{top['cuisine']}）", used

        return "我在的。你想查询哪个城市的天气/酒店/餐厅？", used


def _extract_city(text: str) -> str | None:
    # Very small heuristic for the scaffold; can be replaced by LLM parsing later.
    for city in ("Shanghai", "Hangzhou", "上海", "杭州"):
        if city in text:
            return "Shanghai" if city in ("Shanghai", "上海") else "Hangzhou"
    return None

