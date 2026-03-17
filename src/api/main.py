from __future__ import annotations

from fastapi import FastAPI

from src.api.dependencies import get_settings


app = FastAPI(
    title="Vela API",
    version="0.1.0",
    description="Scaffold API for the travel itinerary agent assessment.",
)


@app.get("/health")
def healthcheck() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "status": "ok",
        "anthropic_configured": bool(settings.anthropic_api_key),
    }
