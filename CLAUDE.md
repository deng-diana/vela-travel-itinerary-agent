# CLAUDE.md - Vela Travel Itinerary Agent

## What This Is
Vela is a travel itinerary agent built for the Affinity Labs interview assessment. It turns a conversational trip request into a structured day-by-day itinerary rendered live in a split-panel UI.

## Evaluation Rubric (drives all decisions)
- Agent architecture: 25% — clean separation, extensibility, intentional prompts
- Tool design: 20% — Pydantic-typed, Claude-callable, realistic data
- Multi-step reasoning: 20% — synthesis across tools, not concatenation
- UI/UX: 15% — split-panel feels like a real product, progressive rendering
- Conversation handling: 10% — context, clarifying questions, preference adaptation
- Code quality: 5% — typed, readable, error handling
- Product thinking: 5% — would a traveller actually use this?

## Tech Stack
- Backend: Python 3.13+ / FastAPI / Pydantic v2
- LLM: Anthropic Claude (claude-opus-4-1-20250805)
- Frontend: React 19 / TypeScript / Vite / Tailwind CSS 4 / Motion
- APIs: Google Places (hotels, restaurants, experiences), Open-Meteo (weather)
- Streaming: Server-Sent Events (SSE)

## Project Structure
```
src/
  agent/
    orchestrator.py    # Main agent loop - coordinates intake, research, compose, adapt
    intake.py          # Brief extraction, slot detection, clarifying questions
    research.py        # Tool planning, parallel execution, candidate ranking/scoring
    composer.py        # Daily structure generation, verify/repair, polish
    preference_update.py # Changed-field detection, selective rerun logic
    prompts.py         # System prompt and sub-task prompts
    state.py           # ConversationState, AgentEvent, AgentRunResult models
  tools/
    schemas.py         # All Pydantic I/O models (PlanningBrief, HotelOption, etc.)
    registry.py        # Tool specs, handlers, Claude tool schema generation
    live_weather.py    # Open-Meteo integration
    live_hotels.py     # Google Places hotel search
    live_restaurants.py # Google Places restaurant search with dedup
    live_experiences.py # Google Places experience search
    live_daily_structure.py # Code-led itinerary skeleton builder
    mock_data.py       # Fallback data for Tokyo, Paris
  api/
    main.py            # FastAPI app, /chat/stream SSE endpoint, /places/photo proxy
    models.py          # ChatRequest, ChatResponse
    dependencies.py    # Settings, session store, DI
  ui/
    src/App.tsx        # Main React app
    src/components/    # Extracted UI components
    src/index.css      # Styles with travel-warm palette
tests/
```

## Key Architectural Decisions
1. **Single orchestrator with modular phases** — intake -> research -> compose -> adapt
2. **PlanningBrief + PlanningBriefPatch** — slot-filling pattern for progressive info gathering
3. **Claude tool-use loop** — Claude decides which tools to call via `tools` parameter
4. **Parallel tool execution** — ThreadPoolExecutor for concurrent API calls
5. **Verify/repair loop** — quality rubric check before showing itinerary
6. **Selective rerun** — only re-execute tools affected by preference changes
7. **SSE streaming** — structured events drive progressive UI rendering

## Running Locally
```bash
# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.api.main:app --reload

# Frontend
cd src/ui && npm install && npm run dev
```

## Environment Variables (.env)
- ANTHROPIC_API_KEY — required
- GOOGLE_MAPS_API_KEY — required for live data (falls back to mock)

## Conventions
- All tool I/O uses Pydantic models in `src/tools/schemas.py`
- SSE events: session, assistant_message, tool_started, tool_completed, final_response
- Bilingual support: detect Chinese characters -> respond in Chinese
- Budget tiers: "budget" | "mid" | "luxury"
- Pace levels: "slow" | "balanced" | "packed"

## Testing
```bash
pytest tests/ -v
```
