import { useState } from 'react'
import type { FormEvent } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import type { AgentStep, ChatMessage, ItineraryDraft, StreamEvent, WeatherSummary, HotelOption, RestaurantOption, ExperienceOption, DayPlan } from './types'
import { API_BASE_URL } from './types'
import { Landing } from './components/Landing'
import { ChatPanel } from './components/ChatPanel'
import { ItineraryPanel } from './components/ItineraryPanel'

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

      const payload = streamEvent.payload as
        | { itinerary?: ItineraryDraft | null; workspace_ready?: boolean }
        | undefined
      if (payload?.itinerary) setItinerary(payload.itinerary)
      if (payload?.workspace_ready) setWorkspaceMode(true)

      setLiveNarration('')
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
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
            className="mx-auto grid min-h-screen max-w-[1600px] gap-4 p-4 lg:grid-cols-[380px_minmax(0,1fr)]"
          >
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
            <ItineraryPanel itinerary={itinerary} />
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
  return { event: eventLine.slice(7).trim(), data: JSON.parse(dataLine.slice(6)) }
}

export default App
