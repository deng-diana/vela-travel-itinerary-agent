from __future__ import annotations

from fastapi import FastAPI, HTTPException

from src.api.dependencies import get_orchestrator, get_session_store, get_settings
from src.api.models import ChatRequest, ChatResponse


app = FastAPI(
    title="Vela API",
    version="0.1.0",
    description="Travel itinerary agent API for the Affinity Labs",
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
