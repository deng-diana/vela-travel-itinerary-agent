from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.tools.schemas import ItineraryDraft


AgentEventType = Literal[
    "session",
    "assistant_message",
    "tool_started",
    "tool_completed",
    "final_response",
]


class AgentEvent(BaseModel):
    type: AgentEventType
    message: str | None = None
    tool_name: str | None = None
    payload: Any = None


class ConversationState(BaseModel):
    session_id: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    last_itinerary: ItineraryDraft | None = None


class AgentRunResult(BaseModel):
    reply: str
    events: list[AgentEvent] = Field(default_factory=list)
    itinerary: ItineraryDraft | None = None
