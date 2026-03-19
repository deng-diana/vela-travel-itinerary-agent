/**
 * StoryPlayer — editorial slide viewer with progressive loading.
 *
 * Panel mode (default): scrollable within right panel, skeleton placeholders during streaming.
 * Standalone mode (fullScreen=true): full viewport scroll-snap for shared links.
 *
 * Skeleton sync: right panel skeletons follow the active tool step on the left panel.
 * When a section loads, pause 1s on the loaded content then scroll to the next skeleton.
 */
import { useRef, useState, useEffect, useCallback, forwardRef, memo } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import type { StorySlide } from '../lib/story'
import type { AgentStep, ItineraryDraft } from '../types'
import { API_BASE_URL } from '../types'
import { CoverSlide } from './slides/CoverSlide'
import { WeatherSlide } from './slides/WeatherSlide'
import { HighlightsSlide } from './slides/HighlightsSlide'
import { DaySlide } from './slides/DaySlide'
import { PracticalSlide } from './slides/PracticalSlide'
import { PackingSlide } from './slides/PackingSlide'
import { ClosingSlide } from './slides/ClosingSlide'

interface Props {
  slides: StorySlide[]
  fullScreen?: boolean
  isStreaming?: boolean
  steps?: AgentStep[]
  liveNarration?: string
  itinerary?: ItineraryDraft | null
  resetToTop?: number
}

// Map tool names to the slide section they produce
function toolToSection(toolName: string): string | null {
  const map: Record<string, string> = {
    get_weather: 'weather',
    get_hotels: 'highlights',
    get_restaurants: 'highlights',
    get_experiences: 'highlights',
    get_daily_structure: 'days',
    estimate_budget: 'practical',
    get_visa_requirements: 'practical',
    get_packing_suggestions: 'packing',
    write_summary: 'closing',
  }
  return map[toolName] ?? null
}

