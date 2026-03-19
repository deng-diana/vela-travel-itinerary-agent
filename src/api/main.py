from __future__ import annotations

import json
import logging
import os

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse

from src.api.dependencies import get_orchestrator, get_session_store, get_settings
from src.api.models import ChatRequest, ChatResponse, PublishRequest, PublishResponse, PlanSnapshot
from src.api.publish_store import get_plan, publish_plan

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Vela API",
    version="0.1.0",
    description="Travel itinerary agent API for the Affinity Labs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def healthcheck() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "status": "ok",
        "anthropic_configured": bool(settings.anthropic_api_key),
        "model": settings.anthropic_model,
    }


@app.get("/places/photo")
def place_photo(name: str = Query(..., min_length=10), max_width_px: int = Query(800, ge=200, le=1600)) -> RedirectResponse:
    settings = get_settings()
    if not settings.google_maps_api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_MAPS_API_KEY is not configured.")

    try:
        response = httpx.get(
            f"https://places.googleapis.com/v1/{name}/media",
            params={
                "key": settings.google_maps_api_key,
                "maxWidthPx": max_width_px,
                "skipHttpRedirect": "true",
            },
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()
        photo_uri = payload.get("photoUri")
        if not photo_uri:
            raise HTTPException(status_code=404, detail="Photo not available.")
        return RedirectResponse(photo_uri)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Failed to fetch Google Places photo.") from exc


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        store = get_session_store()
        state = store.get_or_create(request.session_id)
        orchestrator = get_orchestrator()
        result = orchestrator.run(state=state, user_message=request.message)
        return ChatResponse(
            session_id=state.session_id,
            reply=result.reply,
            events=result.events,
            itinerary=result.itinerary,
            workspace_ready=result.workspace_ready,
            missing_fields=result.missing_fields,
            planning_brief=result.planning_brief,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    try:
        store = get_session_store()
        state = store.get_or_create(request.session_id)
        orchestrator = get_orchestrator()

        def event_stream():
            try:
                for event in orchestrator.stream(state=state, user_message=request.message):
                    yield _format_sse(event.type, event.model_dump(mode="json"))
            except Exception as exc:
                logger.exception("Stream error")
                error_event = {
                    "type": "error",
                    "message": f"Server error: {exc}",
                    "tool_name": None,
                    "payload": None,
                }
                yield _format_sse("error", error_event)

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/plans/publish", response_model=PublishResponse)
def plans_publish(request: PublishRequest, req: Request) -> PublishResponse:
    slug = publish_plan(request.itinerary)
    frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    share_url = f"{frontend_origin}/?trip={slug}"
    return PublishResponse(slug=slug, share_url=share_url)


@app.get("/plans/{slug}", response_model=PlanSnapshot)
def plans_get(slug: str) -> PlanSnapshot:
    itinerary = get_plan(slug)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    return PlanSnapshot(slug=slug, itinerary=itinerary)


def _format_sse(event_name: str, payload: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
