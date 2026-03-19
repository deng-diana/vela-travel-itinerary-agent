# Vela

Vela is an AI-powered travel itinerary agent built for Affinity Labs. It turns a conversational trip request into a structured, day-by-day itinerary that builds live in a split-panel UI while the agent works.

## Demo

[![Watch the demo](https://img.shields.io/badge/▶_Watch_Demo-YouTube-red?style=for-the-badge&logo=youtube)](https://youtu.be/VyTMqK1Nlpc)

A full conversation from initial request to complete itinerary, including a mid-conversation preference change.

## What It Does

A traveller opens Vela, describes a trip in natural language, and watches the itinerary assemble in real time:

1. **Intake** — the agent asks focused clarifying questions until 8 essential fields are filled (destination, dates, party, budget, interests, dietary preferences, accommodation type, trip length)
2. **Research** — weather, hotels, restaurants, and experiences are gathered in parallel from live APIs, with context-aware status updates ("Searching Tokyo hotels…")
3. **Compose** — Claude drafts a day-by-day route from ranked candidates, clustered by neighborhood to minimize transit
4. **Adapt** — changing a preference mid-conversation triggers a selective rerun: only affected tools re-execute, preserving unchanged data

The result is a complete, readable plan with booking links, weather context, budget estimates, packing suggestions, and visa requirements.

## Architecture

```text
src/
  agent/
    orchestrator.py         # Lead agent loop — intake → gather → compose → reply
    intake.py               # 8-field gate, brief extraction, clarifying questions
    research.py             # Tool planning, parallel execution, candidate scoring
    composer.py             # Daily structure generation, verify/repair, polish
    preference_update.py    # Changed-field detection, selective rerun logic
    prompts.py              # System prompt and sub-task prompts
    state.py                # ConversationState, AgentEvent models
    llm_helpers.py          # Claude API response normalization
  tools/
    schemas.py              # All Pydantic I/O models (PlanningBrief, HotelOption, etc.)
    registry.py             # Tool specs, handlers, Claude tool schema generation
    live_weather.py         # Open-Meteo integration
    live_hotels.py          # Google Places hotel search
    live_restaurants.py     # Google Places restaurant search with dedup
    live_experiences.py     # Google Places experience search
    live_daily_structure.py # Code-led itinerary skeleton builder
    live_budget.py          # Budget estimation
    live_visa.py            # Visa requirements
    live_packing.py         # Weather-aware packing suggestions
    mock_data.py            # Fallback data when API keys are absent
  api/
    main.py                 # FastAPI app, /chat/stream SSE endpoint, /places/photo proxy
    models.py               # ChatRequest, ChatResponse
    dependencies.py         # Settings, session store, DI
    publish_store.py        # Shareable trip page storage
  ui/                       # React 19 + TypeScript + Vite + Tailwind CSS 4 + Motion
tests/
  test_agent.py             # Intake gate, selective rerun, tool planning (8 tests)
  test_tools.py             # Tool output structure and coverage (7 tests)
```

## Technical Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Backend | Python 3.13 / FastAPI | Required by spec |
| LLM | Anthropic Claude (claude-opus-4-1-20250805) | Required by spec |
| Data validation | Pydantic v2 | Required by spec |
| Frontend | React 19 / TypeScript / Vite | Fine-grained control over streaming state and progressive rendering |
| Streaming | Server-Sent Events (SSE) | Real-time tool status → incremental UI updates |
| APIs | Google Places (hotels, restaurants, experiences), Open-Meteo (weather) | Live data with mock fallback |

## Key Design Decisions

**1. Single orchestrator with modular phases** — One `AgentOrchestrator` coordinates four phases: intake → research → compose → adapt. Each phase is a separate module (`intake.py`, `research.py`, `composer.py`, `preference_update.py`) that can be tested and iterated independently. This avoids a monolithic agent while keeping the control flow explicit rather than hidden in prompt chaining.

**2. Agentic tool-use loop (standard Anthropic pattern)** — Claude proposes tools → parallel execution via `ThreadPoolExecutor` → results returned to Claude → Claude proposes the next round. Two rounds: Round 1 gathers base data (weather, hotels, restaurants, experiences), Round 2 gathers dependent data (budget, packing) using Round 1 context. Falls back to a deterministic `build_tool_plan()` if the loop fails.

**3. Typed tool I/O via Pydantic** — Every tool has a Pydantic input model and output model in `schemas.py`. The registry auto-generates Claude-compatible JSON schemas from these models. This means tool contracts are validated at both ends — Claude can't pass malformed input, and tool outputs are guaranteed to match the shape the composer expects.

**4. 8-field intake gate** — All essential trip parameters (destination, dates, party, budget, interests, dietary, accommodation type, trip length) must be collected before planning starts. The agent asks clarifying questions with concrete options until the gate passes. No smart defaults that mask missing information — the plan is only as good as the brief.

**5. Selective rerun with code-level enforcement** — When a user changes "budget", a `FIELD_TOOL_DEPENDENCIES` graph determines that only `get_hotels`, `get_restaurants`, and `estimate_budget` need to rerun. This is enforced at the code level: Claude's tool proposals are filtered against a computed `allowed_tools` set before execution. Unchanged tool results are preserved from the previous itinerary via `payloads_from_previous()`.

**6. Candidate scoring before composition** — Hotels, restaurants, and experiences are scored against the planning brief (neighborhood match, interest alignment, rating quality, hidden-gem affinity) and ranked before being passed to the composer. This ensures Claude's day-by-day structure draws from the strongest candidates rather than arbitrary API order.

**7. Neighborhood clustering** — Venues are grouped by neighborhood and assigned to days so each day stays geographically coherent. Day 1 anchors around the hotel neighborhood. This prevents plans where the traveller zig-zags across the city.

**8. SSE streaming with progressive rendering** — Each tool completion emits an SSE event that triggers a visible update on the right panel. The frontend reveals slides sequentially with staggered timing, and skeleton placeholders highlight which section is actively being built — synced with the tool step chain on the left panel.

## Data Providers

| Data | Source | Notes |
|------|--------|-------|
| Weather | Open-Meteo API | Live forecast, no auth required |
| Hotels | Google Places Text Search | Real place data and photos; CTAs link to Google Maps |
| Restaurants | Google Places Text Search | Deduped across queries; heuristic signature dish suggestions |
| Experiences | Google Places Text Search | Category normalization (14 types); duration/cost estimates |
| Budget | Code heuristic | Derived from hotel rates + meal/activity cost tiers |
| Visa | Code heuristic | Based on destination country |
| Packing | Code heuristic | Weather-driven suggestions |

For hotels, the production path would be the Booking.com Demand API for real availability, pricing, and affiliate links. This requires partner onboarding not feasible within the assessment timeframe, so hotel CTAs currently link to Google Maps rather than affiliate booking flows.

## Local Setup

```bash
# Configure environment
cp .env.example .env
# Fill in ANTHROPIC_API_KEY and GOOGLE_MAPS_API_KEY in .env

# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.api.main:app --reload

# Frontend
cd src/ui && npm install && npm run dev
```

## Environment Variables

See [`.env.example`](.env.example) for the full list.

- `ANTHROPIC_API_KEY` — required
- `GOOGLE_MAPS_API_KEY` — required for live data (falls back to mock without it)

## Tests

```bash
pytest tests/ -v
```

15 tests covering intake gate validation, selective rerun logic, tool plan generation, payload preservation, and tool output structure.

## With More Time

- **Verify/repair quality loop** — Re-enable the commented-out verification pass that checks itinerary coverage, geographic coherence, pacing balance, and venue-type diversity, with a Claude-led repair cycle for issues above a severity threshold
- **Replace Google hotel POIs with Booking Demand API** for true availability, real-time pricing, and affiliate deep links
- **Production-grade experience data** — Replace heuristic duration/cost estimates with real API data (e.g., Viator, GetYourGuide) for accurate pricing and bookable tickets
- **Map awareness** — Add travel-time constraints between venues using Google Directions API, ensuring day plans respect actual transit distances
- **User accounts and persistence** — Add authentication, database-backed session storage, and saved itineraries so users can return to modify plans across sessions
- **Export** — Support PDF export and shareable public trip pages (shareable page infrastructure is already built)
