from __future__ import annotations

from pydantic import BaseModel, Field

from src.agent.state import AgentEvent
from src.tools.schemas import ItineraryDraft


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    events: list[AgentEvent]
    itinerary: ItineraryDraft | None = None
