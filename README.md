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
- Structured itinerary output with day cards, venue tiles, and booking CTAs

Mock data is acceptable. The assessment is testing product thinking, architecture, orchestration, and UX quality rather than third-party API integration.

## Product Goal

A traveller should be able to:

1. Describe a trip in natural language
2. Answer a few concrete clarifying questions when key trip information is missing
3. Stay in a single-column intake flow until the agent has enough information to plan responsibly
4. Watch hotels, restaurants, experiences, and weather appear in real time once the canvas opens
5. End with a day-by-day plan that feels coherent, clickable, and useful
6. Change a preference mid-conversation and see the plan adapt instead of restarting

## Chosen Technical Direction

The brief leaves the UI stack open. For this project, the target architecture is:

- Backend: FastAPI
- Agent runtime: Anthropic Messages API for intake, clarification, copy polish, and final response
- Data validation: Pydantic v2
- Frontend: React + TypeScript + Vite
- Streaming: Server-Sent Events from FastAPI to the UI
- State: in-memory conversation/session store for the assessment, designed so it can later be replaced by Redis or Postgres

Why this direction:

- FastAPI + SSE is a fast, reliable way to stream itinerary updates into the UI
- React is the fastest route to a polished split-panel product experience
- Vite keeps the frontend simple and avoids overlapping backend concerns with FastAPI
- In-memory session state is enough for an interview build while keeping the architecture clean
- Claude is used where it adds the most value: extracting intent, asking better questions, drafting the itinerary, and warming up the final copy
- Code still provides soft guardrails, quality checks, selective reruns, and repair passes so the plan stays stable

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
    mock_data.py           # fallback data and itinerary scaffolding
    live_weather.py        # Open-Meteo live weather snapshot
    live_restaurants.py    # Google Places restaurant search
    live_experiences.py    # Google Places experience search
    live_hotels.py         # Google Places hotel POI search
    live_daily_structure.py# code-led itinerary planner
  /api
    main.py                # FastAPI app
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

## Data Providers And Hotel CTA Tradeoff

The current build uses a mixed real-data strategy:

- Weather: Open-Meteo live weather snapshot
- Restaurants: Google Places Text Search + Places photo proxy
- Experiences: Google Places Text Search + Places photo proxy
- Hotels: Google Places hotel POI search + Places photo proxy

This was a deliberate tradeoff.

For hotels, the stronger long-term production path would be Booking.com Demand API because it is better suited for real availability, pricing, and affiliate/deep-link flows. However, Booking Demand API requires partner onboarding, authentication, and an affiliate ID, which is not realistic within the time constraints of this assessment build.

Because the PDF explicitly allows mock data and prioritizes product thinking over third-party integrations, the current implementation uses Google hotel POIs plus standard booking/location CTAs instead of a true affiliate hotel integration.

In other words:

- hotel cards use real place data and real images
- hotel CTAs are currently standard outbound links, not affiliate links
- a future production version would replace this with Booking Demand API

## Current Status

The repository now has:

- a single-column intake flow that stays in conversation mode until required trip inputs are known
- a structured `PlanningBrief` stored in session state
- a lead-agent orchestration loop that decides whether to ask, gather, adapt, or plan
- parallel real-data gathering for weather, hotels, restaurants, and experiences
- a Claude-led planning layer that drafts day-by-day structure from real tool context
- a quality rubric plus verify/repair pass before the final itinerary is shown
- selective reruns when user preferences change, instead of rebuilding everything
- Claude-assisted copy polish for warmer, more human itinerary language

The highest-value remaining work is itinerary quality, UI polish, and stronger selective adaptation for more change types.

## Planning Logic

Vela now plans in three stages:

1. Intake and readiness gate
   - Extract the trip brief from conversation
   - Detect missing required information
   - Ask only the missing questions, using concrete examples and options
2. Parallel gather
   - Once the brief is ready, gather weather, hotels, restaurants, and experiences in parallel
3. Compose, verify, and adapt
   - Let Claude draft the itinerary structure from the gathered venue set
   - Run a quality rubric to check coverage, geography, pace, duplication, and interest fit
   - Repair the draft if needed before showing it
   - When the user changes budget, pace, neighborhood, or priorities, selectively rerun only the affected tools

### Minimum information before opening the canvas

The canvas opens only when Vela has enough to build a responsible first draft:

- destination
- dates or month
- trip length
- travel party
- budget
- trip priorities
- constraints or a clear "no special restrictions" confirmation

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

- Replace Google hotel POIs with Booking Demand API for true availability, pricing, and affiliate links
- Add map awareness and travel-time constraints between venues
- Persist sessions and itineraries
- Add budget estimation, packing suggestions, and visa requirements
- Support export to PDF, Wallet, or shareable trip pages
