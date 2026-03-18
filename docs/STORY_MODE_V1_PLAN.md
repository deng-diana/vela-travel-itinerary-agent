# Vela Story Mode V1 Plan

## Working Name

**Vela Story Mode**

Tagline:

- turn a completed travel plan into a shareable, interactive trip story

## Why This Exists

The current Vela workspace is strong for **planning in progress**:

- left side = agent conversation
- right side = itinerary canvas that fills live

What it does not yet provide is a polished **presentation layer** for the finished trip.

Story Mode is the missing product layer:

- more emotional than the current canvas
- more interactive than a static itinerary
- more memorable in a demo
- shareable through a copied URL

This is explicitly inspired by the presentation rhythm and interaction principles behind the public `frontend-slides` repo, but it should be implemented as a native Vela feature rather than a direct transplant.

## Product Decision

### Core interaction

Vela should use **two right-panel modes**:

1. `Canvas Mode`
   - default while the agent is still gathering, adapting, or rebuilding
   - best for watching weather, hotels, restaurants, experiences, and day cards populate live

2. `Story Mode`
   - a focused, interactive presentation for a finished itinerary
   - best for reading, presenting, and sharing the plan

### Auto-switch rule

Yes, Vela should **start in Canvas Mode first**, then automatically switch to Story Mode **once the first complete itinerary is ready**.

Recommended rule:

- stay in `Canvas Mode` while tool events are still arriving
- once all of these are true:
  - an itinerary exists
  - `days.length > 0`
  - the final response for that run has arrived
- automatically switch the right panel to `Story Mode`

### Important safeguard

Auto-switch should happen only when it helps, not every time.

Recommended behavior:

- auto-switch only the **first time** a complete itinerary is produced in a session
- if the user manually switches back to `Canvas Mode`, remember that preference for the rest of the session
- if the user later edits the trip from the left chat, keep their chosen mode instead of forcing another switch

This avoids the UI feeling jumpy or patronizing.

## V1 Scope

Because there is less than one day left, V1 should be intentionally narrow.

### Must ship

- one story theme only
- one share flow only
- one public read-only trip page
- one itinerary-to-story transformation layer
- auto-switch from canvas to story after completion
- copy-link button for the published trip

### Must not ship

- multiple themes
- theme picker
- single-file HTML export
- autoplay timeline editor
- embedded map engine
- PDF export
- collaborative editing

## Theme Decision

V1 should use **one theme only**:

- editorial travel guide

The visual direction should feel like:

- high-end travel magazine
- a little cinematic
- elegant but readable
- not generic SaaS cards
- not a clone of the external repo

Suggested design language:

- expressive serif headlines
- crisp sans-serif UI labels
- soft paper or atlas-style background texture
- dark ink, warm ivory, muted coastal green, and a controlled copper accent
- slow fade, stagger, and subtle image zoom

## User Experience

### In-session flow

1. User chats with Vela
2. Right panel stays in `Canvas Mode`
3. Live itinerary builds as usual
4. When the plan is complete, the right panel automatically transitions into `Story Mode`
5. User can still toggle back to `Canvas Mode`
6. A `Publish` button creates a shareable link
7. A `Copy Link` button copies that public URL

### Shared-link flow

1. Someone opens the copied URL in any browser
2. The app loads a published trip snapshot
3. It renders directly into the read-only `Story Mode` page
4. No agent chat is shown
5. The trip behaves like an interactive travel guide, not a workspace

## Technical Strategy

## Guiding principle

Do **not** attempt to reproduce the external repo's packaging model.

Instead:

- borrow its presentation ideas
- keep implementation native to the existing React + FastAPI stack

This is the fastest and safest path.

### Rendering model

Story Mode should be built as a React renderer that consumes a structured `StorySlide[]` model.

Flow:

- `ItineraryDraft` + `PlanningBrief` -> `StorySlide[]`
- `StorySlide[]` -> `TripStoryPlayer`

This keeps the presentation layer clean and testable.

### Page structure

The story page should use:

- full-viewport sections
- vertical scroll snap
- top progress bar
- right-side nav dots
- keyboard navigation
- touch-friendly scrolling
- in-view reveal animation

This gives the feel of a slide story without building a fragile slideshow engine.

## Data and Persistence

## Why publishing is required

The current backend session store is in-memory only, which is correct for agent state but not enough for shareable URLs.

Story Mode links must point to a **published snapshot**, not to the live session.

## V1 persistence choice

Use **SQLite** for V1.

Reasons:

- fast to implement
- no new infrastructure
- no new dependency required if using Python's built-in `sqlite3`
- good enough for assessment/demo use

## Snapshot model

Recommended persisted record:

- `slug`
- `created_at`
- `destination`
- `trip_length_days`
- `planning_brief_json`
- `itinerary_json`
- `summary`

Optional later:

- `theme`
- `hero_image`
- `published_by_session_id`

## URL Strategy

For V1, avoid router complexity.

Use a query-parameter share URL:

- `/?trip=<slug>&view=story`

Reasons:

- no extra routing dependency needed
- no server rewrite rules needed
- easier to land quickly
- works with the current app structure

Clean path routing can be a V2 improvement.

## Slide Model

The itinerary should be transformed into a small number of narrative scenes.

