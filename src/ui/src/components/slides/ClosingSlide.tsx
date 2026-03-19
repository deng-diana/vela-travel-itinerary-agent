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
        {/* Destination headline */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7 }}
          className="flex flex-col gap-2"
        >
          <p
            style={{
              fontFamily: 'var(--font-editorial)',
              color: 'var(--story-text)',
              fontSize: 'clamp(1.8rem, 4vw, 2.8rem)',
              fontWeight: 400,
              lineHeight: 1.1,
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
                fontSize: '0.95rem',
                marginTop: '4px',
              }}
            >
              {data.trip_tone}
            </p>
          )}
        </motion.div>

        {/* Two-column layout: moments + cultural notes */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
          {/* Key moments */}
          {data.key_moments.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.2, duration: 0.7 }}
              className="flex flex-col gap-4"
            >
              <span
                className="text-[10px] uppercase tracking-widest"
                style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent2)', letterSpacing: '0.18em' }}
              >
                Moments to Look Forward To
              </span>
              <div className="flex flex-col gap-3">
                {data.key_moments.map((moment, i) => (
                  <motion.div
                    key={moment}
                    initial={{ opacity: 0, x: -12 }}
                    animate={inView ? { opacity: 1, x: 0 } : {}}
                    transition={{ delay: 0.3 + i * 0.1, duration: 0.5 }}
                    className="flex gap-3"
                  >
                    <span
                      className="flex-shrink-0 mt-[2px]"
                      style={{ color: 'var(--story-accent)', fontSize: '0.75rem' }}
                    >
                      —
                    </span>
                    <p
                      style={{
                        fontFamily: "'Lora', Georgia, serif",
                        color: 'var(--story-text)',
                        fontSize: '0.9rem',
                        fontStyle: 'italic',
                        lineHeight: 1.6,
                      }}
                    >
                      {moment}
                    </p>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Cultural notes */}
          {data.cultural_notes.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.5, duration: 0.7 }}
              className="flex flex-col gap-4"
            >
              <span
                className="text-[10px] uppercase tracking-widest"
                style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent2)', letterSpacing: '0.18em' }}
              >
                Cultural Notes
              </span>
              <div className="flex flex-col gap-3">
                {data.cultural_notes.map((note, i) => (
                  <motion.div
                    key={note}
                    initial={{ opacity: 0 }}
                    animate={inView ? { opacity: 1 } : {}}
                    transition={{ delay: 0.6 + i * 0.08, duration: 0.4 }}
                    className="flex gap-3"
                  >
                    <span
                      className="flex-shrink-0 mt-[3px]"
                      style={{ color: 'var(--story-accent2)', fontSize: '0.55rem' }}
                    >
                      ✦
                    </span>
                    <p
                      style={{
                        color: 'var(--story-text-muted)',
                        fontSize: '0.8rem',
                        lineHeight: 1.6,
                      }}
                    >
                      {note}
                    </p>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </div>

        {/* Summary */}
        {data.summary && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ delay: 0.9, duration: 0.6 }}
            className="border-t pt-6"
            style={{ borderColor: 'rgba(245,240,232,0.08)' }}
          >
            <p
              className="max-w-prose"
              style={{
                color: 'var(--story-text-muted)',
                fontSize: '0.85rem',
                lineHeight: 1.7,
                fontStyle: 'italic',
                fontFamily: "'Lora', Georgia, serif",
              }}
            >
              {data.summary.length > 220 ? data.summary.slice(0, 220) + '…' : data.summary}
            </p>
          </motion.div>
        )}
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
