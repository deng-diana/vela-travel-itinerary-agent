import { useRef } from 'react'
import { motion, useInView } from 'motion/react'
import type { PackingSlideData } from '../../lib/story'

interface Props { data: PackingSlideData }

const CATEGORY_ICON: Record<string, string> = {
  'Clothing': '👕',
  'Documents & Money': '📄',
  'Toiletries & Health': '🧴',
  'Tech & Gadgets': '🔌',
  'Extras & Travel Comfort': '🎒',
}

export function PackingSlide({ data }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-10% 0px' })

  return (
    <section
      ref={ref}
      className="story-slide relative flex flex-col justify-center overflow-hidden"
      style={{ background: 'var(--story-bg)' }}
    >
      <div className="relative z-10 mx-auto w-full max-w-5xl px-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="mb-8"
        >
          <span
            className="text-xs uppercase tracking-widest"
            style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent2)' }}
          >
            Packing List
          </span>
          <h2
            style={{
              fontFamily: 'var(--font-editorial)',
              color: 'var(--story-text)',
              fontSize: 'clamp(1.8rem, 4vw, 2.8rem)',
              fontWeight: 400,
              marginTop: '0.25rem',
            }}
          >
            What to Bring
          </h2>
          {data.weather_note && (
            <p
              className="mt-1 text-sm"
              style={{ color: 'var(--story-text-muted)', fontStyle: 'italic' }}
            >
              {data.weather_note}
            </p>
          )}
        </motion.div>

        {/* Category grid — 2 or 3 columns */}
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {data.categories.map((cat, ci) => (
            <motion.div
              key={cat.category}
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.2 + ci * 0.1, duration: 0.6 }}
              className="rounded-lg p-4"
              style={{ background: 'rgba(245,240,232,0.04)', border: '1px solid var(--story-border)' }}
            >
              <div className="flex items-center gap-2 mb-3">
                <span style={{ fontSize: '1rem' }}>{CATEGORY_ICON[cat.category] ?? '•'}</span>
                <span
                  className="text-xs uppercase tracking-wider"
                  style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text-muted)' }}
                >
                  {cat.category}
                </span>
              </div>
              <ul className="flex flex-col gap-1.5">
                {cat.items.slice(0, 6).map((item) => (
                  <li
                    key={item}
                    className="text-xs flex items-start gap-2"
                    style={{ color: 'var(--story-text)', fontFamily: 'Inter, sans-serif', lineHeight: 1.4 }}
                  >
                    <span style={{ color: 'var(--story-accent2)', flexShrink: 0, marginTop: '1px' }}>–</span>
                    {item}
                  </li>
                ))}
                {cat.items.length > 6 && (
                  <li
                    className="text-xs"
                    style={{ color: 'var(--story-text-muted)', fontStyle: 'italic' }}
                  >
                    +{cat.items.length - 6} more
                  </li>
                )}
              </ul>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
