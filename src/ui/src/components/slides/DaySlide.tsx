/**
 * DaySlide — Elegant vertical timeline view of a day's itinerary.
 *
 * Layout:
 *   Header: Day N · theme · summary
 *   Hotel bar (arrival day)
 *   Timeline: each stop as a node with dot + spine + content card
 *   Footer: practical tips + daily cost estimate
 *
 * Each timeline node:
 *   - Time label (JetBrains Mono, coloured dot)
 *   - Transport note (italic, muted — connector from previous stop)
 *   - Place name (Lora, 1.25rem)
 *   - Neighbourhood tag
 *   - Description (Lora italic, 1rem = 16px)
 *   - Photo (right side, when available)
 *   - Booking CTA + advance-booking badge
 */
import { useRef } from 'react'
import { motion, useInView } from 'motion/react'
import type { DaySlideData, DaySlideItem } from '../../lib/story'

interface Props { data: DaySlideData }

// ---------------------------------------------------------------------------
// Time-slot configuration
// ---------------------------------------------------------------------------

type TimeGroup = 'hotel' | 'morning' | 'lunch' | 'afternoon' | 'dinner' | 'evening'

function classifyItem(item: DaySlideItem): TimeGroup {
  if (item.kind === 'hotel') return 'hotel'
  const t = item.time_label.toLowerCase()
  if (t === 'lunch') return 'lunch'
  if (t === 'dinner') return 'dinner'
  if (t === 'afternoon') return 'afternoon'
  if (t === 'evening' || t === 'night') return 'evening'
  return 'morning'
}

const TIME_COLORS: Record<TimeGroup, string> = {
  hotel: 'var(--story-accent)',
  morning: 'var(--story-accent2)',
  lunch: 'var(--story-accent)',
  afternoon: 'var(--story-accent2)',
  dinner: 'var(--story-accent)',
  evening: 'rgba(196,113,92,0.7)',
}

// ---------------------------------------------------------------------------
// Booking link helpers
// ---------------------------------------------------------------------------

