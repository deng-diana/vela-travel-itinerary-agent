from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from src.agent.prompts import SYSTEM_PROMPT
from src.agent.state import AgentEvent, AgentRunResult, ConversationState
from src.tools.registry import get_claude_tools, run_tool
from src.tools.schemas import (
    DailyStructureInput,
    DayPlan,
    ExperienceOption,
    HotelOption,
    ItineraryDraft,
    RestaurantOption,
    WeatherSummary,
)


@dataclass
class AgentOrchestrator:
    client: Any
    model: str
    system_prompt: str = SYSTEM_PROMPT
    max_tokens: int = 1800

    def run(self, state: ConversationState, user_message: str) -> AgentRunResult:
        messages = list(state.messages)
        messages.append({"role": "user", "content": user_message.strip()})

        events: list[AgentEvent] = []
        tool_inputs: dict[str, dict[str, Any]] = {}
        tool_payloads: dict[str, Any] = {}

        response = self._create_message(messages)

        while getattr(response, "stop_reason", None) == "tool_use":
            assistant_blocks = self._normalize_blocks(response.content)
            messages.append({"role": "assistant", "content": assistant_blocks})

            preface = self._extract_text(assistant_blocks)
            if preface:
                events.append(AgentEvent(type="assistant_message", message=preface))

            tool_results = []
            for block in assistant_blocks:
                if block.get("type") != "tool_use":
                    continue

                tool_name = block["name"]
                tool_input = block.get("input", {})
                tool_inputs[tool_name] = tool_input
                events.append(
                    AgentEvent(
                        type="tool_started",
                        tool_name=tool_name,
                        message=f"Running {tool_name}",
                    )
                )

                try:
                    tool_output = run_tool(tool_name, tool_input)
                    tool_payloads[tool_name] = tool_output
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block["id"],
                            "content": json.dumps(tool_output, ensure_ascii=False),
                        }
                    )
                    events.append(
                        AgentEvent(
                            type="tool_completed",
                            tool_name=tool_name,
                            payload=tool_output,
                        )
                    )
                except Exception as exc:  # pragma: no cover - defensive path
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block["id"],
                            "content": str(exc),
                            "is_error": True,
                        }
                    )
                    events.append(
                        AgentEvent(
                            type="tool_completed",
                            tool_name=tool_name,
                            payload={"error": str(exc)},
                        )
                    )

            messages.append({"role": "user", "content": tool_results})
            response = self._create_message(messages)

        final_blocks = self._normalize_blocks(response.content)
        messages.append({"role": "assistant", "content": final_blocks})

        reply = self._extract_text(final_blocks)
        itinerary = self._build_itinerary(tool_inputs, tool_payloads, reply, state.last_itinerary)

        state.messages = messages
        state.last_itinerary = itinerary

        events.append(AgentEvent(type="final_response", message=reply))
        return AgentRunResult(reply=reply, events=events, itinerary=itinerary)

    def _create_message(self, messages: list[dict[str, Any]]) -> Any:
        return self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            tools=get_claude_tools(),
            messages=messages,
        )

    def _normalize_blocks(self, blocks: Any) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for block in blocks:
            if hasattr(block, "model_dump"):
                normalized.append(block.model_dump(exclude_none=True))
                continue

            block_type = getattr(block, "type", None)
            payload = {"type": block_type}
            for field in ("id", "name", "input", "text"):
                if hasattr(block, field):
                    payload[field] = getattr(block, field)
            normalized.append(payload)
        return normalized

    def _extract_text(self, blocks: list[dict[str, Any]]) -> str:
        texts = [block["text"] for block in blocks if block.get("type") == "text" and block.get("text")]
        return "\n".join(texts).strip()

    def _build_itinerary(
        self,
        tool_inputs: dict[str, dict[str, Any]],
        tool_payloads: dict[str, Any],
        reply: str,
        previous: ItineraryDraft | None,
    ) -> ItineraryDraft | None:
        if "get_daily_structure" not in tool_payloads:
            return previous

        daily_input = DailyStructureInput.model_validate(tool_inputs["get_daily_structure"])
        days = [DayPlan.model_validate(day) for day in tool_payloads["get_daily_structure"]]

        weather = None
        if "get_weather" in tool_payloads:
            weather = WeatherSummary.model_validate(tool_payloads["get_weather"])
        elif previous:
            weather = previous.weather

        hotels = [HotelOption.model_validate(item) for item in tool_payloads.get("get_hotels", [])]
        if not hotels and previous:
            hotels = previous.hotels

        restaurants = [RestaurantOption.model_validate(item) for item in tool_payloads.get("get_restaurants", [])]
        if not restaurants and previous:
            restaurants = previous.restaurants

        experiences = [ExperienceOption.model_validate(item) for item in tool_payloads.get("get_experiences", [])]
        if not experiences and previous:
            experiences = previous.experiences

        selected_hotel = next(
            (hotel for hotel in hotels if hotel.name.lower() == daily_input.hotel_name.lower()),
            hotels[0] if hotels else (previous.selected_hotel if previous else None),
        )

        return ItineraryDraft(
            destination=daily_input.destination,
            month=daily_input.month,
            trip_length_days=daily_input.trip_length_days,
            travel_party=daily_input.travel_party,
            budget=daily_input.budget,
            interests=daily_input.interests,
            weather=weather,
            selected_hotel=selected_hotel,
            hotels=hotels,
            restaurants=restaurants,
            experiences=experiences,
            days=days,
            summary=reply or (previous.summary if previous else "Trip plan updated."),
        )
