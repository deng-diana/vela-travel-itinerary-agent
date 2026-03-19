import { useRef, useEffect, useState } from 'react'
import { motion, useInView } from 'motion/react'
import type { WeatherSlideData } from '../../lib/story'

interface Props { data: WeatherSlideData }

// ---------------------------------------------------------------------------
// Weather-aware tips generator
// ---------------------------------------------------------------------------

interface WeatherTip {
  icon: string
  label: string
  highlight?: boolean
}

function generateWeatherTips(
  temp: number | null,
  rainfall: number | null,
  summary: string,
): WeatherTip[] {
  const tips: WeatherTip[] = []
  const s = summary.toLowerCase()

  // Umbrella / rain
  if (rainfall != null && rainfall > 5) {
    tips.push({ icon: '☂️', label: 'Bring an umbrella — expect rainy spells', highlight: true })
  } else if (s.includes('rain') || s.includes('shower')) {
    tips.push({ icon: '☂️', label: 'Pack a compact umbrella, just in case', highlight: true })
  }

  // Temperature-based clothing
  if (temp != null) {
    if (temp <= 5) {
      tips.push({ icon: '🧥', label: 'Heavy coat & warm layers essential', highlight: true })
      tips.push({ icon: '🧤', label: 'Gloves, scarf & beanie recommended' })
    } else if (temp <= 12) {
      tips.push({ icon: '🧥', label: 'Bring a warm jacket for cool days', highlight: true })
      tips.push({ icon: '👟', label: 'Comfortable walking shoes with grip' })
    } else if (temp <= 20) {
      tips.push({ icon: '👕', label: 'Light layers — warm days, cool evenings' })
      tips.push({ icon: '👟', label: 'Comfortable walking shoes' })
    } else if (temp <= 28) {
      tips.push({ icon: '👕', label: 'Light, breathable clothing' })
      tips.push({ icon: '🧴', label: 'Sunscreen SPF 30+ recommended', highlight: true })
    } else {
      tips.push({ icon: '🩳', label: 'Lightweight clothing — it\'s hot!', highlight: true })
      tips.push({ icon: '🧴', label: 'High SPF sunscreen is a must', highlight: true })
      tips.push({ icon: '💧', label: 'Stay hydrated — carry a water bottle' })
    }
  }

  // Sun-related
  if (s.includes('sun') || s.includes('clear') || (temp != null && temp > 22)) {
    tips.push({ icon: '🕶️', label: 'Sunglasses for bright days' })
  }

  // Wind
  if (s.includes('wind')) {
    tips.push({ icon: '💨', label: 'Windbreaker recommended for gusty days' })
  }

  // Snow
  if (s.includes('snow')) {
    tips.push({ icon: '❄️', label: 'Waterproof boots for snowy conditions', highlight: true })
  }

  // Ensure at least 3 tips
  if (tips.length < 3) {
    tips.push({ icon: '👟', label: 'Comfortable walking shoes for exploring' })
  }

  return tips.slice(0, 4)
}

// ---------------------------------------------------------------------------
// Animated weather icon
// ---------------------------------------------------------------------------

