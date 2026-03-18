import { useRef } from 'react'
import { motion, useInView } from 'motion/react'
import type { CoverSlideData } from '../../lib/story'

interface Props { data: CoverSlideData }

export function CoverSlide({ data }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-10% 0px' })

  const partyLabel = data.travel_party ? ` · ${capitalise(data.travel_party)}` : ''
  const dateLabel = `${data.trip_length_days} days · ${data.month}${partyLabel}`

  return (
    <section
      ref={ref}
      className="story-slide relative flex flex-col items-center justify-center overflow-hidden"
      style={{ background: 'var(--story-bg)' }}
    >
      {/* Subtle radial glow */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse 70% 60% at 50% 40%, rgba(196,113,92,0.08) 0%, transparent 70%)',
        }}
      />

      {/* Thin top accent line */}
      <motion.div
        initial={{ scaleX: 0 }}
        animate={inView ? { scaleX: 1 } : { scaleX: 0 }}
        transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
        style={{ originX: 0, background: 'var(--story-accent)' }}
        className="absolute top-0 left-0 right-0 h-[2px]"
      />

      <div className="relative z-10 flex flex-col items-center gap-6 px-8 text-center max-w-4xl">
        {/* Date / party label */}
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.3, duration: 0.6 }}
          style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent)', letterSpacing: '0.15em' }}
          className="text-xs uppercase tracking-widest"
        >
          {dateLabel}
        </motion.p>

        {/* Destination headline */}
        <motion.h1
          initial={{ opacity: 0, y: 32 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.5, duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          style={{
            fontFamily: 'var(--font-editorial)',
            color: 'var(--story-text)',
            fontSize: 'clamp(3.5rem, 10vw, 7.5rem)',
            lineHeight: 1.0,
            fontWeight: 400,
          }}
        >
          {data.destination}
        </motion.h1>

        {/* Trip tone */}
        {data.trip_tone && (
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.8, duration: 0.6 }}
            style={{
              fontFamily: 'var(--font-editorial)',
              color: 'var(--story-text-muted)',
              fontSize: 'clamp(1.1rem, 2.5vw, 1.6rem)',
              fontStyle: 'italic',
            }}
          >
            {data.trip_tone}
          </motion.p>
        )}

        {/* Interests pills */}
        {data.interests.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ delay: 1.1, duration: 0.6 }}
            className="flex flex-wrap justify-center gap-2 mt-2"
          >
            {data.interests.slice(0, 5).map((interest) => (
              <span
                key={interest}
                className="rounded-full border px-3 py-1 text-xs"
                style={{
                  borderColor: 'var(--story-border)',
                  color: 'var(--story-text-muted)',
                  fontFamily: 'var(--font-data)',
                  letterSpacing: '0.05em',
                }}
              >
                {interest}
              </span>
            ))}
          </motion.div>
        )}
      </div>

      {/* Bottom scroll hint */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={inView ? { opacity: 1 } : {}}
        transition={{ delay: 1.4, duration: 0.6 }}
        className="absolute bottom-8 flex flex-col items-center gap-2"
        style={{ color: 'var(--story-text-muted)' }}
      >
        <span className="text-xs" style={{ fontFamily: 'var(--font-data)', letterSpacing: '0.1em' }}>
          SCROLL TO EXPLORE
        </span>
        <motion.div
          animate={{ y: [0, 6, 0] }}
          transition={{ repeat: Infinity, duration: 1.6, ease: 'easeInOut' }}
          className="text-lg"
          style={{ color: 'var(--story-accent)' }}
        >
          ↓
        </motion.div>
      </motion.div>
    </section>
  )
}

function capitalise(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}