export const StoryPlayer = memo(function StoryPlayer({
  slides,
  fullScreen = false,
  isStreaming = false,
  steps = [],
  liveNarration = '',
  itinerary = null,
  resetToTop = 0,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const slideRefs = useRef<(HTMLElement | null)[]>([])
  const skeletonRef = useRef<HTMLDivElement>(null)
  const weatherSkeletonRef = useRef<HTMLDivElement>(null)
  const highlightsSkeletonRef = useRef<HTMLDivElement>(null)
  const daysSkeletonRef = useRef<HTMLDivElement>(null)
  const practicalSkeletonRef = useRef<HTMLDivElement>(null)
  const packingSkeletonRef = useRef<HTMLDivElement>(null)
  const [isPublishing, setIsPublishing] = useState(false)
  const [publishedUrl, setPublishedUrl] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  // ── Progressive reveal queue ──────────────────────────────────────
  // Instead of showing all slides at once, reveal them one at a time
  const [revealedCount, setRevealedCount] = useState(0)
  const revealTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const prevTotalSlidesRef = useRef(0)

  // When slides array grows, start revealing new slides one by one
  useEffect(() => {
    const total = slides.length
    const prevTotal = prevTotalSlidesRef.current

    if (total > prevTotal) {
      // New slides arrived — reveal them sequentially
      // Clear any existing reveal timer
      if (revealTimerRef.current) {
        clearTimeout(revealTimerRef.current)
        revealTimerRef.current = null
      }

      // If this is the first slide (cover), show it immediately
      if (prevTotal === 0 && total >= 1) {
        setRevealedCount(1)
        prevTotalSlidesRef.current = total
        // Then reveal remaining slides with delays
        if (total > 1) {
          let delay = 600
          for (let i = 1; i < total; i++) {
            const idx = i
            setTimeout(() => setRevealedCount((c) => Math.max(c, idx + 1)), delay)
            // Day slides get more time (800ms), others get 500ms
            delay += slides[i]?.type === 'day' ? 900 : 500
          }
        }
        return
      }

      // For subsequent batches of new slides, reveal them one at a time with stagger
      let delay = 300
      for (let i = prevTotal; i < total; i++) {
        const targetCount = i + 1
        setTimeout(() => setRevealedCount((c) => Math.max(c, targetCount)), delay)
        // Day slides get more reveal time so user can absorb content
        delay += slides[i]?.type === 'day' ? 900 : 500
      }
    }

    // When slides shrink (new session), reset
    if (total < prevTotal) {
      setRevealedCount(total)
    }

    prevTotalSlidesRef.current = total
  }, [slides.length]) // eslint-disable-line react-hooks/exhaustive-deps

  // Reset reveal count when streaming starts fresh
  useEffect(() => {
    if (isStreaming && slides.length <= 1) {
      setRevealedCount(slides.length)
      prevTotalSlidesRef.current = slides.length
    }
  }, [isStreaming]) // eslint-disable-line react-hooks/exhaustive-deps

  // In fullScreen or non-streaming, show all slides immediately
  const visibleSlides = (fullScreen || !isStreaming) && revealedCount < slides.length
    ? slides
    : slides.slice(0, revealedCount)

  // Track which section the active tool maps to, for skeleton focus
  const activeStep = steps.find((s) => s.status === 'active')
  // Step id format: "toolName-active-timestamp" — extract toolName
  const activeToolName = activeStep?.id?.replace(/-active-\d+$/, '') ?? ''
  const activeSection = activeToolName ? toolToSection(activeToolName) : null

  // Determine which skeleton placeholders to show during streaming
  const hasWeather = visibleSlides.some((s) => s.type === 'weather')
  const hasHighlights = visibleSlides.some((s) => s.type === 'highlights')
  const hasDays = visibleSlides.some((s) => s.type === 'day')
  const hasPractical = visibleSlides.some((s) => s.type === 'practical')
  const hasPacking = visibleSlides.some((s) => s.type === 'packing')
  const showSkeletons = isStreaming && !fullScreen

  // ── Auto-scroll: follow the latest revealed slide ─────────────────
  const prevRevealedRef = useRef(0)
  useEffect(() => {
    if (fullScreen) {
      prevRevealedRef.current = revealedCount
      return
    }

    if (revealedCount > prevRevealedRef.current && revealedCount > 0) {
      const latestIdx = revealedCount - 1
      const latestEl = slideRefs.current[latestIdx]

      if (revealedCount === 1 && isStreaming) {
        // Cover just appeared — scroll to skeleton zone after a beat
        const t = setTimeout(() => {
          skeletonRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }, 400)
        prevRevealedRef.current = revealedCount
        return () => clearTimeout(t)
      }

      if (latestEl) {
        // Scroll to the newly revealed slide
        const t = setTimeout(() => {
          latestEl.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }, 80)
        prevRevealedRef.current = revealedCount
        return () => clearTimeout(t)
      }
    }

    prevRevealedRef.current = revealedCount
  }, [revealedCount, fullScreen, isStreaming])

  // Scroll to the specific skeleton section that matches the active tool
  // (only when no new slides are being revealed)
  useEffect(() => {
    if (fullScreen || !isStreaming || !activeSection) return
    // Don't fight with reveal scroll — only scroll to skeleton if we're caught up
    if (revealedCount < slides.length) return

    const refMap: Record<string, React.RefObject<HTMLDivElement | null>> = {
      weather: weatherSkeletonRef,
      highlights: highlightsSkeletonRef,
      days: daysSkeletonRef,
      practical: practicalSkeletonRef,
      packing: packingSkeletonRef,
    }

    const targetRef = refMap[activeSection]
    if (targetRef?.current) {
      const t = setTimeout(() => {
        targetRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 300)
      return () => clearTimeout(t)
    }
  }, [activeSection, isStreaming, fullScreen, revealedCount, slides.length])

  // Handle streaming end — scroll back to top
  const wasStreamingRef = useRef(false)
  useEffect(() => {
    if (fullScreen) {
      wasStreamingRef.current = isStreaming
      return
    }
    const justEnded = wasStreamingRef.current && !isStreaming

    if (justEnded && slides.length > 2) {
      // Plan complete: reveal any remaining slides, then scroll to top
      setRevealedCount(slides.length)
      const t = setTimeout(() => {
        containerRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
      }, 1200)
      wasStreamingRef.current = isStreaming
      return () => clearTimeout(t)
    }

    wasStreamingRef.current = isStreaming
  }, [isStreaming, fullScreen]) // eslint-disable-line react-hooks/exhaustive-deps

  // External "view from start" trigger
  useEffect(() => {
    if (resetToTop > 0) {
      containerRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }, [resetToTop])

  // Track active slide via IntersectionObserver
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const idx = slideRefs.current.findIndex((el) => el === entry.target)
            if (idx !== -1) setCurrentIndex(idx)
          }
        }
      },
      { root: fullScreen ? container : null, threshold: 0.55 },
    )

    slideRefs.current.forEach((el) => { if (el) observer.observe(el) })
    return () => observer.disconnect()
  }, [visibleSlides.length, fullScreen])

  const scrollTo = useCallback((index: number) => {
    const el = slideRefs.current[index]
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])

  // Keyboard navigation (only in fullScreen)
  useEffect(() => {
    if (!fullScreen) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'ArrowDown' || e.key === 'PageDown') {
        e.preventDefault()
        scrollTo(Math.min(currentIndex + 1, visibleSlides.length - 1))
      } else if (e.key === 'ArrowUp' || e.key === 'PageUp') {
        e.preventDefault()
        scrollTo(Math.max(currentIndex - 1, 0))
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [currentIndex, visibleSlides.length, scrollTo, fullScreen])

  // Publish
  async function handlePublish() {
    if (isPublishing || !itinerary) return
    setIsPublishing(true)
    try {
      const response = await fetch(`${API_BASE_URL}/plans/publish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ itinerary }),
      })
      if (!response.ok) throw new Error('Publish failed')
      const data = await response.json() as { share_url: string }
      setPublishedUrl(data.share_url)
    } catch {
      // Non-critical
    } finally {
      setIsPublishing(false)
    }
  }

  async function handleCopyLink() {
    if (!publishedUrl) return
    await navigator.clipboard.writeText(publishedUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Empty state — before any data arrives
  if (slides.length === 0 && !isStreaming) {
    return (
      <div
        className="flex h-full items-center justify-center"
        style={{ background: 'var(--story-bg)', color: 'var(--story-text-muted)', fontFamily: 'var(--font-editorial)' }}
      >
        <div className="text-center px-8">
          <p className="text-lg" style={{ opacity: 0.4 }}>
            Your story will unfold here as Vela plans your trip.
          </p>
        </div>
      </div>
    )
  }

  const containerClass = fullScreen ? 'relative w-full h-screen' : 'relative w-full h-full'
  const scrollClass = fullScreen ? 'w-full h-screen overflow-y-scroll' : 'w-full h-full overflow-y-auto'
  const slideHeight = fullScreen ? '100vh' : '100%'
  const minSlideHeight = fullScreen ? '100vh' : 'min(100%, 100vh)'

  return (
    <div className={containerClass} style={{ background: 'var(--story-bg)' }}>
      {/* Scrollable slides container */}
      <div
        ref={containerRef}
        className={scrollClass}
        style={fullScreen ? { scrollSnapType: 'y mandatory', scrollBehavior: 'smooth' } : { scrollBehavior: 'smooth' }}
      >
        {visibleSlides.map((slide, i) => (
          <SlideWrapper
            key={slide.id}
            slide={slide}
            fullScreen={fullScreen}
            slideHeight={slideHeight}
            minSlideHeight={minSlideHeight}
            ref={(el) => { slideRefs.current[i] = el }}
          />
        ))}

        {/* Skeleton placeholders — shown during streaming, synced with active tool */}
        {showSkeletons && (
          <div ref={skeletonRef} className="px-8 lg:px-16 pb-8 space-y-6" style={{ minHeight: '100vh', paddingTop: '5vh' }}>
            {!hasWeather && (
              <div ref={weatherSkeletonRef}>
                <SkeletonCard
                  label="Weather"
                  active={activeSection === 'weather'}
                />
              </div>
            )}
            {!hasHighlights && (
              <div ref={highlightsSkeletonRef}>
                <SkeletonCard
                  label="Where to Stay"
                  active={activeSection === 'highlights'}
                />
              </div>
            )}
            {!hasDays && (
              <div ref={daysSkeletonRef}>
                <SkeletonCard
                  label="Day 1 — Itinerary"
                  wide
                  active={activeSection === 'days'}
                />
                <div className="mt-6">
                  <SkeletonCard
                    label="Day 2 — Itinerary"
                    wide
                    active={activeSection === 'days'}
                  />
                </div>
              </div>
            )}
            {!hasPractical && (
              <div ref={practicalSkeletonRef}>
                <SkeletonCard
                  label="Budget & Visa"
                  active={activeSection === 'practical'}
                />
              </div>
            )}
            {!hasPacking && (
              <div ref={packingSkeletonRef}>
                <SkeletonCard
                  label="Packing List"
                  active={activeSection === 'packing'}
                />
              </div>
            )}
          </div>
        )}

        {/* Streaming narration at the bottom */}
        <AnimatePresence>
          {isStreaming && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="px-8 py-6 lg:px-16"
              style={{ background: 'var(--story-bg)' }}
            >
              <div className="flex items-center gap-3">
                <span
                  className="h-2 w-2 flex-shrink-0 rounded-full animate-pulse"
                  style={{ background: 'var(--story-accent2)' }}
                />
                <p
                  className="text-sm leading-6"
                  style={{ color: 'var(--story-text-muted)', fontFamily: 'var(--font-data)', fontSize: '0.75rem' }}
                >
                  {liveNarration || 'Planning your journey\u2026'}
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Publish bar */}
        {!isStreaming && visibleSlides.length > 2 && !fullScreen && itinerary && (
          <div
            className="px-8 py-6 lg:px-16 flex items-center justify-center gap-3"
            style={{ background: 'var(--story-bg)' }}
          >
            {!publishedUrl ? (
              <button
                onClick={handlePublish}
                disabled={isPublishing}
                className="rounded-full px-5 py-2 text-xs transition-opacity hover:opacity-80 disabled:opacity-40"
                style={{
                  border: '1px solid var(--story-accent)',
                  color: 'var(--story-accent)',
                  background: 'transparent',
                  fontFamily: 'var(--font-data)',
                  letterSpacing: '0.05em',
                }}
              >
                {isPublishing ? 'Publishing\u2026' : 'Share this trip \u2192'}
              </button>
            ) : (
              <button
                onClick={handleCopyLink}
                className="rounded-full px-5 py-2 text-xs transition-opacity hover:opacity-80"
                style={{
                  border: '1px solid var(--story-accent2)',
                  color: 'var(--story-accent2)',
                  background: 'transparent',
                  fontFamily: 'var(--font-data)',
                  letterSpacing: '0.05em',
                }}
              >
                {copied ? 'Copied!' : 'Copy share link'}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Nav dots — fullScreen only */}
      {fullScreen && (
        <nav
          className="fixed right-6 top-1/2 -translate-y-1/2 z-50 flex flex-col gap-2.5"
          aria-label="Slide navigation"
        >
          {visibleSlides.map((slide, i) => (
            <button
              key={slide.id}
              onClick={() => scrollTo(i)}
              aria-label={`Go to slide ${i + 1}`}
              className="transition-all duration-300 rounded-full"
              style={{
                width: i === currentIndex ? '8px' : '5px',
                height: i === currentIndex ? '8px' : '5px',
                background: i === currentIndex ? 'var(--story-accent)' : 'var(--story-border)',
                opacity: i === currentIndex ? 1 : 0.6,
              }}
            />
          ))}
        </nav>
      )}

      {/* Slide counter — fullScreen only */}
      {fullScreen && (
        <div
          className="fixed bottom-6 right-8 z-50 tabular-nums"
          style={{
            fontFamily: 'var(--font-data)',
            fontSize: '0.7rem',
            color: 'var(--story-text-muted)',
            letterSpacing: '0.1em',
          }}
        >
          {String(currentIndex + 1).padStart(2, '0')} / {String(visibleSlides.length).padStart(2, '0')}
        </div>
      )}
    </div>
  )
})

// ---------------------------------------------------------------------------
// Skeleton placeholder card — with active state highlighting
// ---------------------------------------------------------------------------

function SkeletonCard({ label, wide = false, active = false }: { label: string; wide?: boolean; active?: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="rounded-2xl overflow-hidden"
      style={{
        border: active ? '1px solid rgba(196,255,77,0.25)' : '1px solid var(--story-border)',
        background: active ? 'rgba(196,255,77,0.03)' : 'rgba(245,240,232,0.02)',
      }}
    >
      <div className={`p-6 ${wide ? 'py-10' : 'py-6'}`}>
        <div className="flex items-center gap-2 mb-4">
          {active && (
            <span
              className="h-2 w-2 rounded-full animate-pulse"
              style={{ background: 'var(--story-accent)' }}
            />
          )}
          <div
            className="text-[10px] uppercase tracking-[0.2em]"
            style={{
              color: active ? 'var(--story-accent)' : 'var(--story-text-muted)',
              fontFamily: 'var(--font-data)',
            }}
          >
            {label}
          </div>
        </div>
        <div className="space-y-3">
          <div
            className="agent-shimmer h-4 rounded-full"
            style={{
              background: active ? 'rgba(196,255,77,0.1)' : 'rgba(245,240,232,0.06)',
              width: '75%',
            }}
          />
          <div
            className="agent-shimmer h-4 rounded-full"
            style={{
              background: active ? 'rgba(196,255,77,0.06)' : 'rgba(245,240,232,0.04)',
              width: '55%',
            }}
          />
          {wide && (
            <div
              className="agent-shimmer h-4 rounded-full"
              style={{
                background: active ? 'rgba(196,255,77,0.04)' : 'rgba(245,240,232,0.03)',
                width: '65%',
              }}
            />
          )}
        </div>
      </div>
    </motion.div>
  )
}

// ---------------------------------------------------------------------------
// Per-slide wrapper
// ---------------------------------------------------------------------------

interface SlideWrapperProps {
  slide: StorySlide
  fullScreen: boolean
  slideHeight: string
  minSlideHeight: string
}

const SlideWrapper = memo(forwardRef<HTMLElement, SlideWrapperProps>(
  function SlideWrapper({ slide, fullScreen, slideHeight, minSlideHeight: _minSlideHeight }, ref) {
    // Day slides can grow beyond one viewport; all others fill exactly one viewport
    const isDaySlide = slide.type === 'day'
    const style: React.CSSProperties = fullScreen
      ? {
          scrollSnapAlign: 'start',
          scrollSnapStop: 'always',
          height: slideHeight,
          overflow: 'hidden',
          flexShrink: 0,
        }
      : isDaySlide
      ? {
          minHeight: '100vh',
        }
      : {
          height: '100vh',
          overflow: 'hidden',
        }

    const inner = renderSlide(slide)
    if (!inner) return null

    return (
      <motion.div
        ref={ref as React.Ref<HTMLDivElement>}
        style={style}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: 'easeOut' }}
      >
        {inner}
      </motion.div>
    )
  }
))

function renderSlide(slide: StorySlide): React.ReactNode {
  switch (slide.type) {
    case 'cover':
      return <CoverSlide data={slide.data} />
    case 'weather':
      return <WeatherSlide data={slide.data} />
    case 'highlights':
      return <HighlightsSlide data={slide.data} />
    case 'day':
      return <DaySlide data={slide.data} />
    case 'practical':
      return <PracticalSlide data={slide.data} />
    case 'packing':
      return <PackingSlide data={slide.data} />
    case 'closing':
      return <ClosingSlide data={slide.data} />
    default:
      return null
  }
}
