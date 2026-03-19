import { useRef } from 'react'
import { motion, useInView } from 'motion/react'
import type { ClosingSlideData } from '../../lib/story'

interface Props { data: ClosingSlideData }

export function ClosingSlide({ data }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-10% 0px' })

  return (
    <section
      ref={ref}
      className="story-slide relative flex flex-col items-center justify-center overflow-hidden"
      style={{ background: 'var(--story-bg)' }}
    >
      {/* Subtle glow */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse 60% 50% at 50% 60%, rgba(196,113,92,0.07) 0%, transparent 70%)',
        }}
      />

      <div className="relative z-10 mx-auto max-w-3xl w-full px-10 flex flex-col gap-10">
        {/* Key moments */}
        {data.key_moments.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.7 }}
            className="flex flex-col gap-3"
          >
            <span
              className="text-xs uppercase tracking-widest"
              style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text-muted)' }}
            >
              Moments to Look Forward To
            </span>
            {data.key_moments.map((moment, i) => (
              <motion.p
                key={moment}
                initial={{ opacity: 0, x: -16 }}
                animate={inView ? { opacity: 1, x: 0 } : {}}
                transition={{ delay: 0.2 + i * 0.12, duration: 0.6 }}
                style={{
                  fontFamily: 'var(--font-editorial)',
                  color: 'var(--story-text)',
                  fontSize: 'clamp(1.1rem, 2.5vw, 1.5rem)',
                  fontStyle: 'italic',
                  lineHeight: 1.3,
                }}
              >
                <span style={{ color: 'var(--story-accent)', marginRight: '8px' }}>—</span>
                {moment}
              </motion.p>
            ))}
          </motion.div>
        )}

        {/* Cultural notes */}
        {data.cultural_notes.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ delay: 0.6, duration: 0.6 }}
            className="flex flex-col gap-2"
          >
            <span
              className="text-xs uppercase tracking-widest mb-1"
              style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text-muted)' }}
            >
              Cultural Notes
            </span>
            {data.cultural_notes.map((note) => (
              <p
                key={note}
                className="text-sm"
                style={{ color: 'var(--story-text-muted)', fontFamily: 'Inter, sans-serif', lineHeight: 1.5 }}
              >
                <span style={{ color: 'var(--story-accent2)', marginRight: '6px' }}>✦</span>
                {note}
              </p>
            ))}
          </motion.div>
        )}

        {/* Destination + CTA */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.9, duration: 0.7 }}
          className="flex flex-col items-start gap-4 border-t pt-8"
          style={{ borderColor: 'var(--story-border)' }}
        >
          <p
            style={{
              fontFamily: 'var(--font-editorial)',
              color: 'var(--story-text)',
              fontSize: 'clamp(2rem, 5vw, 3.5rem)',
              fontWeight: 400,
              lineHeight: 1,
            }}
          >
            {data.destination}
          </p>
          {data.trip_tone && (
            <p
              style={{
                fontFamily: 'var(--font-editorial)',
                color: 'var(--story-text-muted)',
                fontStyle: 'italic',
                fontSize: '1.1rem',
              }}
            >
              {data.trip_tone}
            </p>
          )}
          <p
            className="text-sm max-w-prose"
            style={{ color: 'var(--story-text-muted)', fontFamily: 'Inter, sans-serif', lineHeight: 1.6 }}
          >
            {data.summary.length > 200 ? data.summary.slice(0, 200) + '…' : data.summary}
          </p>
        </motion.div>
      </div>

      {/* Bottom accent line */}
      <motion.div
        initial={{ scaleX: 0 }}
        animate={inView ? { scaleX: 1 } : {}}
        transition={{ delay: 1.2, duration: 1.0, ease: [0.22, 1, 0.36, 1] }}
        style={{ originX: 0, background: 'var(--story-accent)' }}
        className="absolute bottom-0 left-0 right-0 h-[2px]"
      />
    </section>
  )
}
