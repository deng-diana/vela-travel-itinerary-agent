"""Shared helpers for parsing Claude API responses."""
from __future__ import annotations

import json
import re
from typing import Any


def parse_json_block(text: str) -> dict[str, Any]:
    """Extract and parse a JSON block from Claude's response text."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def normalize_blocks(blocks: Any) -> list[dict[str, Any]]:
    """Normalize Claude response content blocks to plain dicts."""
    normalized: list[dict[str, Any]] = []
    for block in blocks:
        if hasattr(block, "model_dump"):
            normalized.append(block.model_dump(exclude_none=True))
            continue

        block_type = getattr(block, "type", None)
        payload: dict[str, Any] = {"type": block_type}
        for field in ("id", "name", "input", "text"):
            if hasattr(block, field):
                payload[field] = getattr(block, field)
        normalized.append(payload)
    return normalized


def extract_text(blocks: list[dict[str, Any]]) -> str:
    """Join text blocks from normalized Claude response content."""
    texts = [block["text"] for block in blocks if block.get("type") == "text" and block.get("text")]
    return "\n".join(texts).strip()
