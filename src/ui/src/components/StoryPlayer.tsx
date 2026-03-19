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

// Map slide type to section (reverse of toolToSection, for rerun overlay)
function slideTypeToSection(slideType: string): string | null {
  const map: Record<string, string> = {
    weather: 'weather',
    highlights: 'highlights',
    day: 'days',
    practical: 'practical',
    packing: 'packing',
    closing: 'closing',
  }
  return map[slideType] ?? null
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

  // ── Progressive reveal — two modes ───────────────────────────────
  // First run:  ID-based (new slide IDs appear as tools complete)
  // Rerun:      Step-based (completed tool steps reveal their slide types)
  //             Slide IDs are stable on rerun, so ID-detection would never fire.
  const [revealedIds, setRevealedIds] = useState<Set<string>>(new Set())
  const [lastRevealedId, setLastRevealedId] = useState<string | null>(null)
  const prevSlideIdsRef = useRef<Set<string>>(new Set())
  const revealTimersRef = useRef<ReturnType<typeof setTimeout>[]>([])

  // Rerun scroll tracking — declared here so reset effect can access them
  const prevActiveSectionRef = useRef<string | null>(null)
  const hasScrolledForRerunRef = useRef(false)

  // Rerun mode flag — set to true from streaming start until streaming end
  const isRerunRef = useRef(false)
  // Tracks which tool names have already triggered reveals during rerun
  const revealedToolsRef = useRef<Set<string>>(new Set())

  // Which slide types each tool produces (for step-based rerun reveals)
  const TOOL_TO_SLIDE_TYPES: Record<string, string[]> = {
    get_weather: ['weather'],
    get_hotels: ['highlights'],
    get_restaurants: ['highlights'],
    get_experiences: ['highlights'],
    get_daily_structure: ['day'],
    estimate_budget: ['practical'],
    get_visa_requirements: ['practical'],
    get_packing_suggestions: ['packing'],
    write_summary: ['closing'],
  }

  // ── FIRST RUN: ID-based progressive reveal ────────────────────────
  // When slides array changes, detect new IDs and stagger-reveal them.
  // During rerun this effect only does housekeeping (no reveals).
  useEffect(() => {
    const currentIds = slides.map((s) => s.id)

    if (isRerunRef.current) {
      // Rerun: just keep prevSlideIdsRef current; reveals come from [steps] effect.
      // Surgically remove any IDs that no longer exist (e.g. day count changed).
      const removedIds = [...prevSlideIdsRef.current].filter((id) => !currentIds.includes(id))
      if (removedIds.length > 0) {
        setRevealedIds((prev) => {
          const next = new Set(prev)
          removedIds.forEach((id) => next.delete(id))
          return next
        })
      }
      prevSlideIdsRef.current = new Set(currentIds)
      return
    }

    const newIds = currentIds.filter((id) => !prevSlideIdsRef.current.has(id))
    const removedIds = [...prevSlideIdsRef.current].filter((id) => !currentIds.includes(id))

    // Surgically remove stale IDs — never wipe the entire set
    if (removedIds.length > 0) {
      setRevealedIds((prev) => {
        const next = new Set(prev)
        removedIds.forEach((id) => next.delete(id))
        return next
      })
      setLastRevealedId(null)
      revealTimersRef.current.forEach(clearTimeout)
      revealTimersRef.current = []
      prevSlideIdsRef.current = new Set(currentIds)
    }

    if (newIds.length === 0) {
      prevSlideIdsRef.current = new Set(currentIds)
      return
    }

    revealTimersRef.current.forEach(clearTimeout)
    revealTimersRef.current = []

    const isFirstBatch = prevSlideIdsRef.current.size === 0
    let delay = isFirstBatch ? 0 : 300

    for (const newId of newIds) {
      const slide = slides.find((s) => s.id === newId)
      const t = setTimeout(() => {
        setRevealedIds((prev) => new Set([...prev, newId]))
        setLastRevealedId(newId)
      }, delay)
      revealTimersRef.current.push(t)
      delay += slide?.type === 'day' ? 900 : 500
    }

    prevSlideIdsRef.current = new Set(currentIds)
  }, [slides]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── RERUN: Step-based progressive reveal ─────────────────────────
  // Watches completed tool steps and immediately reveals the corresponding
  // slide types. This gives true progressive reveal even though IDs are stable.
  useEffect(() => {
    if (!isRerunRef.current || fullScreen) return

    for (const step of steps) {
      if (step.status !== 'completed') continue
      const toolName = step.id.replace(/-completed-\d+$/, '')
      if (revealedToolsRef.current.has(toolName)) continue
      revealedToolsRef.current.add(toolName)

      const slideTypes = TOOL_TO_SLIDE_TYPES[toolName] ?? []
      if (slideTypes.length === 0) continue

      const matchingIds = slides.filter((s) => slideTypes.includes(s.type)).map((s) => s.id)
      if (matchingIds.length > 0) {
        setRevealedIds((prev) => {
          const next = new Set(prev)
          matchingIds.forEach((id) => next.add(id))
          return next
        })
      }
    }
  }, [steps, slides, fullScreen]) // eslint-disable-line react-hooks/exhaustive-deps

  // Reset when streaming starts (new session or rerun)
  useEffect(() => {
    hasScrolledForRerunRef.current = false
    prevActiveSectionRef.current = null

    if (isStreaming) {
      revealTimersRef.current.forEach(clearTimeout)
      revealTimersRef.current = []
      setLastRevealedId(null)

      if (slides.length > 0) {
        // Rerun: cover stays visible; other sections revealed progressively via [steps]
        isRerunRef.current = true
        revealedToolsRef.current = new Set()
        const coverIds = new Set(slides.filter((s) => s.type === 'cover').map((s) => s.id))
        setRevealedIds(coverIds)
        // Keep all existing IDs in prev so [slides] doesn't see them as "new"
        prevSlideIdsRef.current = new Set(slides.map((s) => s.id))
      } else {
        // Fresh start
        isRerunRef.current = false
        setRevealedIds(new Set())
        prevSlideIdsRef.current = new Set()
      }
    }
  }, [isStreaming]) // eslint-disable-line react-hooks/exhaustive-deps

  // In fullScreen or non-streaming, show all slides immediately
  const visibleSlides = fullScreen || !isStreaming
    ? slides
    : slides.filter((s) => revealedIds.has(s.id))

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
  useEffect(() => {
    if (fullScreen || !isStreaming || !lastRevealedId) return

    // Cover just appeared — scroll to skeleton zone after a beat
    if (revealedIds.size === 1) {
      const t = setTimeout(() => {
        skeletonRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 400)
      return () => clearTimeout(t)
    }

    // Scroll to the newly revealed slide (find its position in visibleSlides)
    const idx = visibleSlides.findIndex((s) => s.id === lastRevealedId)
    if (idx !== -1 && slideRefs.current[idx]) {
      const t = setTimeout(() => {
        slideRefs.current[idx]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 80)
      return () => clearTimeout(t)
    }
  }, [lastRevealedId, fullScreen, isStreaming]) // eslint-disable-line react-hooks/exhaustive-deps

  // Scroll to the specific skeleton section that matches the active tool
  // (only when no new slides are being revealed — i.e. reveals are caught up)
  useEffect(() => {
    if (fullScreen || !isStreaming || !activeSection) return
    // Don't fight with reveal scroll — only scroll to skeleton if caught up
    if (visibleSlides.length < slides.length) return

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
  }, [activeSection, isStreaming, fullScreen, visibleSlides.length, slides.length]) // eslint-disable-line react-hooks/exhaustive-deps

  // During a rerun: scroll to the slide being updated — but only for MAJOR
  // sections (days, highlights, weather). For practical/packing the isUpdating
  // overlay shows in-place without hijacking the scroll position.
  const SCROLL_WORTHY_SECTIONS = new Set(['days', 'highlights', 'weather'])

  useEffect(() => {
    if (fullScreen || !isStreaming) {
      prevActiveSectionRef.current = activeSection
      hasScrolledForRerunRef.current = false
      return
    }

    if (!activeSection || activeSection === prevActiveSectionRef.current) return
    prevActiveSectionRef.current = activeSection

    // Only scroll for major sections that are worth navigating to
    if (!SCROLL_WORTHY_SECTIONS.has(activeSection)) return

    // Don't scroll more than once per rerun cycle to avoid jarring jumps
    if (hasScrolledForRerunRef.current) return

    // Find the slide (for days, scroll to the FIRST day slide)
    const idx = visibleSlides.findIndex((s) => slideTypeToSection(s.type) === activeSection)
    if (idx === -1) return // no existing slide — skeleton handles it

    const el = slideRefs.current[idx]
    if (el) {
      hasScrolledForRerunRef.current = true
      const t = setTimeout(() => {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 300)
      return () => clearTimeout(t)
    }
  }, [activeSection, isStreaming, fullScreen, visibleSlides]) // eslint-disable-line react-hooks/exhaustive-deps

  // Handle streaming end — reveal remaining slides and scroll to top
  const wasStreamingRef = useRef(false)
  useEffect(() => {
    if (fullScreen) {
      wasStreamingRef.current = isStreaming
      return
    }
    const justEnded = wasStreamingRef.current && !isStreaming

    if (justEnded && slides.length > 0) {
      revealTimersRef.current.forEach(clearTimeout)
      revealTimersRef.current = []
      // Reveal any slides that didn't get revealed during streaming (e.g. closing)
      setRevealedIds(new Set(slides.map((s) => s.id)))
      const scrollDelay = isRerunRef.current ? 600 : 1200
      isRerunRef.current = false
      const t = setTimeout(() => {
        containerRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
      }, scrollDelay)
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
        data-story-scroll
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
            isUpdating={isStreaming && !fullScreen && slideTypeToSection(slide.type) === activeSection}
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
  isUpdating?: boolean
}

const SlideWrapper = memo(forwardRef<HTMLElement, SlideWrapperProps>(
  function SlideWrapper({ slide, fullScreen, slideHeight, minSlideHeight: _minSlideHeight, isUpdating = false }, ref) {
    // Day slides can grow beyond one viewport; all others fill exactly one viewport
    const isDaySlide = slide.type === 'day'
    const style: React.CSSProperties = fullScreen
      ? {
          scrollSnapAlign: 'start',
          scrollSnapStop: 'always',
          height: slideHeight,
          overflow: 'hidden',
          flexShrink: 0,
          position: 'relative',
        }
      : isDaySlide
      ? {
          minHeight: '100vh',
          position: 'relative',
        }
      : {
          height: '100vh',
          overflow: 'hidden',
          position: 'relative',
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
        <AnimatePresence>
          {isUpdating && (
            <motion.div
              key="updating-overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="absolute inset-0 pointer-events-none"
              style={{
                boxShadow: 'inset 0 0 0 1px rgba(196,255,77,0.25)',
              }}
            >
              {/* Updating badge — top-right corner */}
              <div
                className="absolute top-4 right-5 flex items-center gap-1.5 rounded-full px-3 py-1.5"
                style={{
                  background: 'rgba(10,9,8,0.88)',
                  border: '1px solid rgba(196,255,77,0.4)',
                  backdropFilter: 'blur(6px)',
                }}
              >
                <span
                  className="h-1.5 w-1.5 rounded-full animate-pulse"
                  style={{ background: 'var(--story-accent)' }}
                />
                <span
                  className="text-[10px] uppercase tracking-[0.18em]"
                  style={{ color: 'var(--story-accent)', fontFamily: 'var(--font-data)' }}
                >
                  Updating
                </span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
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
