import { useRef } from 'react'
import { motion, useInView } from 'motion/react'
import type { HotelSlideData } from '../../lib/story'

interface Props { data: HotelSlideData }

export function HotelSlide({ data }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-10% 0px' })

  return (
    <section
      ref={ref}
      className="story-slide relative flex items-end overflow-hidden"
      style={{ background: '#111' }}
    >
      {/* Hotel photo — Ken Burns zoom */}
      {data.photo_url ? (
        <motion.div
          initial={{ scale: 1.06 }}
          animate={inView ? { scale: 1.0 } : {}}
          transition={{ duration: 8, ease: 'linear' }}
          className="absolute inset-0"
          style={{
            backgroundImage: `url(${data.photo_url})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
          }}
        />
      ) : (
        <div
          className="absolute inset-0"
          style={{
            background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
          }}
        />
      )}

      {/* Gradient overlay — bottom-up */}
      <div
        className="absolute inset-0"
        style={{
          background: 'linear-gradient(to top, rgba(10,10,10,0.95) 0%, rgba(10,10,10,0.4) 50%, rgba(10,10,10,0.1) 100%)',
        }}
      />

      {/* Content — anchored to bottom */}
      <div className="relative z-10 w-full px-10 pb-16 pt-8 max-w-3xl">
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="text-xs uppercase tracking-widest mb-4"
          style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent)' }}
        >
          Your Base · {data.neighborhood}
        </motion.p>

        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.45, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          style={{
            fontFamily: 'var(--font-editorial)',
            color: 'var(--story-text)',
            fontSize: 'clamp(2rem, 5vw, 3.5rem)',
            lineHeight: 1.1,
            fontWeight: 400,
          }}
        >
          {data.name}
        </motion.h2>

        {data.short_description && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ delay: 0.65, duration: 0.6 }}
            style={{
              color: 'var(--story-text-muted)',
              fontSize: '0.95rem',
              maxWidth: '52ch',
              marginTop: '0.75rem',
              lineHeight: 1.6,
            }}
          >
            {data.short_description}
          </motion.p>
        )}

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.8, duration: 0.5 }}
          className="flex flex-wrap items-center gap-4 mt-6"
        >
          <span
            style={{
              fontFamily: 'var(--font-data)',
              color: 'var(--story-text)',
              fontSize: '1.1rem',
              fontWeight: 500,
            }}
          >
            ~${data.nightly_rate_usd}
            <span style={{ color: 'var(--story-text-muted)', fontSize: '0.8rem', marginLeft: '4px' }}>/night</span>
          </span>

          {data.rating && (
            <span
              style={{
                fontFamily: 'var(--font-data)',
                color: 'var(--story-text-muted)',
                fontSize: '0.85rem',
              }}
            >
              ★ {data.rating.toFixed(1)}
            </span>
          )}

          <a
            href={data.affiliate_link}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-auto rounded-full px-5 py-2 text-sm transition-all hover:opacity-90"
            style={{
              background: 'var(--story-accent)',
              color: 'var(--story-text)',
              fontFamily: 'var(--font-data)',
              letterSpacing: '0.05em',
              textDecoration: 'none',
            }}
          >
            Book this stay →
          </a>
        </motion.div>

        {/* Highlights */}
        {data.key_highlights.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ delay: 1.0, duration: 0.5 }}
            className="flex flex-wrap gap-2 mt-4"
          >
            {data.key_highlights.map((highlight) => (
              <span
                key={highlight}
                className="rounded-full border px-3 py-1 text-xs"
                style={{
                  borderColor: 'var(--story-border)',
                  color: 'var(--story-text-muted)',
                  fontFamily: 'Inter, sans-serif',
                }}
              >
                {highlight}
              </span>
            ))}
          </motion.div>
        )}
      </div>
    </section>
  )
}
