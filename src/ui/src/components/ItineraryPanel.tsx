import { AnimatePresence, motion } from 'motion/react'
import type { ItineraryDraft } from '../types'
import { WeatherStrip } from './WeatherStrip'
import { HotelGallery } from './HotelGallery'
import { VenueCard } from './VenueCard'
import { DayCard } from './DayCard'

function compactSummary(summary: string) {
  const normalized = summary.replace(/#+\s*/g, ' ').replace(/\*\*/g, '').replace(/\s+/g, ' ').trim()
  if (!normalized) return ''
  if (normalized.length <= 260) return normalized
  const slice = normalized.slice(0, 260)
  const cutoff = Math.max(slice.lastIndexOf('. '), slice.lastIndexOf('!'))
  return `${slice.slice(0, cutoff > 120 ? cutoff + 1 : 260).trim()}…`
}

export function ItineraryPanel({ itinerary }: { itinerary: ItineraryDraft | null }) {
  const hasDays = itinerary && itinerary.days.length > 0
  const hasVenues = itinerary && (itinerary.restaurants.length > 0 || itinerary.experiences.length > 0)

  return (
    <section className="rounded-[32px] border border-slate-800 bg-slate-900/85 p-6">
      <div className="rounded-[28px] border border-slate-800 bg-slate-950/90 p-6">
        {/* Header */}
        <div className="flex items-center justify-between gap-4">
          <div>
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
            {/* Weather */}
            <div className="rounded-[24px] border border-slate-800 bg-slate-900/70 p-5">
              <div className="text-xs uppercase tracking-[0.22em] text-slate-400">Weather Snapshot</div>
              <div className="mt-4">
                <WeatherStrip weather={itinerary.weather} />
              </div>
            </div>

            {/* Hotel Gallery - progressive rendering: appears as soon as hotels arrive */}
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

            {/* Venue staging area - appears before daily structure organizes them */}
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

            {/* Day-by-day itinerary - replaces venue staging once daily structure arrives */}
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
