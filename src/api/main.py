from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.api.dependencies import get_orchestrator, get_session_store, get_settings
from src.api.models import ChatRequest, ChatResponse


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
            for event in orchestrator.stream(state=state, user_message=request.message):
                yield _format_sse(event.type, event.model_dump(mode="json"))

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _format_sse(event_name: str, payload: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
