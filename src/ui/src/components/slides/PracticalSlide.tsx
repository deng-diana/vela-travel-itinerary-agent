import { useRef, useEffect, useState } from 'react'
import { motion, useInView } from 'motion/react'
import type { PracticalSlideData } from '../../lib/story'

interface Props { data: PracticalSlideData }

export function PracticalSlide({ data }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-10% 0px' })

  return (
    <section
      ref={ref}
      className="story-slide relative flex items-center justify-center overflow-hidden"
      style={{ background: 'var(--story-bg)' }}
    >
      <div className="relative z-10 mx-auto grid max-w-5xl w-full gap-12 px-10 lg:grid-cols-2 items-start">
        {/* Budget column */}
        {data.budget && (
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.7 }}
            className="flex flex-col gap-5"
          >
            <div className="mb-2">
              <span
                className="text-xs uppercase tracking-widest"
                style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent)' }}
              >
                Trip Budget Estimate
              </span>
              <h2
                style={{
                  fontFamily: 'var(--font-editorial)',
                  color: 'var(--story-text)',
                  fontSize: 'clamp(1.6rem, 3.5vw, 2.5rem)',
                  fontWeight: 400,
                  marginTop: '0.25rem',
                }}
              >
                ~${data.budget.grand_total_usd.toLocaleString()} {data.budget.currency}
              </h2>
              <p
                style={{
                  fontFamily: 'var(--font-data)',
                  color: 'var(--story-text-muted)',
                  fontSize: '0.8rem',
                  marginTop: '0.25rem',
                }}
              >
                ${data.budget.daily_average_usd}/day average · {data.budget.trip_length_days} days
              </p>
            </div>

            {data.budget.line_items.map((item, i) => (
              <BudgetBar
                key={item.category}
                item={item}
                total={data.budget!.grand_total_usd}
                index={i}
                inView={inView}
              />
            ))}

            {data.budget.notes.map((note) => (
              <p
                key={note}
                className="text-xs"
                style={{ color: 'var(--story-text-muted)', fontStyle: 'italic' }}
              >
                {note}
              </p>
            ))}
          </motion.div>
        )}

        {/* Visa column */}
        {data.visa && (
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="flex flex-col gap-4"
          >
            <div className="mb-2">
              <span
                className="text-xs uppercase tracking-widest"
                style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent2)' }}
              >
                Entry Requirements
              </span>
              <h2
                style={{
                  fontFamily: 'var(--font-editorial)',
                  color: 'var(--story-text)',
                  fontSize: 'clamp(1.4rem, 3vw, 2rem)',
                  fontWeight: 400,
                  marginTop: '0.25rem',
                }}
              >
                {data.visa.visa_type}
              </h2>
              {data.visa.max_stay_days && (
                <p
                  style={{
                    fontFamily: 'var(--font-data)',
                    color: 'var(--story-text-muted)',
                    fontSize: '0.8rem',
                    marginTop: '0.25rem',
                  }}
                >
                  Up to {data.visa.max_stay_days} days · {data.visa.nationality} passport
                </p>
              )}
            </div>

            {/* Required docs */}
            <div className="flex flex-col gap-2">
              <p
                className="text-xs uppercase tracking-wider mb-1"
                style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text-muted)' }}
              >
                Required Documents
              </p>
              {data.visa.required_docs.map((doc, i) => (
                <motion.div
                  key={doc}
                  initial={{ opacity: 0, x: 12 }}
                  animate={inView ? { opacity: 1, x: 0 } : {}}
                  transition={{ delay: 0.5 + i * 0.08 }}
                  className="flex items-start gap-2 text-sm"
                  style={{ color: 'var(--story-text)' }}
                >
                  <span style={{ color: 'var(--story-accent2)', marginTop: '2px', flexShrink: 0 }}>✓</span>
                  {doc}
                </motion.div>
              ))}
            </div>

            {/* Fee / processing */}
            <div className="flex flex-wrap gap-4 mt-2">
              {data.visa.fee_usd != null && (
                <div className="flex flex-col">
                  <span
                    className="text-xs"
                    style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text-muted)' }}
                  >
                    Fee
                  </span>
                  <span style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text)', fontWeight: 600 }}>
                    {data.visa.fee_usd === 0 ? 'Free' : `$${data.visa.fee_usd}`}
                  </span>
                </div>
              )}
              {data.visa.processing_days != null && (
                <div className="flex flex-col">
                  <span
                    className="text-xs"
                    style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text-muted)' }}
                  >
                    Processing
                  </span>
                  <span style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text)', fontWeight: 600 }}>
                    {data.visa.processing_days === 0 ? 'On arrival' : `${data.visa.processing_days} days`}
                  </span>
                </div>
              )}
            </div>

            {data.visa.notes && (
              <p
                className="text-xs mt-1"
                style={{ color: 'var(--story-text-muted)', fontStyle: 'italic', maxWidth: '45ch' }}
              >
                {data.visa.notes}
              </p>
            )}

            {data.visa.official_link && (
              <a
                href={data.visa.official_link}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 text-xs hover:opacity-80"
                style={{
                  color: 'var(--story-accent2)',
                  fontFamily: 'var(--font-data)',
                  textDecoration: 'none',
                }}
              >
                Official source →
              </a>
            )}
          </motion.div>
        )}
      </div>
    </section>
  )
}

function BudgetBar({
  item,
  total,
  index,
  inView,
}: {
  item: { category: string; amount_usd: number; detail: string }
  total: number
  index: number
  inView: boolean
}) {
  const pct = Math.round((item.amount_usd / total) * 100)
  const [width, setWidth] = useState(0)

  useEffect(() => {
    if (!inView) return
    const t = setTimeout(() => setWidth(pct), 300 + index * 100)
    return () => clearTimeout(t)
  }, [inView, pct, index])

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between">
        <span className="text-sm" style={{ color: 'var(--story-text)', fontFamily: 'Inter, sans-serif' }}>
          {item.category}
        </span>
        <span
          style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text)', fontSize: '0.85rem', fontWeight: 600 }}
        >
          ${item.amount_usd.toLocaleString()}
        </span>
      </div>
      <div
        className="relative h-[3px] rounded-full overflow-hidden"
        style={{ background: 'var(--story-border)' }}
      >
        <div
          className="absolute left-0 top-0 h-full rounded-full transition-all duration-700"
          style={{
            width: `${width}%`,
            background: 'var(--story-accent)',
            transitionDelay: `${index * 0.1}s`,
          }}
        />
      </div>
      <p className="text-xs" style={{ color: 'var(--story-text-muted)', fontFamily: 'Inter, sans-serif' }}>
        {item.detail}
      </p>
    </div>
  )
}
