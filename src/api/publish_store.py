"""
publish_store.py — SQLite-backed store for published trip snapshots.

Table: published_plans(slug TEXT PK, created_at TEXT, destination TEXT, itinerary_json TEXT)
"""
from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "published_plans.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS published_plans (
            slug        TEXT PRIMARY KEY,
            created_at  TEXT NOT NULL,
            destination TEXT NOT NULL,
            itinerary_json TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def publish_plan(itinerary: dict) -> str:
    """Store itinerary snapshot, return slug."""
    slug = secrets.token_urlsafe(8)
    destination = itinerary.get("destination", "Unknown")
    created_at = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    conn.execute(
        "INSERT INTO published_plans (slug, created_at, destination, itinerary_json) VALUES (?, ?, ?, ?)",
        (slug, created_at, destination, json.dumps(itinerary, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()
    return slug


def get_plan(slug: str) -> dict | None:
    """Retrieve itinerary snapshot by slug, or None if not found."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT itinerary_json FROM published_plans WHERE slug = ?", (slug,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return json.loads(row[0])
