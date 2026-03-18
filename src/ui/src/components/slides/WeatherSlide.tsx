import { useRef, useEffect, useState } from 'react'
import { motion, useInView } from 'motion/react'
import type { WeatherSlideData } from '../../lib/story'

interface Props { data: WeatherSlideData }

export function WeatherSlide({ data }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-10% 0px' })
  const [displayTemp, setDisplayTemp] = useState(0)

  // Count-up animation for temperature
  useEffect(() => {
    if (!inView || data.avg_temp_c == null) return
    const target = data.avg_temp_c
    const duration = 1400
    const start = Date.now()
    const tick = () => {
      const elapsed = Date.now() - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplayTemp(Math.round(eased * target))
      if (progress < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [inView, data.avg_temp_c])

  return (
    <section
      ref={ref}
      className="story-slide relative flex items-center justify-center overflow-hidden"
      style={{ background: 'var(--story-bg)' }}
    >
      {/* Ambient teal glow */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse 50% 70% at 20% 50%, rgba(42,127,111,0.12) 0%, transparent 60%)',
        }}
      />

      <div className="relative z-10 mx-auto grid max-w-5xl w-full gap-16 px-12 lg:grid-cols-[1fr_1fr] items-center">
        {/* Left: giant temperature */}
        <motion.div
          initial={{ opacity: 0, x: -24 }}
          animate={inView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="flex flex-col gap-4"
        >
          <p
            className="text-xs uppercase tracking-widest mb-2"
            style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent2)' }}
          >
            {data.destination} · {data.month}
          </p>

          {data.avg_temp_c != null ? (
            <div className="flex items-start gap-1">
              <span
                style={{
                  fontFamily: 'var(--font-data)',
                  color: 'var(--story-text)',
                  fontSize: 'clamp(5rem, 14vw, 9rem)',
                  lineHeight: 1,
                  fontWeight: 600,
                }}
              >
                {displayTemp}
              </span>
              <span
                style={{
                  fontFamily: 'var(--font-data)',
                  color: 'var(--story-accent2)',
                  fontSize: '2.5rem',
                  marginTop: '0.5rem',
                  fontWeight: 500,
                }}
              >
                °C
              </span>
            </div>
          ) : (
            <p
              style={{
                fontFamily: 'var(--font-editorial)',
                color: 'var(--story-text)',
                fontSize: '2rem',
                fontStyle: 'italic',
              }}
            >
              {data.conditions_summary}
            </p>
          )}

          <p
            style={{
              fontFamily: 'var(--font-editorial)',
              color: 'var(--story-text-muted)',
              fontSize: '1.2rem',
              fontStyle: 'italic',
              maxWidth: '28ch',
            }}
          >
            {data.conditions_summary}
          </p>

          {data.rainfall_mm != null && (
            <p
              style={{
                fontFamily: 'var(--font-data)',
                color: 'var(--story-text-muted)',
                fontSize: '0.8rem',
                letterSpacing: '0.05em',
              }}
            >
              {data.rainfall_mm}mm avg. rainfall
            </p>
          )}
        </motion.div>

        {/* Right: packing notes */}
        <motion.div
          initial={{ opacity: 0, x: 24 }}
          animate={inView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
          className="flex flex-col gap-3"
        >
          <p
            className="text-xs uppercase tracking-widest mb-3"
            style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text-muted)' }}
          >
            What to Pack
          </p>
          {data.packing_notes.map((note, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: 16 }}
              animate={inView ? { opacity: 1, x: 0 } : {}}
              transition={{ delay: 0.4 + i * 0.1, duration: 0.5 }}
              className="flex items-start gap-3"
            >
              <span style={{ color: 'var(--story-accent)', marginTop: '2px', flexShrink: 0 }}>–</span>
              <span
                style={{
                  color: 'var(--story-text)',
                  fontSize: '0.95rem',
                  lineHeight: 1.5,
                }}
              >
                {note}
              </span>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}
