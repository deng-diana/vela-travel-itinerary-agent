import { useState, useEffect, useMemo } from 'react'
import type { FormEvent } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import type {
  AgentStep,
  ChatMessage,
  ItineraryDraft,
  StreamEvent,
  WeatherSummary,
  HotelOption,
  RestaurantOption,
  ExperienceOption,
  DayPlan,
  BudgetEstimate,
  VisaRequirements,
  PackingSuggestions,
} from './types'
import { API_BASE_URL, buildPhotoUrl } from './types'
import { Landing } from './components/Landing'
import { ChatPanel } from './components/ChatPanel'
import { StoryPlayer } from './components/StoryPlayer'
import { buildStory } from './lib/story'

const BLANK_ITINERARY: ItineraryDraft = {
  destination: '',
  month: '',
  trip_length_days: 0,
  interests: [],
  hotels: [],
  restaurants: [],
  experiences: [],
  days: [],
  summary: '',
}

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [steps, setSteps] = useState<AgentStep[]>([])
  const [liveNarration, setLiveNarration] = useState('')
  const [itinerary, setItinerary] = useState<ItineraryDraft | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [workspaceMode, setWorkspaceMode] = useState(false)
  const resetToTop = 0

  // Public story page: ?trip=<slug>
  const [publicSlug] = useState<string | null>(() => {
    const params = new URLSearchParams(window.location.search)
    return params.get('trip')
  })
  const [publicItinerary, setPublicItinerary] = useState<ItineraryDraft | null>(null)
  const [publicLoading, setPublicLoading] = useState(false)
  const [publicError, setPublicError] = useState<string | null>(null)

  // Load public itinerary if ?trip= param is present
  useEffect(() => {
    if (!publicSlug) return
    setPublicLoading(true)
    fetch(`${API_BASE_URL}/plans/${publicSlug}`)
      .then((r) => {
        if (!r.ok) throw new Error(`Plan not found (${r.status})`)
        return r.json()
      })
      .then((data) => {
        setPublicItinerary(data.itinerary as ItineraryDraft)
        setPublicLoading(false)
      })
      .catch((err) => {
        setPublicError(err instanceof Error ? err.message : 'Failed to load plan')
        setPublicLoading(false)
      })
  }, [publicSlug])

  // Build slides incrementally from current itinerary state
  const slides = useMemo(
    () => buildStory(itinerary, buildPhotoUrl),
    [itinerary],
  )

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || isStreaming) return

    setError(null)
    setIsStreaming(true)
    setInput('')
    setMessages((current) => [...current, { role: 'user', text: trimmed }])
    setSteps([])
    setLiveNarration('')

    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: trimmed }),
      })

      if (!response.ok || !response.body) {
        throw new Error(`Stream request failed with status ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop() ?? ''

        for (const chunk of chunks) {
          const parsed = parseSseChunk(chunk)
          if (!parsed) continue
          applyStreamEvent({ type: parsed.event, ...(parsed.data as Record<string, unknown>) })
        }
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unknown stream error')
      setLiveNarration('')
    } finally {
      setIsStreaming(false)
    }
  }

  function applyStreamEvent(streamEvent: StreamEvent) {
    if (streamEvent.type === 'session') {
      const payload = streamEvent.payload as { session_id?: string } | undefined
      if (payload?.session_id) setSessionId(payload.session_id)
      return
    }

    if (streamEvent.type === 'assistant_message' && streamEvent.message) {
      setLiveNarration(streamEvent.message)
      return
    }

    // Immediate workspace transition when backend signals readiness
    if (streamEvent.type === 'workspace_ready') {
      setWorkspaceMode(true)
      const payload = streamEvent.payload as { planning_brief?: { destination?: string; dates_or_month?: string; trip_length_days?: number; priorities?: string[]; travel_party?: string } } | undefined
      if (payload?.planning_brief) {
        const brief = payload.planning_brief
        setItinerary((current) => ({
          ...(current ?? { ...BLANK_ITINERARY }),
          destination: brief.destination ?? '',
          month: brief.dates_or_month ?? '',
          trip_length_days: brief.trip_length_days ?? 0,
          interests: brief.priorities ?? [],
          travel_party: brief.travel_party ?? null,
        }))
      }
      return
    }

    if (streamEvent.type === 'tool_started' && streamEvent.tool_name) {
      setWorkspaceMode(true)
      const step = makeActiveStep(streamEvent.tool_name)
      setSteps((current) => [...current.filter((item) => item.status === 'completed'), step])
      setLiveNarration(step.detail)
      return
    }

    if (streamEvent.type === 'tool_completed' && streamEvent.tool_name) {
      setWorkspaceMode(true)
      const completedStep = makeCompletedStep(streamEvent.tool_name)
      setSteps((current) => {
        const withoutActive = current.filter((item) => item.status === 'completed')
        return [...withoutActive, completedStep]
      })
      setLiveNarration(completedStep.detail)

      setItinerary((current) => {
        const next: ItineraryDraft = current ?? { ...BLANK_ITINERARY }

        switch (streamEvent.tool_name) {
          case 'get_weather':
            next.weather = streamEvent.payload as WeatherSummary
            break
          case 'get_hotels': {
            const hotels = streamEvent.payload as HotelOption[]
            next.hotels = hotels
            next.selected_hotel = hotels[0] ?? null
            break
          }
          case 'get_restaurants':
            next.restaurants = streamEvent.payload as RestaurantOption[]
            break
          case 'get_experiences':
            next.experiences = streamEvent.payload as ExperienceOption[]
            break
          case 'get_daily_structure':
            next.days = streamEvent.payload as DayPlan[]
            break
          case 'estimate_budget':
            next.budget_estimate = streamEvent.payload as BudgetEstimate
            break
          case 'get_visa_requirements':
            next.visa_requirements = streamEvent.payload as VisaRequirements
            break
          case 'get_packing_suggestions':
            next.packing_suggestions = streamEvent.payload as PackingSuggestions
            break
          default:
            break
        }

        return { ...next }
      })
      return
    }

    if (streamEvent.type === 'final_response') {
      if (streamEvent.message) {
        setMessages((current) => [...current, { role: 'assistant', text: streamEvent.message ?? '' }])
      }

      const payload = streamEvent.payload as
        | { itinerary?: ItineraryDraft | null; workspace_ready?: boolean }
        | undefined
      if (payload?.itinerary) setItinerary(payload.itinerary)
      if (payload?.workspace_ready) setWorkspaceMode(true)

      setLiveNarration('')
    }
  }

  // Public story page — standalone full-screen
  if (publicSlug) {
    if (publicLoading) {
      return (
        <div
          className="min-h-screen flex items-center justify-center"
          style={{ background: 'var(--story-bg)', color: 'var(--story-text-muted)', fontFamily: 'var(--font-data)' }}
        >
          Loading trip...
        </div>
      )
    }
    if (publicError || !publicItinerary) {
      return (
        <div
          className="min-h-screen flex items-center justify-center"
          style={{ background: 'var(--story-bg)', color: 'var(--story-text-muted)', fontFamily: 'var(--font-data)' }}
        >
          {publicError ?? 'Trip not found.'}
        </div>
      )
    }
    const publicSlides = buildStory(publicItinerary, buildPhotoUrl)
    return <StoryPlayer slides={publicSlides} fullScreen />
  }

  return (
    <main className="min-h-screen" style={{ background: 'var(--story-bg)' }}>
      <AnimatePresence mode="wait">
        {!workspaceMode ? (
          <Landing
            messages={messages}
            input={input}
            isStreaming={isStreaming}
            liveNarration={liveNarration}
            error={error}
            onInputChange={setInput}
            onSubmit={handleSubmit}
          />
        ) : (
          <motion.section
            key="workspace"
            initial={{ opacity: 0, scale: 0.985 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
            className="h-screen grid grid-cols-1 lg:grid-cols-[480px_minmax(0,1fr)]"
          >
            {/* Left: Chat */}
            <ChatPanel
              sessionId={sessionId}
              messages={messages}
              steps={steps}
              liveNarration={liveNarration}
              isStreaming={isStreaming}
              error={error}
              input={input}
              onInputChange={setInput}
              onSubmit={handleSubmit}
            />

            {/* Right: Story Player — always visible, progressively populated */}
            <div className="hidden lg:block h-screen overflow-hidden">
              <StoryPlayer
                slides={slides}
                isStreaming={isStreaming}
                steps={steps}
                liveNarration={liveNarration}
                itinerary={itinerary}
                resetToTop={resetToTop}
              />
            </div>
          </motion.section>
        )}
      </AnimatePresence>
    </main>
  )
}

// ---------------------------------------------------------------------------
// SSE helpers
// ---------------------------------------------------------------------------

function makeActiveStep(toolName: string): AgentStep {
  const detailByTool: Record<string, string> = {
    analyze_preferences: 'Reading your preferences and planning the research strategy.',
    plan_research: 'Deciding which research tools to run for this trip.',
    get_weather: 'Checking live destination weather and turning it into practical travel context.',
    get_hotels: 'Screening stay options that fit the trip style, neighborhood, and budget.',
    get_restaurants: 'Curating dining options that match the traveler profile and local rhythm.',
    get_experiences: 'Collecting experiences that add texture without breaking the pace.',
    get_daily_structure: 'Organizing everything into a coherent day-by-day route.',
    estimate_budget: 'Calculating a realistic budget breakdown for the trip.',
    get_visa_requirements: 'Looking up entry requirements and visa details.',
    get_packing_suggestions: 'Building a smart packing list based on weather and activities.',
    verify_itinerary: 'Running quality checks — ensuring every day is complete and coherent.',
    polish_copy: 'Rewriting descriptions for warmth, clarity, and a sense of place.',
    write_summary: 'Crafting your final trip summary and travel tips.',
  }

  return {
    id: `${toolName}-active-${Date.now()}`,
    title: prettyToolName(toolName),
    detail: detailByTool[toolName] ?? 'Working on the next planning step.',
    status: 'active',
  }
}

function makeCompletedStep(toolName: string): AgentStep {
  const completedByTool: Record<string, string> = {
    analyze_preferences: 'Preferences analyzed — research plan ready.',
    plan_research: 'Research strategy selected.',
    get_weather: 'Live weather is now grounding the plan.',
    get_hotels: 'Stay options have been added to the itinerary.',
    get_restaurants: 'Dining options are now part of the plan.',
    get_experiences: 'Experience options are ready and mapped into the trip.',
    get_daily_structure: 'The itinerary has been organized into labeled days.',
    estimate_budget: 'Budget breakdown is ready.',
    get_visa_requirements: 'Entry requirements have been looked up.',
    get_packing_suggestions: 'Packing list is ready.',
    verify_itinerary: 'Quality verified — the plan is solid.',
    polish_copy: 'Every description has been polished.',
    write_summary: 'Summary and travel tips are ready.',
  }

  return {
    id: `${toolName}-completed-${Date.now()}`,
    title: prettyToolName(toolName),
    detail: completedByTool[toolName] ?? 'Step completed.',
    status: 'completed',
  }
}

function prettyToolName(toolName: string): string {
  const names: Record<string, string> = {
    analyze_preferences: 'Analyzing trip preferences',
    plan_research: 'plan_research — selecting tools to run',
    get_weather: 'get_weather — fetching live conditions',
    get_hotels: 'get_hotels — screening accommodation',
    get_restaurants: 'get_restaurants — curating dining options',
    get_experiences: 'get_experiences — collecting activities',
    get_daily_structure: 'get_daily_structure — building day-by-day plan',
    estimate_budget: 'estimate_budget — calculating costs',
    get_visa_requirements: 'get_visa_requirements — checking entry rules',
    get_packing_suggestions: 'get_packing_suggestions — building list',
    verify_itinerary: 'verify_itinerary — quality check',
    polish_copy: 'polish_copy — rewriting descriptions',
    write_summary: 'write_summary — composing final reply',
  }
  return names[toolName] ?? toolName
}

function parseSseChunk(chunk: string): { event: string; data: unknown } | null {
  const lines = chunk.split('\n')
  const eventLine = lines.find((line) => line.startsWith('event: '))
  const dataLine = lines.find((line) => line.startsWith('data: '))
  if (!eventLine || !dataLine) return null
  return { event: eventLine.slice(7).trim(), data: JSON.parse(dataLine.slice(6)) }
}

export default App
