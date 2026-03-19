from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.tools.schemas import ItineraryDraft, PlanningBrief


AgentEventType = Literal[
    "session",
    "assistant_message",
    "tool_started",
    "tool_completed",
    "final_response",
    "workspace_ready",
]


class AgentEvent(BaseModel):
    type: AgentEventType
    message: str | None = None
    tool_name: str | None = None
    payload: Any = None


class ConversationState(BaseModel):
    session_id: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    planning_brief: PlanningBrief = Field(default_factory=PlanningBrief)
    workspace_ready: bool = False
    intake_followup_asked: bool = False
    last_itinerary: ItineraryDraft | None = None


class AgentRunResult(BaseModel):
    reply: str
    events: list[AgentEvent] = Field(default_factory=list)
    itinerary: ItineraryDraft | None = None
    workspace_ready: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    planning_brief: PlanningBrief = Field(default_factory=PlanningBrief)
