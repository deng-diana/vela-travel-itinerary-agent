/**
 * VenueHighlightsSlide — shared component for both Dining and Experiences slides.
 * Shows up to 3 venue cards with staggered reveal animation.
 * Note: This component is deprecated. Dining and experiences are now shown in HighlightsSlide.
 */
import { useRef } from 'react'
import { motion, useInView } from 'motion/react'
// import type { DiningSlideData, ExperiencesSlideData } from '../../lib/story'

type DiningSlideData = any
type ExperiencesSlideData = any
type DiningVenue = any
type ExperienceVenue = any

interface DiningProps {
  mode: 'dining'
  data: DiningSlideData
}

interface ExperiencesProps {
  mode: 'experiences'
  data: ExperiencesSlideData
}

type Props = DiningProps | ExperiencesProps

export function VenueHighlightsSlide(props: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-10% 0px' })

  const isDining = props.mode === 'dining'
  const venues: Array<DiningVenue | ExperienceVenue> = isDining
    ? (props.data as DiningSlideData).restaurants
    : (props.data as ExperiencesSlideData).experiences

  const sectionLabel = isDining ? 'Where to Eat' : 'What to Do'
  const accent = isDining ? 'var(--story-accent)' : 'var(--story-accent2)'

  return (
    <section
      ref={ref}
      className="story-slide relative flex flex-col justify-center overflow-hidden"
      style={{ background: 'var(--story-bg)' }}
    >
      {/* Subtle diagonal texture */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: 'repeating-linear-gradient(-45deg, var(--story-text) 0px, var(--story-text) 1px, transparent 0px, transparent 50%)',
          backgroundSize: '24px 24px',
        }}
      />

      <div className="relative z-10 mx-auto w-full max-w-6xl px-10">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="mb-10 flex items-baseline gap-4"
        >
          <h2
            style={{
              fontFamily: 'var(--font-editorial)',
              color: 'var(--story-text)',
              fontSize: 'clamp(2rem, 4vw, 3rem)',
              fontWeight: 400,
            }}
          >
            {sectionLabel}
          </h2>
          <div className="h-px flex-1 opacity-20" style={{ background: 'var(--story-text)' }} />
        </motion.div>

        {/* Venue cards — 3-column grid */}
        <div className="grid gap-6 md:grid-cols-3">
          {venues.map((venue, i) => (
            <VenueCard
              key={venue.name}
              venue={venue}
              mode={props.mode}
              index={i}
              inView={inView}
              accent={accent}
            />
          ))}
        </div>
      </div>
    </section>
  )
}

function VenueCard({
  venue,
  mode,
  index,
  inView,
  accent,
}: {
  venue: DiningVenue | ExperienceVenue
  mode: 'dining' | 'experiences'
  index: number
  inView: boolean
  accent: string
}) {
  const isDining = mode === 'dining'
  const d = venue as DiningVenue
  const e = venue as ExperienceVenue

  const subLabel = isDining
    ? [d.cuisine, d.price_range].filter(Boolean).join(' · ')
    : [e.category, e.duration_hours ? `${e.duration_hours}h` : null].filter(Boolean).join(' · ')

  const ctaLink = isDining ? d.reservation_link : e.booking_link
  const ctaText = isDining ? 'Reserve' : 'Book'

  return (
    <motion.div
      initial={{ opacity: 0, y: 28 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ delay: 0.2 + index * 0.12, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      className="flex flex-col overflow-hidden rounded-lg"
      style={{ background: 'rgba(245,240,232,0.04)', border: '1px solid var(--story-border)' }}
    >
      {/* Photo or placeholder */}
      <div
        className="relative overflow-hidden"
        style={{ height: '180px', background: '#1a1a1a' }}
      >
        {venue.photo_url ? (
          <img
            src={venue.photo_url}
            alt={venue.name}
            className="h-full w-full object-cover"
            style={{ transition: 'transform 6s ease', willChange: 'transform' }}
            onMouseEnter={(e) => ((e.target as HTMLImageElement).style.transform = 'scale(1.05)')}
            onMouseLeave={(e) => ((e.target as HTMLImageElement).style.transform = 'scale(1)')}
          />
        ) : (
          <div
            className="flex h-full items-center justify-center"
            style={{
              background: `linear-gradient(135deg, rgba(${isDining ? '196,113,92' : '42,127,111'},0.2) 0%, transparent 100%)`,
            }}
          >
            <span style={{ fontSize: '2.5rem', opacity: 0.3 }}>{isDining ? '🍽' : '✦'}</span>
          </div>
        )}

        {/* Rating badge */}
        {venue.rating && (
          <span
            className="absolute top-2 right-2 rounded-full px-2 py-0.5 text-xs"
            style={{
              background: 'rgba(10,10,10,0.7)',
              color: 'var(--story-text)',
              fontFamily: 'var(--font-data)',
              backdropFilter: 'blur(4px)',
            }}
          >
            ★ {venue.rating.toFixed(1)}
          </span>
        )}
      </div>

      {/* Text content */}
      <div className="flex flex-1 flex-col gap-2 p-4">
        <p
          className="text-xs uppercase tracking-wider"
          style={{ fontFamily: 'var(--font-data)', color: accent }}
        >
          {subLabel}
        </p>

        <h3
          style={{
            fontFamily: 'var(--font-editorial)',
            color: 'var(--story-text)',
            fontSize: '1.25rem',
            fontWeight: 400,
            lineHeight: 1.2,
          }}
        >
          {venue.name}
        </h3>

        <p
          className="text-xs"
          style={{ color: 'var(--story-text-muted)', fontFamily: 'Inter, sans-serif' }}
        >
          {venue.neighborhood}
        </p>

        {isDining && d.must_order_dish && (
          <p
            className="text-xs mt-1"
            style={{ color: 'var(--story-text-muted)', fontStyle: 'italic' }}
          >
            Must order: {d.must_order_dish}
          </p>
        )}

        {!isDining && e.best_time && (
          <p
            className="text-xs mt-1"
            style={{
              color: 'var(--story-text-muted)',
              fontFamily: 'var(--font-data)',
              letterSpacing: '0.05em',
            }}
          >
            {e.best_time}
          </p>
        )}

        <div className="mt-auto pt-3">
          <a
            href={ctaLink}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block rounded-full px-4 py-1.5 text-xs transition-opacity hover:opacity-80"
            style={{
              border: `1px solid ${accent}`,
              color: accent,
              fontFamily: 'var(--font-data)',
              textDecoration: 'none',
              letterSpacing: '0.05em',
            }}
          >
            {ctaText} →
          </a>
        </div>
      </div>
    </motion.div>
  )
}
