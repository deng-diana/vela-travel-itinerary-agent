from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    """
    Minimal scaffold model for recording tool usage.

    The full assessment build should replace this with richer Pydantic
    request/response schemas for each tool, but the scaffold needs a concrete
    type so the agent and tests can run coherently.
    """

    name: str
    data: Any
    meta: dict[str, Any] = field(default_factory=dict)