function buildMapsUrl(title: string, neighborhood: string | null | undefined, destination: string): string {
  const query = [title, neighborhood, destination].filter(Boolean).join(' ')
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`
}

function getBookingCta(item: DaySlideItem, destination: string) {
  const href = item.booking_link ?? buildMapsUrl(item.title, item.neighborhood, destination)
  const isDirect = Boolean(item.booking_link)
  let label: string
  if (!isDirect) {
    label = 'View on Google Maps →'
  } else if (item.kind === 'restaurant') {
    label = 'Reserve a table →'
  } else {
    label = 'Book tickets →'
  }
  return { href, label, isDirect }
}

function needsAdvanceBookingBadge(item: DaySlideItem): boolean {
  return item.kind === 'experience' || (item.kind === 'restaurant' && item.time_label.toLowerCase() === 'dinner')
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function DaySlide({ data }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-8% 0px' })

  const hotel = data.items.find((i) => i.kind === 'hotel')
  const timelineItems = data.items.filter((i) => i.kind !== 'hotel')

  return (
    <section
      ref={ref}
      className="relative flex flex-col py-14"
      style={{ background: 'var(--story-bg)', minHeight: '100vh' }}
    >
      {/* Faint day-number watermark */}
      <div
        className="pointer-events-none absolute right-6 top-1/2 -translate-y-1/2 select-none"
        style={{
          fontFamily: 'var(--font-editorial)',
          fontSize: 'clamp(7rem, 16vw, 14rem)',
          color: 'rgba(245,240,232,0.018)',
          fontWeight: 600,
          lineHeight: 1,
        }}
      >
        {data.day_number}
      </div>

      <div className="relative z-10 mx-auto w-full max-w-4xl px-8 lg:px-12 flex flex-col gap-8">

        {/* ── Header ──────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        >
          <span
            className="text-xs uppercase tracking-widest"
            style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent)', letterSpacing: '0.18em' }}
          >
            {data.day_number === 1 ? 'Arrival · ' : ''}Day {data.day_number}
            {data.part ? ' (continued)' : ''}
          </span>

          <h2
            style={{
              fontFamily: 'var(--font-editorial)',
              color: 'var(--story-text)',
              fontSize: 'clamp(2rem, 4.5vw, 3rem)',
              fontWeight: 400,
              lineHeight: 1.1,
              marginTop: '0.2rem',
            }}
          >
            {data.theme}
          </h2>

          {data.summary && (
            <p
              style={{
                fontFamily: "'Lora', Georgia, serif",
                color: 'var(--story-text-muted)',
                fontStyle: 'italic',
                fontSize: '1rem',
                lineHeight: 1.7,
                marginTop: '0.5rem',
                maxWidth: '42rem',
              }}
            >
              {data.summary}
            </p>
          )}

          <div className="mt-5" style={{ height: '1px', background: 'var(--story-border)' }} />
        </motion.div>

        {/* ── Hotel bar ───────────────────────────────────────── */}
        {hotel && (
          <motion.div
            initial={{ opacity: 0, x: -12 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ delay: 0.15, duration: 0.5 }}
            className="flex items-start gap-3 rounded-xl px-4 py-3"
            style={{ background: 'rgba(196,113,92,0.07)', border: '1px solid rgba(196,113,92,0.2)' }}
          >
            <span style={{ fontSize: '1.1rem', marginTop: '2px' }}>🏨</span>
            <div className="flex-1 min-w-0">
              <span
                style={{
                  fontFamily: "'Lora', Georgia, serif",
                  color: 'var(--story-text)',
                  fontSize: '1.1rem',
                  fontWeight: 500,
                }}
              >
                {hotel.title}
              </span>
              {hotel.neighborhood && (
                <span style={{ color: 'var(--story-text-muted)', fontFamily: 'Inter, sans-serif', fontSize: '0.85rem', marginLeft: '8px' }}>
                  · {hotel.neighborhood}
                </span>
              )}
              {hotel.description && (
                <p style={{ color: 'var(--story-text-muted)', fontFamily: "'Lora', Georgia, serif", fontStyle: 'italic', fontSize: '0.9rem', marginTop: '3px', lineHeight: 1.5 }}>
                  {hotel.description}
                </p>
              )}
            </div>
            {hotel.booking_link && (
              <a
                href={hotel.booking_link}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-shrink-0 rounded-full px-3 py-1 text-xs transition-opacity hover:opacity-75"
                style={{
                  border: '1px solid var(--story-accent)',
                  color: 'var(--story-accent)',
                  fontFamily: 'var(--font-data)',
                  textDecoration: 'none',
                  whiteSpace: 'nowrap',
                }}
              >
                View hotel →
              </a>
            )}
          </motion.div>
        )}

        {/* ── Timeline ────────────────────────────────────────── */}
        <div className="flex flex-col">
          {timelineItems.map((item, i) => (
            <TimelineNode
              key={`${item.title}-${i}`}
              item={item}
              index={i}
              isLast={i === timelineItems.length - 1}
              inView={inView}
              destination={data.destination}
            />
          ))}
        </div>

        {/* ── Footer ──────────────────────────────────────────── */}
        {(data.practical_tips.length > 0 || data.day_estimated_cost_usd) && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ delay: 0.6, duration: 0.5 }}
            className="flex flex-wrap items-start justify-between gap-4 pt-5"
            style={{ borderTop: '1px solid var(--story-border)' }}
          >
            {data.practical_tips.length > 0 && (
              <div className="flex flex-wrap gap-x-5 gap-y-2">
                {data.practical_tips.map((tip, i) => (
                  <p
                    key={i}
                    style={{ color: 'var(--story-text-muted)', fontFamily: 'Inter, sans-serif', fontSize: '0.85rem', lineHeight: 1.6 }}
                  >
                    <span style={{ color: 'var(--story-accent)', marginRight: '6px' }}>✦</span>
                    {tip}
                  </p>
                ))}
              </div>
            )}
            {data.day_estimated_cost_usd && (
              <div className="flex flex-col items-end flex-shrink-0">
                <span
                  className="text-xs uppercase tracking-wider"
                  style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text-muted)' }}
                >
                  Est. per person
                </span>
                <span style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text)', fontSize: '1.25rem', fontWeight: 600 }}>
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
// Timeline node
// ---------------------------------------------------------------------------

function TimelineNode({
  item,
  index,
  isLast,
  inView,
  destination,
}: {
  item: DaySlideItem
  index: number
  isLast: boolean
  inView: boolean
  destination: string
}) {
  const group = classifyItem(item)
  const dotColor = TIME_COLORS[group]
  const cta = getBookingCta(item, destination)
  const showAdvanceBadge = needsAdvanceBookingBadge(item)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ delay: 0.2 + index * 0.09, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className="flex"
    >
      {/* ── Left: spine + dot ───────────────────────────────── */}
      <div className="flex flex-col items-center" style={{ width: '2.25rem', flexShrink: 0 }}>
        <div
          style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            background: dotColor,
            flexShrink: 0,
            marginTop: '0.4rem',
            boxShadow: `0 0 0 3px #0A0A0A, 0 0 0 4.5px ${dotColor}`,
          }}
        />
        {!isLast && (
          <div
            style={{
              width: '1px',
              flex: 1,
              background: 'var(--story-border)',
              marginTop: '6px',
              minHeight: '2.5rem',
            }}
          />
        )}
      </div>

      {/* ── Right: content ──────────────────────────────────── */}
      <div className="flex-1 pb-8" style={{ paddingLeft: '1.25rem' }}>
        {/* Time label */}
        <span
          className="text-xs uppercase"
          style={{
            fontFamily: 'var(--font-data)',
            color: dotColor,
            letterSpacing: '0.16em',
            lineHeight: 1,
          }}
        >
          {item.time_label}
        </span>

        {/* Transport note */}
        {item.transport_note && (
          <p
            style={{
              fontFamily: 'Inter, sans-serif',
              color: 'var(--story-text-muted)',
              fontSize: '0.85rem',
              fontStyle: 'italic',
              lineHeight: 1.5,
              marginTop: '5px',
              marginBottom: '4px',
            }}
          >
            {item.transport_note}
          </p>
        )}

        {/* Main card */}
        <div
          className="mt-2 flex rounded-2xl overflow-hidden"
          style={{
            border: '1px solid var(--story-border)',
            background: 'rgba(245,240,232,0.025)',
          }}
        >
          {/* Text */}
          <div className="flex-1 p-5 flex flex-col gap-2 min-w-0">
            <h3
              style={{
                fontFamily: "'Lora', Georgia, serif",
                color: 'var(--story-text)',
                fontSize: '1.25rem',
                fontWeight: 500,
                lineHeight: 1.25,
              }}
            >
              {item.booking_link ? (
                <a
                  href={item.booking_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: 'inherit', textDecoration: 'none' }}
                  className="hover:underline"
                >
                  {item.title}
                </a>
              ) : item.title}
            </h3>

            {item.neighborhood && (
              <span
                style={{
                  fontFamily: 'Inter, sans-serif',
                  color: 'var(--story-text-muted)',
                  fontSize: '0.8rem',
                  letterSpacing: '0.04em',
                }}
              >
                {item.neighborhood}
              </span>
            )}

            {item.description && item.description.length > 0 && (
              <p
                style={{
                  fontFamily: "'Lora', Georgia, serif",
                  color: 'rgba(245,240,232,0.62)',
                  fontSize: '1rem',
                  fontStyle: 'italic',
                  lineHeight: 1.7,
                  marginTop: '2px',
                }}
              >
                {item.description}
              </p>
            )}

            {/* Booking CTA */}
            <div className="flex flex-wrap items-center gap-3 mt-2">
              <a
                href={cta.href}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-full px-3 py-1 text-xs transition-opacity hover:opacity-75"
                style={{
                  border: `1px solid ${cta.isDirect ? dotColor : 'rgba(245,240,232,0.18)'}`,
                  color: cta.isDirect ? dotColor : 'var(--story-text-muted)',
                  fontFamily: 'var(--font-data)',
                  textDecoration: 'none',
                  letterSpacing: '0.04em',
                  whiteSpace: 'nowrap',
                }}
              >
                {cta.label}
              </a>

              {showAdvanceBadge && (
                <span
                  className="text-xs"
                  style={{
                    fontFamily: 'var(--font-data)',
                    color: 'var(--story-accent)',
                    letterSpacing: '0.04em',
                    opacity: 0.85,
                  }}
                >
                  ⚡ Book ahead
                </span>
              )}
            </div>
          </div>

          {/* Photo */}
          {item.photo_url && (
            <div
              style={{
                width: '160px',
                minHeight: '180px',
                flexShrink: 0,
                overflow: 'hidden',
                position: 'relative',
              }}
            >
              <img
                src={item.photo_url}
                alt={item.title}
                style={{
                  position: 'absolute',
                  inset: 0,
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                }}
              />
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
