import { useState } from 'react'
import type { FormEvent } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

type ChatMessage = {
  role: 'user' | 'assistant'
  text: string
}

type StreamEvent = {
  type: string
  message?: string | null
  tool_name?: string | null
  payload?: unknown
}

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

type ExperienceOption = {
  id: string
  name: string
  category: string
  neighborhood: string
  booking_link: string
}

type DayItem = {
  time_label: string
  kind: string
  title: string
  neighborhood?: string | null
  description: string
  booking_link?: string | null
}

type DayPlan = {
  day_number: number
  theme: string
  summary: string
  items: DayItem[]
}

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

const initialPrompt =
  'I am going to Tokyo for 6 days in August. Mid-range budget, really into food and hidden gems. Travelling as a couple.'

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [input, setInput] = useState(initialPrompt)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [events, setEvents] = useState<StreamEvent[]>([])
  const [itinerary, setItinerary] = useState<ItineraryDraft | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || isStreaming) return

    setError(null)
    setIsStreaming(true)
    setMessages((current) => [...current, { role: 'user', text: trimmed }])
    setEvents([])

    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
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

          setEvents((current) => [...current, streamEvent])
          applyStreamEvent(streamEvent)
        }
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unknown stream error')
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
      setMessages((current) => [...current, { role: 'assistant', text: streamEvent.message ?? '' }])
      return
    }

    if (streamEvent.type === 'tool_completed' && streamEvent.tool_name) {
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
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto grid min-h-screen max-w-7xl gap-4 p-4 lg:grid-cols-[420px_minmax(0,1fr)]">
        <section className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
          <div className="mb-4">
            <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Conversation</p>
            <h1 className="mt-2 text-2xl font-semibold">Vela MVP Tester</h1>
            <p className="mt-2 text-sm text-slate-400">
              Session: {sessionId ?? 'new session'} {isStreaming ? '• streaming' : ''}
            </p>
          </div>

          <form className="space-y-3" onSubmit={handleSubmit}>
            <textarea
              className="min-h-36 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Describe the trip you want to plan..."
            />
            <button
              className="w-full rounded-2xl bg-emerald-400 px-4 py-3 font-medium text-slate-950 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
              disabled={isStreaming}
              type="submit"
            >
              {isStreaming ? 'Streaming...' : 'Send'}
            </button>
          </form>

          {error ? (
            <div className="mt-4 rounded-2xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {error}
            </div>
          ) : null}

          <div className="mt-6 space-y-3">
            {messages.map((message, index) => (
              <article
                key={`${message.role}-${index}`}
                className={`rounded-2xl px-4 py-3 text-sm leading-6 ${
                  message.role === 'user'
                    ? 'ml-8 bg-emerald-500/20 text-emerald-50'
                    : 'mr-6 border border-slate-700 bg-slate-950 text-slate-200'
                }`}
              >
                <div className="mb-2 text-[11px] uppercase tracking-[0.24em] text-slate-400">
                  {message.role}
                </div>
                {message.text}
              </article>
            ))}
          </div>
        </section>

        <section className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
          <div className="grid gap-4 xl:grid-cols-[340px_minmax(0,1fr)]">
            <aside className="space-y-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Event Stream</p>
                <div className="mt-3 max-h-[70vh] space-y-2 overflow-auto">
                  {events.map((event, index) => (
                    <div key={`${event.type}-${index}`} className="rounded-xl border border-slate-800 px-3 py-2 text-xs">
                      <div className="font-semibold text-emerald-300">{event.type}</div>
                      <div className="mt-1 text-slate-400">{event.tool_name ?? event.message ?? ''}</div>
                    </div>
                  ))}
                </div>
              </div>
            </aside>

            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Live Itinerary</p>
                {!itinerary ? (
                  <p className="mt-3 text-sm text-slate-400">Send a trip request to see live updates here.</p>
                ) : (
                  <div className="mt-4 space-y-4">
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="rounded-2xl border border-slate-800 p-4">
                        <div className="text-xs uppercase tracking-[0.22em] text-slate-400">Trip</div>
                        <div className="mt-2 text-lg font-semibold">
                          {itinerary.destination || 'Destination pending'} / {itinerary.trip_length_days || '?'} days
                        </div>
                        <div className="mt-1 text-sm text-slate-400">{itinerary.month}</div>
                      </div>
                      <div className="rounded-2xl border border-slate-800 p-4">
                        <div className="text-xs uppercase tracking-[0.22em] text-slate-400">Weather</div>
                        <div className="mt-2 text-sm text-slate-200">
                          {itinerary.weather
                            ? `${itinerary.weather.destination}: ${itinerary.weather.conditions_summary}`
                            : 'Waiting for weather'}
                        </div>
                      </div>
                    </div>

                    <div className="grid gap-4 md:grid-cols-3">
                      <SummaryCard
                        title="Hotels"
                        lines={itinerary.hotels.map((hotel) => `${hotel.name} · ${hotel.neighborhood}`)}
                      />
                      <SummaryCard
                        title="Restaurants"
                        lines={itinerary.restaurants.map((restaurant) => `${restaurant.name} · ${restaurant.neighborhood}`)}
                      />
                      <SummaryCard
                        title="Experiences"
                        lines={itinerary.experiences.map((experience) => `${experience.name} · ${experience.neighborhood}`)}
                      />
                    </div>

                    <div className="rounded-2xl border border-slate-800 p-4">
                      <div className="text-xs uppercase tracking-[0.22em] text-slate-400">Day by day</div>
                      <div className="mt-4 grid gap-4 lg:grid-cols-2">
                        {itinerary.days.map((day) => (
                          <article key={day.day_number} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                            <div className="flex items-center justify-between gap-3">
                              <h2 className="text-lg font-semibold">Day {day.day_number}</h2>
                              <span className="text-xs uppercase tracking-[0.18em] text-emerald-300">{day.theme}</span>
                            </div>
                            <p className="mt-2 text-sm text-slate-400">{day.summary}</p>
                            <div className="mt-4 space-y-2">
                              {day.items.map((item, index) => (
                                <div key={`${item.title}-${index}`} className="rounded-xl border border-slate-800 px-3 py-2 text-sm">
                                  <div className="font-medium text-slate-100">
                                    {item.time_label} · {item.title}
                                  </div>
                                  <div className="mt-1 text-slate-400">{item.description}</div>
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
            </div>
          </div>
        </section>
      </div>
    </main>
  )
}

function SummaryCard({ title, lines }: { title: string; lines: string[] }) {
  return (
    <div className="rounded-2xl border border-slate-800 p-4">
      <div className="text-xs uppercase tracking-[0.22em] text-slate-400">{title}</div>
      <div className="mt-3 space-y-2">
        {lines.length ? (
          lines.map((line) => (
            <div key={line} className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-200">
              {line}
            </div>
          ))
        ) : (
          <div className="text-sm text-slate-500">Waiting for {title.toLowerCase()}</div>
        )}
      </div>
    </div>
  )
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
