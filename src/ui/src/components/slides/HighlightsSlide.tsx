/**
 * HighlightsSlide — "Where to Stay"
 *
 * 2 hotel cards in a staggered layout with dates, map links,
 * and recommendation text below each card.
 */
import { useRef } from 'react'
import { motion, useInView } from 'motion/react'
import type { HighlightSlideData, HotelOption } from '../../lib/story'

interface Props { data: HighlightSlideData }

function buildStayDates(
  index: number,
  totalHotels: number,
  tripDays: number,
  month: string,
): string {
  if (totalHotels <= 1) {
    return `${tripDays} nights · ${month}`
  }
  // Split stay across hotels
  const firstHalf = Math.ceil(tripDays / 2)
  if (index === 0) {
    return `Night 1–${firstHalf} · ${month}`
  }
  return `Night ${firstHalf + 1}–${tripDays} · ${month}`
}

export function HighlightsSlide({ data }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-10% 0px' })

  if (data.hotels.length === 0) return null

  return (
    <section
      ref={ref}
      className="story-slide relative flex flex-col justify-center overflow-hidden"
      style={{ background: 'var(--story-bg)' }}
    >
      <div className="relative z-10 mx-auto w-full max-w-5xl px-10 flex flex-col gap-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
        >
          <span
            className="text-xs uppercase tracking-widest"
            style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent2)', letterSpacing: '0.18em' }}
          >
            Accommodation
          </span>
          <h2
            style={{
              fontFamily: 'var(--font-editorial)',
              color: 'var(--story-text)',
              fontSize: 'clamp(1.8rem, 3.5vw, 2.8rem)',
              fontWeight: 400,
              marginTop: '0.2rem',
            }}
          >
            Where to Stay
          </h2>
        </motion.div>

        {/* Hotel cards — compact, top-aligned */}
        <div
          className="flex items-start justify-center gap-6"
        >
          {data.hotels.slice(0, 2).map((hotel, i) => (
            <HotelCard
              key={hotel.name}
              hotel={hotel}
              index={i}
              inView={inView}
              stayDates={buildStayDates(i, Math.min(data.hotels.length, 2), data.trip_length_days, data.month)}
              isSelected={i === 0}
            />
          ))}
        </div>
      </div>
    </section>
  )
}

function HotelCard({
  hotel,
  index,
  inView,
  stayDates,
  isSelected = false,
}: {
  hotel: HotelOption
  index: number
  inView: boolean
  stayDates: string
  isSelected?: boolean
}) {
  const mapsUrl = hotel.maps_url ??
    `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(hotel.name + ' ' + hotel.neighborhood)}`

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ delay: 0.15 + index * 0.15, duration: 0.7 }}
      className="flex flex-col"
      style={{ width: '320px', maxWidth: '100%', flexShrink: 0 }}
    >
      {/* Stay dates badge */}
      <div
        className="mb-3 flex items-center gap-2"
      >
        <span
          className="text-xs uppercase tracking-wider"
          style={{
            fontFamily: 'var(--font-data)',
            color: 'var(--story-accent)',
            letterSpacing: '0.12em',
          }}
        >
          {stayDates}
        </span>
      </div>

      {/* Card */}
      <div
        className="flex flex-col overflow-hidden rounded-xl"
        style={{
          border: isSelected ? '1px solid rgba(196,255,77,0.35)' : '1px solid var(--story-border)',
          background: isSelected ? 'rgba(196,255,77,0.03)' : 'rgba(245,240,232,0.03)',
        }}
      >
        {/* Photo */}
        <div className="relative overflow-hidden" style={{ height: '180px', background: '#111' }}>
          {hotel.photo_url ? (
            <img
              src={hotel.photo_url}
              alt={hotel.name}
              className="h-full w-full object-cover"
              style={{ transition: 'transform 8s ease', transform: 'scale(1.06)', willChange: 'transform' }}
              onLoad={(e) => {
                setTimeout(() => { (e.target as HTMLImageElement).style.transform = 'scale(1.0)' }, 100)
              }}
            />
          ) : (
            <div
              className="flex h-full items-center justify-center"
              style={{ background: 'linear-gradient(135deg, rgba(196,113,92,0.15) 0%, transparent 100%)' }}
            >
              <span style={{ fontSize: '3rem', opacity: 0.2 }}>🏨</span>
            </div>
          )}
          {/* Recommended badge for selected hotel */}
          {isSelected && (
            <span
              className="absolute top-3 left-3 rounded-full px-2.5 py-0.5 text-[10px] uppercase tracking-wider"
              style={{
                background: 'rgba(196,255,77,0.9)',
                color: '#0A0A0A',
                fontFamily: 'var(--font-data)',
                fontWeight: 600,
                letterSpacing: '0.08em',
              }}
            >
              Recommended
            </span>
          )}
          {hotel.rating && (
            <span
              className="absolute top-3 right-3 rounded-full px-2 py-0.5 text-xs"
              style={{
                background: 'rgba(10,10,10,0.75)',
                color: 'var(--story-text)',
                fontFamily: 'var(--font-data)',
                backdropFilter: 'blur(4px)',
              }}
            >
              ★ {hotel.rating.toFixed(1)}
            </span>
          )}
        </div>

        {/* Hotel info */}
        <div className="flex flex-col gap-2 p-4">
          <h3
            style={{
              fontFamily: 'var(--font-editorial)',
              color: 'var(--story-text)',
              fontSize: '1.2rem',
              fontWeight: 400,
              lineHeight: 1.2,
            }}
          >
            {hotel.name}
          </h3>
          <span
            className="text-xs"
            style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent2)' }}
          >
            {hotel.neighborhood}
          </span>

          {/* Price + actions */}
          <div className="flex items-center justify-between pt-2 mt-1" style={{ borderTop: '1px solid rgba(245,240,232,0.06)' }}>
            <span style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text)', fontSize: '0.95rem', fontWeight: 600 }}>
              ~${hotel.nightly_rate_usd}
              <span className="text-xs font-normal" style={{ color: 'var(--story-text-muted)' }}>/night</span>
            </span>
            <div className="flex items-center gap-2">
              <a
                href={mapsUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-full px-2.5 py-1 text-xs transition-opacity hover:opacity-80"
                style={{
                  border: '1px solid rgba(245,240,232,0.15)',
                  color: 'var(--story-text-muted)',
                  fontFamily: 'var(--font-data)',
                  textDecoration: 'none',
                }}
              >
                Map ↗
              </a>
              <a
                href={hotel.affiliate_link}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-full px-3 py-1 text-xs transition-opacity hover:opacity-80"
                style={{
                  border: '1px solid var(--story-accent)',
                  color: 'var(--story-accent)',
                  fontFamily: 'var(--font-data)',
                  textDecoration: 'none',
                }}
              >
                Book →
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Recommendation text — below the card */}
      {hotel.why_selected && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ delay: 0.4 + index * 0.15, duration: 0.5 }}
          style={{
            fontFamily: "'Lora', Georgia, serif",
            color: 'var(--story-text-muted)',
            fontSize: '0.85rem',
            fontStyle: 'italic',
            lineHeight: 1.6,
            marginTop: '12px',
            paddingLeft: '2px',
          }}
        >
          {hotel.why_selected}
        </motion.p>
      )}
    </motion.div>
  )
}
