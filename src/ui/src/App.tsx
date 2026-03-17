import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { AnimatePresence, motion } from 'motion/react'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
type ChatMessage = { role: 'user' | 'assistant'; text: string }
type StreamEvent = { type: string; message?: string | null; tool_name?: string | null; payload?: unknown }
type AgentStep = { id: string; title: string; detail: string; status: 'active' | 'completed' }
type WeatherSummary = {
  destination: string
  month: string
  avg_temp_c: number | null
  rainfall_mm: number | null
  conditions_summary: string
  packing_notes: string[]
}
type HotelOption = {
  id: string
  name: string
  neighborhood: string
  category: string
  nightly_rate_usd: number
  affiliate_link: string
  key_highlights: string[]
}
type RestaurantOption = {
  id: string
  name: string
  cuisine: string
  neighborhood: string
  must_order_dish: string
  reservation_link: string
}
type ExperienceOption = { id: string; name: string; category: string; neighborhood: string; booking_link: string }
type DayItem = {
  time_label: string
  kind: string
  title: string
  neighborhood?: string | null
  description: string
  booking_link?: string | null
}
type DayPlan = { day_number: number; theme: string; summary: string; items: DayItem[] }
type ItineraryDraft = {
  destination: string
  month: string
  trip_length_days: number
  interests: string[]
  weather?: WeatherSummary | null
  selected_hotel?: HotelOption | null
  hotels: HotelOption[]
  restaurants: RestaurantOption[]
  experiences: ExperienceOption[]
  days: DayPlan[]
  summary: string
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
  const [showHistory, setShowHistory] = useState(false)
  const [workspaceMode, setWorkspaceMode] = useState(false)
  const transcriptEndRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, liveNarration, steps])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || isStreaming) return

    setWorkspaceMode(true)
    setError(null)
    setIsStreaming(true)
    setMessages((current) => [...current, { role: 'user', text: trimmed }])
    setSteps([])
    setLiveNarration('Reading the request and shaping the first planning moves.')

    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: trimmed,
        }),
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

          const streamEvent: StreamEvent = {
            type: parsed.event,
            ...(parsed.data as Record<string, unknown>),
          }

          applyStreamEvent(streamEvent)
        }
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unknown stream error')
      setLiveNarration('')
    } finally {
      setIsStreaming(false)
      setInput('')
    }
  }

  function applyStreamEvent(streamEvent: StreamEvent) {
    if (streamEvent.type === 'session') {
      const payload = streamEvent.payload as { session_id?: string } | undefined
      if (payload?.session_id) {
        setSessionId(payload.session_id)
      }
      return
    }

    if (streamEvent.type === 'assistant_message' && streamEvent.message) {
      setLiveNarration(streamEvent.message)
      return
    }

    if (streamEvent.type === 'tool_started' && streamEvent.tool_name) {
      const step = makeActiveStep(streamEvent.tool_name)
      setSteps((current) => [...current.filter((item) => item.status === 'completed'), step])
      setLiveNarration(step.detail)
      return
    }

    if (streamEvent.type === 'tool_completed' && streamEvent.tool_name) {
      const completedStep = makeCompletedStep(streamEvent.tool_name)
      setSteps((current) => {
        const withoutActive = current.filter((item) => item.status === 'completed')
        return [...withoutActive, completedStep]
      })
      setLiveNarration(completedStep.detail)

      setItinerary((current) => {
        const next: ItineraryDraft = current ?? {
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

      const payload = streamEvent.payload as { itinerary?: ItineraryDraft | null } | undefined
      if (payload?.itinerary) {
        setItinerary(payload.itinerary)
      }

      setLiveNarration('')
    }
  }

  const activeStep = [...steps].reverse().find((step) => step.status === 'active') ?? null
  const completedSteps = steps.filter((step) => step.status === 'completed').slice().reverse()

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <AnimatePresence mode="wait">
        {!workspaceMode ? (
          <motion.section
            key="landing"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -18 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
            className="mx-auto flex min-h-screen max-w-6xl items-center justify-center px-5 py-10"
          >
            <div className="w-full max-w-4xl rounded-[40px] border border-white/10 bg-[linear-gradient(180deg,rgba(16,27,43,0.9),rgba(8,16,27,0.92))] p-8 shadow-[0_30px_120px_rgba(3,8,16,0.45)] lg:p-12">
              <div className="mx-auto max-w-3xl text-center">
                <h1 className="text-6xl font-semibold tracking-[-0.07em] text-white lg:text-8xl">Vela</h1>
                <p className="mx-auto mt-6 max-w-2xl text-xl leading-9 text-slate-300 lg:text-2xl">
                  A warmer way to turn a travel idea into a trip that feels thoughtful, useful, and deeply your own.
                </p>
              </div>

              <div className="mx-auto mt-10 max-w-3xl rounded-[32px] border border-white/10 bg-slate-950/70 p-5 lg:p-6">
                <form className="space-y-4" onSubmit={handleSubmit}>
                  <textarea
                    className="min-h-40 w-full rounded-[24px] border border-slate-800 bg-slate-950 px-5 py-4 text-base text-slate-100 outline-none"
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    placeholder="Where do you want to go, what kind of trip do you want, and what should Vela optimize for?"
                  />
                  <div className="flex items-center justify-end">
                    <button
                      className="rounded-[20px] bg-emerald-400 px-6 py-3 font-medium text-slate-950 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
                      disabled={isStreaming || !input.trim()}
                      type="submit"
                    >
                      Start planning
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </motion.section>
        ) : (
          <motion.section
            key="workspace"
            initial={{ opacity: 0, scale: 0.985 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
            className="mx-auto grid min-h-screen max-w-[1600px] gap-4 p-4 lg:grid-cols-[380px_minmax(0,1fr)]"
          >
            <section className="flex min-h-[calc(100vh-2rem)] flex-col rounded-[32px] border border-slate-800 bg-slate-900/85">
              <div className="border-b border-slate-800 px-5 py-5">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Vela</p>
                    <h2 className="mt-2 text-xl font-semibold tracking-[-0.04em] text-white">Planning in motion</h2>
                  </div>
                  <div className="rounded-full border border-slate-800 bg-slate-950 px-3 py-1 text-xs text-slate-400">
                    {sessionId ? 'session live' : 'new session'}
                  </div>
                </div>
              </div>

              <div className="border-b border-slate-800 px-5 py-5">
                <div className="rounded-[24px] border border-slate-800 bg-slate-950 px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Agent</p>
                      <p className="mt-1 text-sm font-medium text-white">
                        {activeStep ? activeStep.title : isStreaming ? 'Thinking' : 'Ready'}
                      </p>
                    </div>
                    <span
                      className={`rounded-full px-3 py-1 text-[11px] uppercase tracking-[0.2em] ${
                        isStreaming ? 'bg-emerald-400/15 text-emerald-200 agent-shimmer' : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {isStreaming ? 'Live' : 'Idle'}
                    </span>
                  </div>

                  <div className="mt-4 min-h-20 rounded-[18px] border border-slate-800 bg-slate-900/70 px-3 py-3 text-sm leading-6 text-slate-200">
                    <TypewriterText text={liveNarration || activeStep?.detail || 'Waiting for the next trip request.'} animate={isStreaming} />
                  </div>

                  <div className="mt-4">
                    <button
                      className="text-xs uppercase tracking-[0.22em] text-slate-400"
                      onClick={() => setShowHistory((current) => !current)}
                      type="button"
                    >
                      {showHistory ? 'Hide' : 'Show'} completed steps ({completedSteps.length})
                    </button>

                    {showHistory ? (
                      <div className="mt-3 space-y-2">
                        {completedSteps.length ? (
                          completedSteps.map((step) => (
                            <div key={step.id} className="rounded-2xl border border-slate-800 px-3 py-3 text-sm">
                              <div className="font-medium text-slate-100">{step.title}</div>
                              <div className="mt-1 text-slate-400">{step.detail}</div>
                            </div>
                          ))
                        ) : (
                          <div className="text-sm text-slate-500">Completed steps will appear here.</div>
                        )}
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>

              <div className="flex-1 overflow-auto px-5 py-5">
                <div className="space-y-3">
                  {messages.map((message, index) => (
                    <article
                      key={`${message.role}-${index}`}
                      className={`rounded-[24px] px-4 py-4 text-sm leading-7 ${
                        message.role === 'user'
                          ? 'ml-6 bg-emerald-500/18 text-emerald-50'
                          : 'mr-4 border border-slate-700 bg-slate-950 text-slate-200'
                      }`}
                    >
                      <div className="mb-2 text-[11px] uppercase tracking-[0.24em] text-slate-400">
                        {message.role === 'user' ? 'You' : 'Vela'}
                      </div>
                      {message.role === 'assistant' ? (
                        <TypewriterText text={message.text} animate={index === messages.length - 1 && !isStreaming} />
                      ) : (
                        message.text
                      )}
                    </article>
                  ))}
                  <div ref={transcriptEndRef} />
                </div>
              </div>

              <div className="border-t border-slate-800 bg-slate-900/95 px-5 py-5">
                <form className="space-y-3" onSubmit={handleSubmit}>
                  <textarea
                    className="min-h-28 w-full rounded-[24px] border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none"
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    placeholder="Refine the trip, change the pace, or add a new preference..."
                  />
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs text-slate-500">Keep the conversation moving without losing the plan.</p>
                    <button
                      className="rounded-[18px] bg-emerald-400 px-5 py-3 font-medium text-slate-950 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
                      disabled={isStreaming || !input.trim()}
                      type="submit"
                    >
                      {isStreaming ? 'Planning...' : 'Send'}
                    </button>
                  </div>
                </form>

                {error ? (
                  <div className="mt-4 rounded-2xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                    {error}
                  </div>
                ) : null}
              </div>
            </section>

            <section className="rounded-[32px] border border-slate-800 bg-slate-900/85 p-6">
              <div className="rounded-[28px] border border-slate-800 bg-slate-950/90 p-6">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Live Itinerary</p>
                    <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-white">
                      {itinerary?.destination ? `${itinerary.destination} / ${itinerary.trip_length_days} days` : 'Your trip canvas'}
                    </h2>
                    <p className="mt-2 text-sm text-slate-400">
                      {itinerary ? itinerary.summary || 'Trip structure is updating live.' : 'The plan will open here as Vela gathers weather, stays, food, and route logic.'}
                    </p>
                  </div>
                  <div className="rounded-[22px] border border-slate-800 bg-slate-900 px-4 py-3 text-sm text-slate-300">
                    {itinerary?.month || 'Awaiting dates'}
                  </div>
                </div>

                {!itinerary ? (
                  <div className="mt-6 rounded-[24px] border border-dashed border-slate-800 px-6 py-16 text-center text-sm text-slate-500">
                    The itinerary canvas will expand in real time once the agent starts planning.
                  </div>
                ) : (
                  <div className="mt-6 space-y-5">
                    <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
                      <div className="rounded-[24px] border border-slate-800 bg-slate-900/70 p-5">
                        <div className="text-xs uppercase tracking-[0.22em] text-slate-400">Weather Snapshot</div>
                        {itinerary.weather ? (
                          <div className="mt-4 space-y-3">
                            <div className="text-lg font-semibold text-white">
                              {itinerary.weather.destination} {itinerary.weather.avg_temp_c !== null ? `· ${itinerary.weather.avg_temp_c}C` : ''}
                            </div>
                            <p className="text-sm leading-6 text-slate-300">{itinerary.weather.conditions_summary}</p>
                            <div className="flex flex-wrap gap-2">
                              {itinerary.weather.packing_notes.map((note) => (
                                <span
                                  key={note}
                                  className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs text-slate-300"
                                >
                                  {note}
                                </span>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <p className="mt-4 text-sm text-slate-500">Waiting for live weather.</p>
                        )}
                      </div>

                      <div className="grid gap-4 sm:grid-cols-3 xl:grid-cols-1">
                        <SummaryCard
                          title="Stay"
                          lines={itinerary.hotels.map((hotel) => `${hotel.name} · ${hotel.neighborhood}`)}
                        />
                        <SummaryCard
                          title="Dining"
                          lines={itinerary.restaurants.map((restaurant) => `${restaurant.name} · ${restaurant.neighborhood}`)}
                        />
                        <SummaryCard
                          title="Experiences"
                          lines={itinerary.experiences.map((experience) => `${experience.name} · ${experience.neighborhood}`)}
                        />
                      </div>
                    </div>

                    <div className="rounded-[24px] border border-slate-800 bg-slate-900/70 p-5">
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <div className="text-xs uppercase tracking-[0.22em] text-slate-400">Day by Day</div>
                          <div className="mt-2 text-xl font-semibold text-white">Structured itinerary</div>
                        </div>
                        <div className="rounded-full border border-slate-800 bg-slate-950 px-3 py-1 text-xs uppercase tracking-[0.18em] text-slate-400">
                          live draft
                        </div>
                      </div>

                      <div className="mt-5 grid gap-4 xl:grid-cols-2">
                        {itinerary.days.map((day) => (
                          <article key={day.day_number} className="rounded-[22px] border border-slate-800 bg-slate-950 p-4">
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <h3 className="text-lg font-semibold text-white">Day {day.day_number}</h3>
                                <p className="mt-1 text-sm text-slate-400">{day.summary}</p>
                              </div>
                              <span className="text-xs uppercase tracking-[0.18em] text-emerald-300">{day.theme}</span>
                            </div>

                            <div className="mt-4 space-y-3">
                              {day.items.map((item, index) => (
                                <div key={`${item.title}-${index}`} className="rounded-[18px] border border-slate-800 px-3 py-3">
                                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">{item.time_label}</div>
                                  <div className="mt-1 text-sm font-medium text-slate-100">{item.title}</div>
                                  <div className="mt-1 text-sm leading-6 text-slate-400">{item.description}</div>
                                </div>
                              ))}
                            </div>
                          </article>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </section>
          </motion.section>
        )}
      </AnimatePresence>
    </main>
  )
}

function SummaryCard({ title, lines }: { title: string; lines: string[] }) {
  return (
    <div className="rounded-[22px] border border-slate-800 bg-slate-900/70 p-4">
      <div className="text-xs uppercase tracking-[0.22em] text-slate-400">{title}</div>
      <div className="mt-3 space-y-2">
        {lines.length ? (
          lines.map((line) => (
            <div key={line} className="rounded-[16px] border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-200">
              {line}
            </div>
          ))
        ) : (
          <div className="text-sm text-slate-500">Waiting for {title.toLowerCase()}.</div>
        )}
      </div>
    </div>
  )
}

function TypewriterText({ text, animate }: { text: string; animate: boolean }) {
  const [visibleText, setVisibleText] = useState(text)

  useEffect(() => {
    if (!animate) {
      setVisibleText(text)
      return
    }

    setVisibleText('')
    let index = 0
    const timer = window.setInterval(() => {
      index += 2
      setVisibleText(text.slice(0, index))
      if (index >= text.length) {
        window.clearInterval(timer)
      }
    }, 12)

    return () => window.clearInterval(timer)
  }, [text, animate])

  return <span className={animate ? 'agent-shimmer-text' : ''}>{visibleText}</span>
}

function makeActiveStep(toolName: string): AgentStep {
  const detailByTool: Record<string, string> = {
    get_weather: 'Checking live destination weather and turning it into practical travel context.',
    get_hotels: 'Screening stay options that fit the trip style, neighborhood, and budget.',
    get_restaurants: 'Curating dining options that match the traveler profile and local rhythm.',
    get_experiences: 'Collecting experiences that add texture without breaking the pace.',
    get_daily_structure: 'Organizing everything into a coherent day-by-day route.',
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
    get_weather: 'Live weather is now grounding the plan.',
    get_hotels: 'Stay options have been added to the itinerary canvas.',
    get_restaurants: 'Dining options are now part of the plan.',
    get_experiences: 'Experience options are ready and mapped into the trip.',
    get_daily_structure: 'The itinerary has been organized into labeled days.',
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
    get_weather: 'Checking weather',
    get_hotels: 'Finding stays',
    get_restaurants: 'Curating dining',
    get_experiences: 'Finding experiences',
    get_daily_structure: 'Building the itinerary',
  }

  return names[toolName] ?? toolName
}

function parseSseChunk(chunk: string): { event: string; data: unknown } | null {
  const lines = chunk.split('\n')
  const eventLine = lines.find((line) => line.startsWith('event: '))
  const dataLine = lines.find((line) => line.startsWith('data: '))
  if (!eventLine || !dataLine) return null

  return {
    event: eventLine.slice(7).trim(),
    data: JSON.parse(dataLine.slice(6)),
  }
}

export default App
