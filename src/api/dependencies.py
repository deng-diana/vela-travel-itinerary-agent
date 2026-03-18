from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from src.agent.orchestrator import AgentOrchestrator
from src.agent.state import ConversationState

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "7200"))  # 2 hours


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None
    anthropic_model: str
    google_maps_api_key: str | None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-opus-4-1-20250805"),
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY"),
    )
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY is not set — API calls will fail at runtime")
    if not settings.google_maps_api_key:
        logger.warning("GOOGLE_MAPS_API_KEY is not set — will fall back to mock data")
    return settings


@dataclass
class SessionStore:
    sessions: dict[str, ConversationState] = field(default_factory=dict)
    _timestamps: dict[str, float] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def get_or_create(self, session_id: str | None) -> ConversationState:
        with self._lock:
            self._evict_expired()
            if session_id and session_id in self.sessions:
                self._timestamps[session_id] = time.time()
                return self.sessions[session_id]

            resolved_id = session_id or str(uuid4())
            state = ConversationState(session_id=resolved_id)
            self.sessions[resolved_id] = state
            self._timestamps[resolved_id] = time.time()
            return state

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [
            sid for sid, ts in self._timestamps.items()
            if now - ts > SESSION_TTL_SECONDS
        ]
        for sid in expired:
            del self.sessions[sid]
            del self._timestamps[sid]
        if expired:
            logger.info("Evicted %d expired sessions", len(expired))


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
