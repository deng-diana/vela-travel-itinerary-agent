/**
 * DaySlide — comprehensive per-day plan.
 *
 * Layout:
 *   Header: Day N · Theme · Summary
 *   Hotel bar (if hotel item present)
 *   2-column grid: Activities (left) | Meals (right)
 *   Evening: full-width
 *   Footer: practical tips + estimated cost
 */
import { useRef } from 'react'
import { motion, useInView } from 'motion/react'
import type { DaySlideData } from '../../lib/story'
import type { DayItem } from '../../types'

interface Props { data: DaySlideData }

type TimeGroup = 'hotel' | 'morning' | 'lunch' | 'afternoon' | 'dinner' | 'evening'

function classifyItem(item: DayItem): TimeGroup {
  if (item.kind === 'hotel') return 'hotel'
  const t = item.time_label.toLowerCase()
  if (t === 'lunch') return 'lunch'
  if (t === 'dinner') return 'dinner'
  if (t === 'afternoon') return 'afternoon'
  if (t === 'evening' || t === 'night') return 'evening'
  return 'morning'
}

export function DaySlide({ data }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-10% 0px' })

  const hotel = data.items.find((i) => i.kind === 'hotel')
  const morning = data.items.filter((i) => classifyItem(i) === 'morning')
  const afternoon = data.items.filter((i) => classifyItem(i) === 'afternoon')
  const lunch = data.items.find((i) => classifyItem(i) === 'lunch')
  const dinner = data.items.find((i) => classifyItem(i) === 'dinner')
  const evening = data.items.filter((i) => classifyItem(i) === 'evening')

  return (
    <section
      ref={ref}
      className="story-slide relative flex flex-col justify-center overflow-hidden"
      style={{ background: 'var(--story-bg)' }}
    >
      {/* Faint day watermark */}
      <div
        className="pointer-events-none absolute right-6 top-1/2 -translate-y-1/2 select-none"
        style={{
          fontFamily: 'var(--font-editorial)',
          fontSize: 'clamp(6rem, 14vw, 12rem)',
          color: 'rgba(245,240,232,0.022)',
          fontWeight: 600,
          lineHeight: 1,
          userSelect: 'none',
        }}
      >
        {data.day_number}
      </div>

      <div className="relative z-10 mx-auto w-full max-w-5xl px-10 flex flex-col gap-5">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.55 }}
        >
          <span
            className="text-xs uppercase tracking-widest"
            style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent)' }}
          >
            {data.day_number === 1 ? 'Arrival — ' : ''}Day {data.day_number}
            {data.part ? ' (continued)' : ''}
          </span>
          <h2
            style={{
              fontFamily: 'var(--font-editorial)',
              color: 'var(--story-text)',
              fontSize: 'clamp(1.5rem, 3vw, 2.4rem)',
              fontWeight: 400,
              marginTop: '0.15rem',
              lineHeight: 1.1,
            }}
          >
            {data.theme}
          </h2>
          {data.summary && (
            <p
              style={{
                fontFamily: 'var(--font-editorial)',
                color: 'var(--story-text-muted)',
                fontStyle: 'italic',
                fontSize: '0.9rem',
                marginTop: '0.2rem',
              }}
            >
              {data.summary}
            </p>
          )}
        </motion.div>

        {/* Hotel bar */}
        {hotel && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ delay: 0.15, duration: 0.5 }}
            className="flex items-center gap-3 rounded-lg px-4 py-2.5"
            style={{ background: 'rgba(196,113,92,0.07)', border: '1px solid rgba(196,113,92,0.18)' }}
          >
            <span style={{ fontSize: '1rem' }}>🏨</span>
            <div className="flex items-baseline gap-2 flex-wrap">
              <span
                style={{ fontFamily: 'var(--font-editorial)', color: 'var(--story-text)', fontSize: '1rem', fontWeight: 400 }}
              >
                {hotel.title}
              </span>
              {hotel.neighborhood && (
                <span className="text-xs" style={{ color: 'var(--story-text-muted)', fontFamily: 'Inter, sans-serif' }}>
                  · {hotel.neighborhood}
                </span>
              )}
              {hotel.transport_note && (
                <span className="text-xs" style={{ color: 'var(--story-text-muted)', fontFamily: 'var(--font-data)', fontSize: '0.7rem' }}>
                  · {hotel.transport_note}
                </span>
              )}
            </div>
          </motion.div>
        )}

        {/* Main 2-column grid: Activities | Meals */}
        <div className="grid gap-4 lg:grid-cols-2">
          {/* LEFT: Activities (Morning + Afternoon) */}
          <motion.div
            initial={{ opacity: 0, x: -16 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ delay: 0.2, duration: 0.6 }}
            className="flex flex-col gap-3"
          >
            {morning.map((item) => (
              <ActivityCard key={item.title} item={item} period="Morning" color="var(--story-accent2)" />
            ))}
            {afternoon.map((item) => (
              <ActivityCard key={item.title} item={item} period="Afternoon" color="var(--story-accent2)" />
            ))}
          </motion.div>

          {/* RIGHT: Meals (Lunch + Dinner) */}
          <motion.div
            initial={{ opacity: 0, x: 16 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ delay: 0.25, duration: 0.6 }}
            className="flex flex-col gap-3"
          >
            {lunch && <MealCard item={lunch} period="Lunch" />}
            {dinner && <MealCard item={dinner} period="Dinner" />}
          </motion.div>
        </div>

        {/* Evening — full width */}
        {evening.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.35, duration: 0.55 }}
            className="flex flex-col gap-2"
          >
            {evening.map((item) => (
              <EveningRow key={item.title} item={item} />
            ))}
          </motion.div>
        )}

        {/* Footer: tips + cost */}
        {(data.practical_tips.length > 0 || data.day_estimated_cost_usd) && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ delay: 0.45, duration: 0.5 }}
            className="flex flex-wrap items-start justify-between gap-3 border-t pt-3"
            style={{ borderColor: 'var(--story-border)' }}
          >
            {data.practical_tips.length > 0 && (
              <div className="flex flex-wrap gap-x-5 gap-y-1">
                {data.practical_tips.map((tip, i) => (
                  <p
                    key={i}
                    className="text-xs"
                    style={{ color: 'var(--story-text-muted)', fontFamily: 'Inter, sans-serif' }}
                  >
                    <span style={{ color: 'var(--story-accent)', marginRight: '5px' }}>✦</span>
                    {tip}
                  </p>
                ))}
              </div>
            )}
            {data.day_estimated_cost_usd && (
              <div className="flex flex-col items-end flex-shrink-0">
                <span className="text-xs uppercase tracking-wider" style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text-muted)' }}>
                  Est. per person
                </span>
                <span style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text)', fontSize: '1.1rem', fontWeight: 600 }}>
                  ~${data.day_estimated_cost_usd}
                </span>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ActivityCard({ item, period, color }: { item: DayItem; period: string; color: string }) {
  return (
    <div
      className="flex flex-col gap-1 rounded-lg p-3"
      style={{ border: '1px solid var(--story-border)', background: 'rgba(245,240,232,0.03)' }}
    >
      <div className="flex items-center gap-2">
        <span className="text-xs uppercase tracking-wider" style={{ fontFamily: 'var(--font-data)', color, minWidth: '72px' }}>
          {period}
        </span>
        {item.transport_note && (
          <span className="text-xs" style={{ color: 'var(--story-text-muted)', fontFamily: 'var(--font-data)', fontSize: '0.68rem' }}>
            · {item.transport_note}
          </span>
        )}
      </div>
      <span
        style={{ fontFamily: 'var(--font-editorial)', color: 'var(--story-text)', fontSize: '1.05rem', fontWeight: 400, lineHeight: 1.2 }}
      >
        {item.title}
      </span>
      {item.neighborhood && (
        <span className="text-xs" style={{ color: 'var(--story-text-muted)', fontFamily: 'Inter, sans-serif' }}>
          {item.neighborhood}
        </span>
      )}
    </div>
  )
}