Recommended V1 slides:

1. `cover`
   - destination
   - trip length
   - trip tone

2. `weather`
   - weather snapshot
   - packing notes

3. `stay`
   - selected hotel
   - neighborhood base
   - why this base works

4. `food-highlights`
   - 2 to 4 standout restaurants

5. `experience-highlights`
   - 2 to 4 standout experiences

6. `day-1`
   - arrival framing

7. `day-2-plus`
   - one slide per remaining day

8. `closing`
   - summary
   - practical note or follow-up CTA

## Frontend Architecture

## New frontend pieces

Recommended additions:

- `src/ui/src/components/TripStoryPlayer.tsx`
- `src/ui/src/components/StorySlide.tsx`
- `src/ui/src/lib/story.ts`

## Existing files to update

- `src/ui/src/App.tsx`
- `src/ui/src/components/ItineraryPanel.tsx`
- `src/ui/src/types.ts`
- `src/ui/src/index.css`

## App behavior changes

### `App.tsx`

Responsibilities:

- parse `trip` and `view` from `window.location.search`
- if `trip` exists:
  - load published snapshot from backend
  - render the public Story page
- otherwise run the normal workspace app

### `ItineraryPanel.tsx`

Responsibilities:

- add `Canvas | Story` toggle
- trigger auto-switch after first complete itinerary
- render current canvas or `TripStoryPlayer`
- show `Publish` and `Copy Link` actions when appropriate

### `story.ts`

Responsibilities:

- transform raw itinerary data into `StorySlide[]`
- centralize presentation mapping logic
- keep rendering components simple

## Backend Architecture

## New backend pieces

Recommended additions:

- `src/api/publish_store.py`

## Existing files to update

- `src/api/main.py`
- `src/api/models.py`

## API design

### `POST /plans/publish`

Request:

- `planning_brief`
- `itinerary`

Response:

- `slug`
- `share_url`

Behavior:

- validate snapshot
- persist snapshot
- return copyable URL

### `GET /plans/{slug}`

Response:

- the published plan snapshot

Behavior:

- return read-only JSON for the public Story page
- `404` if not found

## Auto-switch implementation details

The auto-switch should be session-local UI state, not backend state.

Recommended UI state:

- `viewMode: 'canvas' | 'story'`
- `hasAutoSwitchedToStory: boolean`
- `isPublished: boolean`
- `publishedShareUrl: string | null`
- `userLockedViewMode: boolean`

Suggested logic:

- initial state = `canvas`
- when itinerary becomes complete:
  - if `hasAutoSwitchedToStory` is false
  - and `userLockedViewMode` is false
  - switch to `story`
  - set `hasAutoSwitchedToStory = true`
- when user clicks the toggle manually:
  - set `userLockedViewMode = true`

## Motion System

V1 motion should stay elegant and simple.

Allowed:

- staggered reveal
- fade + lift
- image zoom on enter
- progress bar fill
- nav dot state change

Avoid in V1:

- heavy parallax
- 3D card flips
- autoplay storytelling
- particle systems

## Publish UX

Recommended CTA flow:

1. `Publish story`
2. backend returns `share_url`
3. button becomes `Copy link`
4. optional secondary action: `Open story`

Rules:

- if itinerary changes after publish, mark the current share link as outdated
- user must republish to get a fresh snapshot

## Acceptance Criteria

V1 is done when all of the following are true:

- the planning flow still works exactly as before
- the right panel starts in `Canvas Mode`
- once a complete itinerary is ready, the right panel automatically switches to `Story Mode`
- the user can manually switch between `Canvas` and `Story`
- the app can publish a snapshot and return a copyable URL
- the copied URL opens a read-only interactive story page in a browser
- the public page works on desktop and mobile

## Time-Boxed Build Plan

### Phase 1: Publish backend

Estimate:

- 60 to 90 minutes

Build:

- snapshot store
- publish endpoint
- fetch endpoint

### Phase 2: URL-driven public story page

Estimate:

- 45 to 60 minutes

Build:

- query-param detection
- public snapshot fetch
- read-only story render path

### Phase 3: Story renderer

Estimate:

- 2 to 3 hours

Build:

- slide model
- player shell
- cover/weather/stay/day slides
- single theme styling

### Phase 4: Workspace integration

Estimate:

- 60 to 90 minutes

Build:

- auto-switch
- toggle
- publish button
- copy-link feedback

### Phase 5: polish and verification

Estimate:

- 60 minutes

Build:

- motion cleanup
- mobile pass
- smoke tests

## Risks

### Risk 1: trying to build too much

Mitigation:

- one theme only
- no export system
- no router dependency

### Risk 2: public URL complexity

Mitigation:

- use query-param sharing in V1
- use SQLite snapshot storage

### Risk 3: UI becomes jumpy because of auto-switching

Mitigation:

- auto-switch only once
- respect manual override

## Recommendation

This plan is worth implementing.

It adds a strong demo moment without destabilizing the core planning experience.

If time gets tight, the last things to cut should be:

- extra motion flourishes
- advanced closing slide polish
- secondary buttons

The last things to cut should **not** be:

- published snapshot persistence
- copyable share URL
- auto-switch from canvas to story
- manual toggle between modes
