from __future__ import annotations

from pydantic import BaseModel, Field

from src.agent.state import AgentEvent
from src.tools.schemas import ItineraryDraft, PlanningBrief


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    events: list[AgentEvent]
    itinerary: ItineraryDraft | None = None
    workspace_ready: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    planning_brief: PlanningBrief | None = None


class PublishRequest(BaseModel):
    itinerary: dict


class PublishResponse(BaseModel):
    slug: str
    share_url: str


class PlanSnapshot(BaseModel):
    slug: str
    itinerary: dict
