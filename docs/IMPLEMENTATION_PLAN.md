# Implementation Plan

This plan is optimized for interview-speed delivery without sacrificing architecture quality.

## Phase 1: Lock the Domain Model

Goal:

- define the language of the system before wiring Claude or the UI

Build:

- Pydantic models for hotel, restaurant, experience, weather, venue card, day plan, itinerary
- tool input/output schemas
- API event schemas for streaming updates

Definition of done:

- every required tool has typed inputs and outputs
- tests validate shape and required fields

## Phase 2: Build the Tool Layer

Goal:

- make tool outputs realistic enough for product-quality rendering

Build:

- `get_hotels`
- `get_restaurants`
- `get_experiences`
- `get_weather`
- `get_daily_structure`

Important constraints:

- include affiliate links or CTA URLs
- return realistic neighborhoods, durations, pricing, and highlights
- make `get_daily_structure` respect geography and opening-hour assumptions

Definition of done:

- each tool can run independently with deterministic mock data
- tests cover happy-path and empty-state behavior

## Phase 3: Implement the Agent Loop

Goal:

- move from a keyword router to a real orchestration system

Build:

- system prompt that teaches clarifying-first behavior
- conversation-state model
- Claude tool registry
- orchestration loop that:
  - checks whether clarification is needed
  - calls tools in sequence
  - emits structured UI events
  - synthesizes a final itinerary summary

Definition of done:

- the agent asks questions when information is missing
- the agent performs multiple tool calls for a typical trip request
- a preference change updates the state and triggers a revised plan

## Phase 4: Expose a Streaming API

Goal:

- give the frontend progressive updates instead of one blocking response

Build:

- `POST /chat` endpoint
- session-aware request model
- SSE stream of agent events

Definition of done:

- a client can send a message and receive ordered events for tool start, tool completion, itinerary patch, and final response

## Phase 5: Build the Split-Panel UI

Goal:

- turn the backend into a product, not just a demo API

Build:

- left chat panel
- right itinerary panel
- weather strip
- selected hotel card
- day-by-day itinerary cards
- CTA buttons on venue cards
- visible activity feed for agent progress

Definition of done:

- the user can watch the itinerary populate live as tools complete
- the layout works on laptop and mobile widths

## Phase 6: Polish for Submission

Goal:

- make the assessment feel production-minded

Build:

- empty states and loading states
- error handling
- visual polish
- tighter README
- screen recording script and demo flow

Definition of done:

- the recorded demo is smooth
- the repo structure is easy to explain in interview
- there is one strong end-to-end user story with a mid-conversation change

## Recommended Build Order for the Next Working Session

1. implement `src/tools/schemas.py`
2. rebuild `src/tools/mock_data.py` around required tool names and fields
3. implement `src/agent/state.py` and a real `ToolResult`
4. replace `src/agent/orchestrator.py` with a multi-step tool orchestration loop
5. implement `src/api/main.py` and streaming models
6. add the frontend

## Questions to Keep Asking During the Build

- If I were the traveller, would this output help me make a real decision?
- Does each UI update reduce uncertainty, or is it just visual noise?
- If the user changes one preference, can the system update intelligently without starting over?
- Can I explain why each architectural choice exists in under 30 seconds?
