# PRD: Vela Travel Itinerary Agent

## 1. Product Summary

Vela is an AI travel planning agent that turns a conversational request into a personalised multi-day itinerary. The product experience is defined by two ideas:

- The agent should ask smart clarifying questions before it acts
- The itinerary should build live in the UI as the agent gathers and organises information

This PRD is intentionally anchored to the original assessment brief and avoids adding product requirements that were not requested.

## 2. User Problem

Planning a trip requires stitching together accommodation, dining, weather, activities, and pacing decisions. Most tools either dump search results or generate a static plan. The assessment asks for something better: an agent that reasons through the trip, explains progress, and produces a structured itinerary the user can actually use.

## 3. Core User Story

Example input from the brief:

> "I'm going to Tokyo for 6 days in August. Mid-range budget, really into food and hidden gems. Travelling as a couple."

The agent should:

1. Understand the request and identify missing information
2. Ask targeted clarifying questions with concrete examples or options
3. Stay in a single-column intake flow until the minimum planning brief is complete
4. Call tools for hotels, restaurants, experiences, and weather
5. Synthesize the results into a coherent day-by-day plan
6. Render the itinerary live as data arrives
7. Update the plan when the user changes preferences mid-conversation

## 4. Product Principles

### 4.1 Ask Before Acting

The first response should not blindly generate a plan. It should confirm missing constraints such as neighborhood preference, accommodation style, dietary restrictions, or pace.

Clarifying questions should be concrete and easy to answer. For example:

- "Do you want a slower pace, or do you want to fit in as much as possible?"
- "Would you rather stay in a lively central area, or somewhere quieter and more local?"
- "Is this trip mainly about food, art, classic landmarks, or hidden gems?"

### 4.2 Show Progress, Not Hidden Reasoning

The UI can show agent activity and tool status, such as "Searching hotels in Shinjuku". It should not rely on exposing chain-of-thought. The user needs confidence and visibility, not raw internal reasoning.

### 4.3 Build a Traveller-Usable Output

The final itinerary should feel concrete and actionable:

- clear day cards
- sensible venue sequencing
- realistic pacing
- visible booking CTAs or affiliate links

### 4.4 Adapt Instead of Restarting

If the user changes a preference, the plan should evolve from the current conversation context rather than resetting from scratch.

### 4.5 Structure First, Warmth Second

The itinerary should be drafted by the model using real tool context, then checked and corrected by a planning layer with soft guardrails. This keeps the plan expressive and warm without letting it drift into generic or repetitive output.

### 4.6 Verify Before Showing

The agent should not assume the first draft is good enough. Before the final itinerary is shown, the system should verify it against a quality rubric:

- enough coverage across each day
- limited repetition
- geographically sensible clustering
- pacing that matches the brief
- strong fit to the traveller's goals
- respect for stated constraints
- at least one or two memorable anchors

If the draft fails the rubric, the system should repair it rather than showing a low-value plan.

## 5. Functional Requirements

### 5.1 Required Backend

- `POST /chat` endpoint with conversation state
- agent orchestration loop that decides whether to ask clarifying questions, gather tools, adapt an existing plan, or build a new one
- Pydantic request/response models
- structured tool definitions and a planning brief stored in state

### 5.2 Required Tools

All tools may use mock data, but the shape and semantics should feel realistic.

| Tool | Required Output |
| --- | --- |
| `get_hotels` | name, category (`budget` / `mid` / `luxury`), nightly rate, affiliate booking link, key highlights |
| `get_restaurants` | name, cuisine, price range, neighborhood, must-order dish, reservation or affiliate link |
| `get_experiences` | activity name, category, duration, cost, booking link |
| `get_weather` | average temperature, rainfall, condition summary, packing notes |
| `get_daily_structure` | sequenced day-by-day itinerary that respects geography and opening hours |

Bonus tools:

- `estimate_budget`
- `get_visa_requirements`
- `get_packing_suggestions`

### 5.3 Required Frontend Experience

The product should behave in two stages:

- Stage 1: single-column intake while the agent gathers missing planning inputs
- Stage 2: split-panel workspace once the brief is ready
  - Left panel: conversation and agent status
  - Right panel: live itinerary canvas

Required right-panel behavior:

- when `get_weather` completes, show a weather summary strip
- when `get_hotels` completes, show hotel options and highlight the selected stay
- when `get_restaurants` or `get_experiences` complete, populate venue cards into day slots or staging areas
- when `get_daily_structure` completes, organize everything into a labelled day-by-day itinerary
- every venue card must include a visible booking CTA or affiliate link

### 5.4 Memory and Adaptation

The system must retain enough conversation context to support preference changes such as:

- "Make it more romantic"
- "Swap the luxury hotel for something cheaper"
- "Add more food experiences"
- "Move one day slower because we land late"

The implementation should treat these as patches to the current planning brief, not as a new trip request. The system should rerun only the affected planning steps wherever possible.

### 5.5 Minimum Planning Brief

The agent should not open the full itinerary canvas until it knows:

- destination
- dates or month
- trip length
- travel party
- budget
- top priorities
- constraints, or an explicit confirmation that there are no special constraints

## 6. Technical Decisions

These are implementation choices for this repository, not extra assessment requirements.

### 6.1 Backend

- FastAPI for API endpoints and streaming
- Anthropic Claude for intent extraction, clarifying questions, copy polish, and final response
- Pydantic v2 for tool and API schemas
- in-memory session state for the assessment build
- model-led itinerary drafting with code-based quality verification and adaptive updates

### 6.2 Frontend

- React + TypeScript + Vite
- split-panel layout with streaming updates from the backend
- optimistic, event-driven rendering rather than waiting for a single final response

### 6.3 Orchestration Model

The preferred architecture is:

- one lead agent
- one structured planning brief in session state
- parallel tool gathering for weather, hotels, restaurants, and experiences
- one planning layer that gives Claude the gathered venue set and trip brief
- one verification layer that checks quality and triggers repair if needed
- one polishing layer that makes the final copy warmer and more useful

This is preferred over multiple independent LLM sub-agents because it is easier to debug, cheaper to run, and more stable when the user changes preferences.

### 6.4 Streaming Model

The UI should receive structured events, for example:

- `assistant_message`
- `tool_started`
- `tool_completed`
- `itinerary_patch`
- `final_itinerary`

This allows the right panel to evolve progressively as tools finish.

## 7. Suggested Data Model

The implementation should converge on a small set of typed domain objects:

- `ConversationState`
- `PlanningBrief`
- `PlanningBriefPatch`
- `ToolInvocation`
- `ToolResult`
- `VenueCard`
- `DayPlan`
- `ItineraryDraft`

This keeps the agent loop, API layer, and UI speaking the same language.

## 8. Success Criteria

The build is successful when:

- the repository has a clean separation between agent logic, tools, API, and UI
- the agent performs multiple tool calls and synthesizes results instead of concatenating them
- the agent asks for missing information before it starts planning
- the UI feels like a coherent product, not a debug console
- the user can change a preference mid-conversation and the itinerary updates without restarting from scratch
- the output is believable enough that a real traveller could use it

## 9. Delivery Checklist

Before submission, the project should include:

1. a public GitHub repository
2. a working README with setup instructions, architecture decisions, and future improvements
3. a screen recording showing:
   - the initial request
   - clarifying questions
   - live itinerary construction
   - at least one mid-conversation preference change

## 10. Explicit Non-Goals for This Assessment

To stay focused, the first shipping version does not need:

- persistent production infrastructure
- authentication or multi-user collaboration
- full cost optimization or route planning
