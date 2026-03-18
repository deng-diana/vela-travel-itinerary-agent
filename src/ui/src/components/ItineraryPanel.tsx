import { useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import type { ItineraryDraft } from '../types'
import { API_BASE_URL } from '../types'
import { WeatherStrip } from './WeatherStrip'
import { HotelGallery } from './HotelGallery'
import { VenueCard } from './VenueCard'
import { DayCard } from './DayCard'

type ViewMode = 'canvas' | 'story'

interface Props {
  itinerary: ItineraryDraft | null
  viewMode: ViewMode
  onToggleView: (mode: ViewMode) => void
  canSwitchToStory: boolean
  isStreaming: boolean
  liveNarration: string
  steps: Array<{ id: string; title: string; detail: string; status: 'active' | 'completed' }>
}

function compactSummary(summary: string) {
  const normalized = summary.replace(/#+\s*/g, ' ').replace(/\*\*/g, '').replace(/\s+/g, ' ').trim()
  if (!normalized) return ''
  if (normalized.length <= 260) return normalized
  const slice = normalized.slice(0, 260)
  const cutoff = Math.max(slice.lastIndexOf('. '), slice.lastIndexOf('!'))
  return `${slice.slice(0, cutoff > 120 ? cutoff + 1 : 260).trim()}…`
}

export function ItineraryPanel({ itinerary, viewMode, onToggleView, canSwitchToStory, isStreaming, liveNarration, steps }: Props) {
  const hasDays = itinerary && itinerary.days.length > 0
  const hasVenues = itinerary && (itinerary.restaurants.length > 0 || itinerary.experiences.length > 0)
  const activeStep = [...steps].reverse().find((s) => s.status === 'active') ?? null
  const completedSteps = steps.filter((s) => s.status === 'completed')

  const [isPublishing, setIsPublishing] = useState(false)
  const [publishedUrl, setPublishedUrl] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  async function handlePublish() {
    if (!itinerary || isPublishing) return
    setIsPublishing(true)
    try {
      const response = await fetch(`${API_BASE_URL}/plans/publish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ itinerary }),
      })
      if (!response.ok) throw new Error('Publish failed')
      const data = await response.json() as { share_url: string }
      setPublishedUrl(data.share_url)
    } catch {
      // Silently fail — publish is non-critical
    } finally {
      setIsPublishing(false)
    }
  }

  async function handleCopyLink() {
    if (!publishedUrl) return
    await navigator.clipboard.writeText(publishedUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <section className="rounded-[32px] border border-slate-800 bg-slate-900/85 p-6">
      <div className="rounded-[28px] border border-slate-800 bg-slate-950/90 p-6">
        {/* Header row */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Live Itinerary</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-white">
              {itinerary?.destination
                ? `${itinerary.destination} / ${itinerary.trip_length_days} days`
                : 'Your trip canvas'}
            </h2>
            <p className="mt-2 text-sm leading-7 text-slate-400">
              {itinerary
                ? compactSummary(itinerary.summary) || 'Trip structure is updating live.'
                : 'The plan will open here as Vela gathers weather, stays, food, and route logic.'}
            </p>
          </div>

          <div className="flex flex-col items-end gap-2 flex-shrink-0">
            <div className="rounded-[22px] border border-slate-800 bg-slate-900 px-4 py-3 text-sm text-slate-300">
              {itinerary?.month || 'Awaiting dates'}
            </div>

            {/* Canvas / Story toggle */}
            {itinerary && (
              <div className="flex rounded-full border border-slate-800 bg-slate-900 overflow-hidden text-xs">
                <button
                  onClick={() => onToggleView('canvas')}
                  className="px-3 py-1.5 transition-colors"
                  style={{
                    background: viewMode === 'canvas' ? 'rgba(255,255,255,0.08)' : 'transparent',
                    color: viewMode === 'canvas' ? '#fff' : '#94a3b8',
                  }}
                >
                  Canvas
                </button>
                <button
                  onClick={() => onToggleView('story')}
                  disabled={!canSwitchToStory}
                  className="px-3 py-1.5 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  style={{
                    background: viewMode === 'story' ? 'rgba(196,113,92,0.2)' : 'transparent',
                    color: viewMode === 'story' ? '#C4715C' : '#94a3b8',
                  }}
                >
                  Story
                </button>
              </div>
            )}

            {/* Publish */}
            {canSwitchToStory && (
              <div className="flex items-center gap-2">
                {!publishedUrl ? (
                  <button
                    onClick={handlePublish}
                    disabled={isPublishing}
                    className="rounded-full px-3 py-1.5 text-xs transition-opacity hover:opacity-80 disabled:opacity-40"
                    style={{
                      border: '1px solid #C4715C',
                      color: '#C4715C',
                      background: 'transparent',
                    }}
                  >
                    {isPublishing ? 'Publishing…' : 'Publish →'}
                  </button>
                ) : (
                  <button
                    onClick={handleCopyLink}
                    className="rounded-full px-3 py-1.5 text-xs transition-opacity hover:opacity-80"
                    style={{
                      border: '1px solid #2A7F6F',
                      color: '#2A7F6F',
                      background: 'transparent',
                    }}
                  >
                    {copied ? 'Copied!' : 'Copy link'}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Streaming progress — shown during planning, right side */}
        <AnimatePresence>
          {isStreaming && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
              className="mt-5 rounded-[20px] border border-slate-800 bg-slate-900/60 px-5 py-4"
            >
              {/* Completed steps as a compact trail */}
              {completedSteps.length > 0 && (
                <div className="mb-3 flex flex-wrap gap-2">
                  {completedSteps.map((step) => (
                    <span
                      key={step.id}
                      className="flex items-center gap-1.5 rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-[11px] text-slate-400"
                    >
                      <span className="text-emerald-400">✓</span>
                      {step.title}
                    </span>
                  ))}
                </div>
              )}
              {/* Active step + narration */}
              <div className="flex items-start gap-3">
                <span className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-emerald-400 animate-pulse" />
                <p className="text-sm text-slate-300 leading-6">
                  {liveNarration || activeStep?.detail || 'Thinking…'}
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {!itinerary ? (
          <div className="mt-6 rounded-[24px] border border-dashed border-slate-800 px-6 py-16 text-center text-sm text-slate-500">
            The itinerary canvas will expand in real time once the agent starts planning.
          </div>
        ) : (
          <div className="mt-6 space-y-5">
            {/* Weather */}
            <div className="rounded-[24px] border border-slate-800 bg-slate-900/70 p-5">
              <div className="text-xs uppercase tracking-[0.22em] text-slate-400">Weather Snapshot</div>
              <div className="mt-4">
                <WeatherStrip weather={itinerary.weather} />
              </div>
            </div>

            {/* Hotel Gallery */}
            <AnimatePresence>
              {itinerary.hotels.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <HotelGallery hotels={itinerary.hotels} selectedHotel={itinerary.selected_hotel} />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Venue staging area */}
            <AnimatePresence>
              {hasVenues && !hasDays && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.3 }}
                  className="space-y-5"
                >
                  {itinerary.restaurants.length > 0 && (
                    <div className="rounded-[24px] border border-slate-800 bg-slate-900/70 p-5">
                      <div className="text-xs uppercase tracking-[0.22em] text-slate-400">Dining Options</div>
                      <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                        {itinerary.restaurants.map((r) => (
                          <VenueCard
                            key={r.id}
                            name={r.name}
                            subtitle={`${r.neighborhood} · ${r.cuisine}`}
                            photoName={r.photo_name}
                            attribution={r.photo_attribution}
                            href={r.maps_url || r.reservation_link}
                            ctaLabel="Open place"
                            tags={r.must_order_dish ? [`Try: ${r.must_order_dish}`] : undefined}
                          />
                        ))}
                      </div>
                    </div>
                  )}

                  {itinerary.experiences.length > 0 && (
                    <div className="rounded-[24px] border border-slate-800 bg-slate-900/70 p-5">
                      <div className="text-xs uppercase tracking-[0.22em] text-slate-400">Experience Options</div>
                      <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                        {itinerary.experiences.map((e) => (
                          <VenueCard
                            key={e.id}
                            name={e.name}
                            subtitle={`${e.neighborhood} · ${e.category}`}
                            photoName={e.photo_name}
                            attribution={e.photo_attribution}
                            href={e.maps_url || e.booking_link}
                            ctaLabel="View stop"
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Day-by-day itinerary */}
            <AnimatePresence>
              {hasDays && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35 }}
                  className="rounded-[24px] border border-slate-800 bg-slate-900/70 p-5"
                >
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
                      <DayCard key={day.day_number} day={day} itinerary={itinerary} />
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </div>
    </section>
  )
}
