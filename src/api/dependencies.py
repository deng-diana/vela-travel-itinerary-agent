from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from src.agent.orchestrator import AgentOrchestrator
from src.agent.state import ConversationState

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None
    anthropic_model: str
    google_maps_api_key: str | None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-opus-4-1-20250805"),
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY"),
    )


@dataclass
class SessionStore:
    sessions: dict[str, ConversationState] = field(default_factory=dict)

    def get_or_create(self, session_id: str | None) -> ConversationState:
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]

        resolved_id = session_id or str(uuid4())
        state = ConversationState(session_id=resolved_id)
        self.sessions[resolved_id] = state
        return state


@lru_cache(maxsize=1)
def get_session_store() -> SessionStore:
    return SessionStore()


def get_anthropic_client():
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

    from anthropic import Anthropic

    return Anthropic(api_key=settings.anthropic_api_key)


def get_orchestrator() -> AgentOrchestrator:
    settings = get_settings()
    return AgentOrchestrator(
        client=get_anthropic_client(),
        model=settings.anthropic_model,
    )
