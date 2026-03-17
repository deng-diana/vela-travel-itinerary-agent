# Vela

Vela is an AI-powered travel itinerary agent built for the Affinity Labs assessment. The goal is to turn a conversational trip request into a realistic multi-day itinerary that builds live in a split-panel UI while the agent works.

## Assessment Requirements

This repository is being built against the original PDF brief. The non-negotiable requirements are:

- FastAPI backend
- Anthropic Claude as the LLM
- Pydantic schemas for tool I/O and API contracts
- A split-panel UI: conversation on the left, live itinerary on the right
- Required tools: `get_hotels`, `get_restaurants`, `get_experiences`, `get_weather`, `get_daily_structure`
- Conversation memory so the plan updates when preferences change mid-chat
- Structured itinerary output with day cards, venue tiles, and affiliate booking links

Mock data is acceptable. The assessment is testing product thinking, architecture, orchestration, and UX quality rather than third-party API integration.

## Product Goal

A traveller should be able to:

1. Describe a trip in natural language
2. Answer a few smart clarifying questions
3. Watch hotels, restaurants, experiences, and weather appear in real time
4. End with a day-by-day plan that feels coherent, clickable, and useful
5. Change a preference mid-conversation and see the plan adapt instead of restarting

## Chosen Technical Direction

The brief leaves the UI stack open. For this project, the target architecture is:

- Backend: FastAPI
- Agent runtime: Anthropic Messages API with tool use
- Data validation: Pydantic v2
- Frontend: React + TypeScript + Vite
- Streaming: Server-Sent Events from FastAPI to the UI
- State: in-memory conversation/session store for the assessment, designed so it can later be replaced by Redis or Postgres

Why this direction:

- FastAPI + SSE is a fast, reliable way to stream itinerary updates into the UI
- React is the fastest route to a polished split-panel product experience
- Vite keeps the frontend simple and avoids overlapping backend concerns with FastAPI
- In-memory session state is enough for an interview build while keeping the architecture clean

## Target Architecture

```text
/src
  /agent
    prompts.py             # system prompt and orchestration instructions
    orchestrator.py        # Claude loop, tool execution, synthesis
    state.py               # conversation and itinerary state models
  /tools
    schemas.py             # tool input/output models
    registry.py            # Claude tool schema definitions
    mock_data.py           # realistic mock hotel/restaurant/experience/weather data
    service.py             # tool execution functions
  /api
    main.py                # FastAPI app
    routes.py              # POST /chat and stream endpoints
    models.py              # API request/response/event models
    dependencies.py        # settings and shared services
  /ui
    ...                    # React app
/tests
  ...                      # unit and integration tests
/docs
  PRD.md
  IMPLEMENTATION_PLAN.md
```

## Current Status

The current repository is an early scaffold, not a finished assessment submission. The next build phase is to replace the simple local intent router with a real tool-driven orchestration loop and add the split-panel UI.

## Local Setup

Install the current Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the backend scaffold:

```bash
uvicorn src.api.main:app --reload
```

## Build Priorities

1. Define typed tool schemas and realistic mock data
2. Implement a conversation-aware Claude orchestration loop
3. Add a streaming chat API that emits UI events as tools complete
4. Build the split-panel frontend
5. Add preference-change handling and itinerary regeneration logic
6. Polish the UI, tests, README, and demo recording

## With More Time

- Replace mock data with live providers for hotels, restaurants, weather, and booking links
- Add map awareness and travel-time constraints between venues
- Persist sessions and itineraries
- Add budget estimation, packing suggestions, and visa requirements
- Support export to PDF, Wallet, or shareable trip pages
