from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"))
