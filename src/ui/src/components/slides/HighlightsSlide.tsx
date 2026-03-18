/**
 * HighlightsSlide — "What awaits you on this trip"
 *
 * Left: featured base-camp hotel (photo + key info)
 * Right: top 3 must-experience moments (experiences + signature dining)
 */
import { useRef } from 'react'
import { motion, useInView } from 'motion/react'
import type { HighlightSlideData } from '../../lib/story'

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

        {/* Main grid: hotel (left) + moments (right) */}
        <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
          {/* Hotel card */}
          {data.hotel && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.15, duration: 0.7 }}
              className="flex flex-col overflow-hidden rounded-xl"
              style={{ border: '1px solid var(--story-border)', background: 'rgba(245,240,232,0.03)' }}
            >
              {/* Photo */}
              <div className="relative overflow-hidden" style={{ height: '200px', background: '#111' }}>
                {data.hotel.photo_url ? (
                  <img
                    src={data.hotel.photo_url}
                    alt={data.hotel.name}
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
                {data.hotel.rating && (
                  <span
                    className="absolute top-3 right-3 rounded-full px-2 py-0.5 text-xs"
                    style={{
                      background: 'rgba(10,10,10,0.75)',
                      color: 'var(--story-text)',
                      fontFamily: 'var(--font-data)',
                      backdropFilter: 'blur(4px)',
                    }}
                  >
                    ★ {data.hotel.rating.toFixed(1)}
                  </span>
                )}
              </div>

              {/* Hotel info */}
              <div className="flex flex-col gap-2 p-5 flex-1">
                <span
                  className="text-xs uppercase tracking-wider"
                  style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent)' }}
                >
                  Base Camp · {data.hotel.neighborhood}
                </span>
                <h3
                  style={{
                    fontFamily: 'var(--font-editorial)',
                    color: 'var(--story-text)',
                    fontSize: '1.4rem',
                    fontWeight: 400,
                    lineHeight: 1.2,
                  }}
                >
                  {data.hotel.name}
                </h3>
                {data.hotel.short_description && (
                  <p className="text-xs" style={{ color: 'var(--story-text-muted)', lineHeight: 1.5 }}>
                    {data.hotel.short_description}
                  </p>
                )}
                <div className="mt-auto flex items-center justify-between pt-3">
                  <span style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text)', fontSize: '1rem', fontWeight: 600 }}>
                    ~${data.hotel.nightly_rate_usd}
                    <span className="text-xs font-normal" style={{ color: 'var(--story-text-muted)' }}>/night</span>
                  </span>
                  <a
                    href={data.hotel.affiliate_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded-full px-4 py-1.5 text-xs transition-opacity hover:opacity-80"
                    style={{
                      border: '1px solid var(--story-accent)',
                      color: 'var(--story-accent)',
                      fontFamily: 'var(--font-data)',
                      textDecoration: 'none',
                    }}
                  >
                    Book stay →
                  </a>
                </div>
              </div>
            </motion.div>
          )}

          {/* Must-experience moments */}
          {data.moments.length > 0 && (
            <div className="flex flex-col gap-4">
              <span
                className="text-xs uppercase tracking-widest"
                style={{ fontFamily: 'var(--font-data)', color: 'var(--story-text-muted)' }}
              >
                Must Experience
              </span>
              <div className="flex flex-col gap-3">
                {data.moments.map((moment, i) => (
                  <motion.div
                    key={moment.name}
                    initial={{ opacity: 0, x: 20 }}
                    animate={inView ? { opacity: 1, x: 0 } : {}}
                    transition={{ delay: 0.25 + i * 0.12, duration: 0.6 }}
                    className="flex items-center gap-4 rounded-lg overflow-hidden"
                    style={{ border: '1px solid var(--story-border)', background: 'rgba(245,240,232,0.03)' }}
                  >
                    {/* Thumbnail */}
                    <div
                      className="flex-shrink-0 overflow-hidden"
                      style={{ width: '90px', height: '90px', background: '#111' }}
                    >
                      {moment.photo_url ? (
                        <img
                          src={moment.photo_url}
                          alt={moment.name}
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <div
                          className="flex h-full items-center justify-center"
                          style={{
                            background: moment.kind === 'dining'
                              ? 'linear-gradient(135deg, rgba(196,113,92,0.2) 0%, transparent 100%)'
                              : 'linear-gradient(135deg, rgba(42,127,111,0.2) 0%, transparent 100%)',
                          }}
                        >
                          <span style={{ fontSize: '1.8rem', opacity: 0.3 }}>
                            {moment.kind === 'dining' ? '🍽' : '✦'}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Text */}
                    <div className="flex flex-col gap-1 py-3 pr-4">
                      <span
                        className="text-xs uppercase tracking-wider"
                        style={{
                          fontFamily: 'var(--font-data)',
                          color: moment.kind === 'dining' ? 'var(--story-accent)' : 'var(--story-accent2)',
                        }}
                      >
                        {moment.kind === 'dining' ? 'Dining' : 'Experience'} · {moment.neighborhood}
                      </span>
                      <span
                        style={{
                          fontFamily: 'var(--font-editorial)',
                          color: 'var(--story-text)',
                          fontSize: '1.15rem',
                          fontWeight: 400,
                          lineHeight: 1.2,
                        }}
                      >
                        {moment.name}
                      </span>
                      <span
                        className="text-xs"
                        style={{ color: 'var(--story-text-muted)', fontStyle: 'italic' }}
                      >
                        {moment.caption}
                      </span>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
