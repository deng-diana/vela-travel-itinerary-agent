/**
 * HighlightsSlide — "What awaits you on this trip"
 *
 * Top: 2-3 recommended hotels with why selected + nearby highlights
 * Bottom: masonry grid of must-experience moments with big images on top
 */
import { useRef } from 'react'
import { motion, useInView } from 'motion/react'
import type { HighlightSlideData, HighlightMoment, HotelOption } from '../../lib/story'

interface Props { data: HighlightSlideData }

export function HighlightsSlide({ data }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-10% 0px' })

  return (
    <section
      ref={ref}
      className="story-slide relative flex flex-col justify-center overflow-hidden"
      style={{ background: 'var(--story-bg)' }}
    >
      <div className="relative z-10 mx-auto w-full max-w-6xl px-10 flex flex-col gap-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
        >
          <span
            className="text-xs uppercase tracking-widest"
            style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent2)' }}
          >
            What Awaits You
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
            The best of this trip
          </h2>
        </motion.div>

        {/* Hotel recommendations section */}
        {data.hotels.length > 0 && (
          <div className="flex flex-col gap-4">
            <span
              className="text-xs uppercase tracking-widest"
              style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent2)' }}
            >
              Where to Stay
            </span>

            {/* Grid of hotel cards: 1 col on mobile, 2-3 cols on desktop */}
            <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {data.hotels.map((hotel, i) => (
                <HotelCard
                  key={hotel.name}
                  hotel={hotel}
                  index={i}
                  inView={inView}
                />
              ))}
            </div>
          </div>
        )}

        {/* Must-experience masonry grid */}
        {data.moments.length > 0 && (
          <div className="flex flex-col gap-4">
            <span
              className="text-xs uppercase tracking-widest"
              style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text-muted)' }}
            >
              Must Experience
            </span>

            {/* 2-column masonry grid */}
            <div
              style={{
                columnCount: 2,
                columnGap: '12px',
              }}
            >
              {data.moments.map((moment, i) => (
                <MomentCard
                  key={moment.name}
                  moment={moment}
                  index={i}
                  inView={inView}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

function HotelCard({
  hotel,
  index,
  inView,
}: {
  hotel: HotelOption
  index: number
  inView: boolean
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ delay: 0.15 + index * 0.08, duration: 0.7 }}
      className="flex flex-col overflow-hidden rounded-xl"
      style={{ border: '1px solid var(--story-border)', background: 'rgba(245,240,232,0.03)' }}
    >
      {/* Photo */}
      <div className="relative overflow-hidden" style={{ height: '200px', background: '#111' }}>
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
      <div className="flex flex-col gap-3 p-4 flex-1">
        <div>
          <h3
            style={{
              fontFamily: 'var(--font-editorial)',
              color: 'var(--story-text)',
              fontSize: '1.2rem',
              fontWeight: 400,
              lineHeight: 1.2,
              marginBottom: '0.3rem',
            }}
          >
            {hotel.name}
          </h3>
          <span
            className="text-xs"
            style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent)' }}
          >
            {hotel.neighborhood}
          </span>
        </div>

        {hotel.short_description && (
          <p className="text-xs" style={{ color: 'var(--story-text-muted)', lineHeight: 1.5 }}>
            {hotel.short_description}
          </p>
        )}

        {hotel.why_selected && (
          <div style={{ fontSize: '0.85rem', color: 'var(--story-text)', lineHeight: 1.5, fontStyle: 'italic' }}>
            <span style={{ fontWeight: 500, display: 'block', marginBottom: '0.2rem' }}>Why selected:</span>
            <p style={{ margin: 0 }}>{hotel.why_selected}</p>
          </div>
        )}

        {hotel.nearby_highlights && hotel.nearby_highlights.length > 0 && (
          <div style={{ fontSize: '0.75rem', color: 'var(--story-text-muted)' }}>
            <span style={{ fontWeight: 500, display: 'block', marginBottom: '0.4rem', color: 'var(--story-text)' }}>
              Nearby Highlights
            </span>
            <ul style={{ margin: 0, paddingLeft: '1rem', lineHeight: 1.5 }}>
              {hotel.nearby_highlights.map((highlight, i) => (
                <li key={i}>{highlight}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-auto flex items-center justify-between pt-2">
          <span style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text)', fontSize: '0.95rem', fontWeight: 600 }}>
            ~${hotel.nightly_rate_usd}
            <span className="text-xs font-normal" style={{ color: 'var(--story-text-muted)' }}>/night</span>
          </span>
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
    </motion.div>
  )
}

function MomentCard({
  moment,
  index,
  inView,
}: {
  moment: HighlightMoment
  index: number
  inView: boolean
}) {
  const isDining = moment.kind === 'dining'
  const accentColor = isDining ? 'var(--story-accent)' : 'var(--story-accent2)'

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ delay: 0.2 + index * 0.08, duration: 0.55 }}
      style={{
        breakInside: 'avoid',
        marginBottom: '12px',
        display: 'inline-block',
        width: '100%',
        borderRadius: '10px',
        overflow: 'hidden',
        border: '1px solid var(--story-border)',
        background: 'rgba(245,240,232,0.025)',
      }}
    >
      {/* Image — tall for first 2, shorter for rest */}
      <div
        style={{
          height: index < 2 ? '160px' : '120px',
          background: isDining
            ? 'linear-gradient(135deg, rgba(196,113,92,0.18) 0%, transparent 100%)'
            : 'linear-gradient(135deg, rgba(42,127,111,0.18) 0%, transparent 100%)',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {moment.photo_url ? (
          <img
            src={moment.photo_url}
            alt={moment.name}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : (
          <div
            className="flex h-full items-center justify-center"
          >
            <span style={{ fontSize: '2rem', opacity: 0.25 }}>
              {isDining ? '🍽' : '✦'}
            </span>
          </div>
        )}

        {/* Kind badge */}
        <span
          style={{
            position: 'absolute',
            top: '8px',
            left: '8px',
            fontFamily: 'var(--font-data)',
            fontSize: '0.6rem',
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: '#0A0A0A',
            background: isDining ? 'var(--story-accent)' : 'var(--story-accent2)',
            padding: '2px 7px',
            borderRadius: '99px',
          }}
        >
          {isDining ? 'Dining' : 'Experience'}
        </span>
      </div>

      {/* Text */}
      <div style={{ padding: '10px 12px 12px', display: 'flex', flexDirection: 'column' }}>
        <div
          style={{
            fontFamily: 'var(--font-editorial)',
            color: 'var(--story-text)',
            fontSize: '1rem',
            fontWeight: 400,
            lineHeight: 1.25,
            marginBottom: '4px',
          }}
        >
          {moment.name}
        </div>
        <div
          style={{
            fontFamily: 'Inter, sans-serif',
            color: 'var(--story-text-muted)',
            fontSize: '0.72rem',
            lineHeight: 1.4,
            fontStyle: isDining ? 'italic' : 'normal',
          }}
        >
          {moment.caption}
        </div>
        <div
          style={{
            marginTop: '6px',
            fontFamily: 'var(--font-data)',
            color: accentColor,
            fontSize: '0.62rem',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            opacity: 0.8,
          }}
        >
          {moment.neighborhood}
        </div>

        {/* Booking CTA */}
        <a
          href={
            moment.booking_link ??
            `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
              [moment.name, moment.neighborhood].filter(Boolean).join(' ')
            )}`
          }
          target="_blank"
          rel="noopener noreferrer"
          className="transition-opacity hover:opacity-75"
          style={{
            marginTop: '8px',
            alignSelf: 'flex-start',
            display: 'inline-block',
            fontFamily: 'var(--font-data)',
            fontSize: '0.75rem',
            letterSpacing: '0.04em',
            color: 'var(--color-accent)',
            border: '1px solid var(--color-accent)',
            borderRadius: '9999px',
            padding: '3px 10px',
            textDecoration: 'none',
            whiteSpace: 'nowrap',
          }}
        >
          {isDining ? 'Reserve \u2192' : 'Book \u2192'}
        </a>
      </div>
    </motion.div>
  )
}