function WeatherIcon({ temp, summary }: { temp: number | null; summary: string }) {
  const s = summary.toLowerCase()
  const isRainy = s.includes('rain') || s.includes('shower')
  const isSnowy = s.includes('snow')
  const isCloudy = s.includes('cloud') || s.includes('overcast')
  const isSunny = s.includes('sun') || s.includes('clear') || s.includes('warm')

  if (isSnowy) {
    return (
      <motion.div
        className="flex items-center justify-center"
        style={{ width: '80px', height: '80px' }}
      >
        <motion.span
          animate={{ y: [0, -4, 0] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          style={{ fontSize: '3.5rem', filter: 'drop-shadow(0 0 12px rgba(200,220,255,0.3))' }}
        >
          ❄️
        </motion.span>
      </motion.div>
    )
  }

  if (isRainy) {
    return (
      <motion.div
        className="relative flex items-center justify-center"
        style={{ width: '80px', height: '80px' }}
      >
        <motion.span
          animate={{ y: [0, -3, 0] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
          style={{ fontSize: '3.5rem', filter: 'drop-shadow(0 0 12px rgba(100,160,255,0.25))' }}
        >
          🌧️
        </motion.span>
      </motion.div>
    )
  }

  if (isCloudy) {
    return (
      <motion.div
        className="flex items-center justify-center"
        style={{ width: '80px', height: '80px' }}
      >
        <motion.span
          animate={{ x: [0, 5, 0] }}
          transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
          style={{ fontSize: '3.5rem', filter: 'drop-shadow(0 0 8px rgba(180,180,180,0.2))' }}
        >
          ⛅
        </motion.span>
      </motion.div>
    )
  }

  if (isSunny || (temp != null && temp > 22)) {
    return (
      <motion.div
        className="flex items-center justify-center"
        style={{ width: '80px', height: '80px' }}
      >
        <motion.span
          animate={{ rotate: [0, 15, -15, 0], scale: [1, 1.05, 1] }}
          transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
          style={{ fontSize: '3.5rem', filter: 'drop-shadow(0 0 16px rgba(255,200,50,0.35))' }}
        >
          ☀️
        </motion.span>
      </motion.div>
    )
  }

  // Default: partly cloudy
  return (
    <motion.div
      className="flex items-center justify-center"
      style={{ width: '80px', height: '80px' }}
    >
      <motion.span
        animate={{ x: [0, 3, 0] }}
        transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
        style={{ fontSize: '3.5rem', filter: 'drop-shadow(0 0 8px rgba(180,200,220,0.2))' }}
      >
        🌤️
      </motion.span>
    </motion.div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function WeatherSlide({ data }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-10% 0px' })
  const [displayTemp, setDisplayTemp] = useState(0)

  const tips = generateWeatherTips(data.avg_temp_c, data.rainfall_mm, data.conditions_summary)

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
        {/* Left: giant temperature + weather icon */}
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
            <div className="flex items-center gap-5">
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
              <WeatherIcon temp={data.avg_temp_c} summary={data.conditions_summary} />
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
            <div className="flex items-center gap-2">
              <motion.span
                animate={{ y: [0, 2, 0] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                style={{ fontSize: '1rem' }}
              >
                💧
              </motion.span>
              <span
                style={{
                  fontFamily: 'var(--font-data)',
                  color: 'var(--story-text-muted)',
                  fontSize: '0.8rem',
                  letterSpacing: '0.05em',
                }}
              >
                {data.rainfall_mm}mm avg. rainfall
              </span>
            </div>
          )}
        </motion.div>

        {/* Right: weather-aware tips */}
        <motion.div
          initial={{ opacity: 0, x: 24 }}
          animate={inView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
          className="flex flex-col gap-3"
        >
          <p
            className="text-xs uppercase tracking-widest mb-3"
            style={{ fontFamily: 'var(--font-data)', color: 'var(--story-accent2)' }}
          >
            Travel Advisory
          </p>
          {tips.map((tip, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: 16 }}
              animate={inView ? { opacity: 1, x: 0 } : {}}
              transition={{ delay: 0.4 + i * 0.12, duration: 0.5 }}
              className="flex items-center gap-3 rounded-lg px-4 py-3"
              style={{
                background: tip.highlight
                  ? 'rgba(42,127,111,0.12)'
                  : 'rgba(245,240,232,0.04)',
                border: tip.highlight
                  ? '1px solid rgba(42,127,111,0.25)'
                  : '1px solid rgba(245,240,232,0.06)',
              }}
            >
              <motion.span
                animate={tip.highlight ? { scale: [1, 1.15, 1] } : {}}
                transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                style={{ fontSize: '1.3rem', flexShrink: 0 }}
              >
                {tip.icon}
              </motion.span>
              <span
                style={{
                  color: tip.highlight ? 'var(--story-text)' : 'var(--story-text-muted)',
                  fontSize: '0.9rem',
                  lineHeight: 1.5,
                  fontWeight: tip.highlight ? 500 : 400,
                }}
              >
                {tip.label}
              </span>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}