function MealCard({ item, period }: { item: DayItem; period: string }) {
  return (
    <div
      className="flex flex-col gap-1 rounded-lg p-3"
      style={{ border: '1px solid rgba(196,113,92,0.2)', background: 'rgba(196,113,92,0.04)' }}
    >
      <div className="flex items-center gap-2">
        <span className="text-xs uppercase tracking-wider" style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent)', minWidth: '56px' }}>
          {period}
        </span>
        {item.transport_note && (
          <span className="text-xs" style={{ color: 'var(--story-text-muted)', fontFamily: 'var(--font-data)', fontSize: '0.68rem' }}>
            · {item.transport_note}
          </span>
        )}
      </div>
      <span
        style={{ fontFamily: 'var(--font-editorial)', color: 'var(--story-text)', fontSize: '1.05rem', fontWeight: 400, lineHeight: 1.2 }}
      >
        {item.booking_link ? (
          <a href={item.booking_link} target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'none' }} className="hover:underline">
            {item.title}
          </a>
        ) : item.title}
      </span>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5">
        {item.neighborhood && (
          <span className="text-xs" style={{ color: 'var(--story-text-muted)', fontFamily: 'Inter, sans-serif' }}>
            {item.neighborhood}
          </span>
        )}
        {/* Show must-order or tip from description */}
        {item.description && item.description.length < 60 && (
          <span className="text-xs" style={{ color: 'var(--story-text-muted)', fontStyle: 'italic', fontFamily: 'Inter, sans-serif' }}>
            {item.description}
          </span>
        )}
      </div>
    </div>
  )
}

function EveningRow({ item }: { item: DayItem }) {
  return (
    <div
      className="flex items-start gap-3 rounded-lg px-4 py-2.5"
      style={{ border: '1px solid var(--story-border)', background: 'rgba(42,127,111,0.05)' }}
    >
      <span className="text-xs uppercase tracking-wider flex-shrink-0 mt-0.5" style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent2)', minWidth: '60px' }}>
        Evening
      </span>
      <div className="flex flex-col gap-0.5">
        <span style={{ fontFamily: 'var(--font-editorial)', color: 'var(--story-text)', fontSize: '1rem', fontWeight: 400 }}>
          {item.title}
        </span>
        {(item.neighborhood || item.transport_note) && (
          <span className="text-xs" style={{ color: 'var(--story-text-muted)', fontFamily: 'Inter, sans-serif' }}>
            {[item.neighborhood, item.transport_note].filter(Boolean).join(' · ')}
          </span>
        )}
      </div>
    </div>
  )
}
