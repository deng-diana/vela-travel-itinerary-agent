/**
 * StoryPlayer — scroll-snap container for Story Mode.
 *
 * Features:
 * - scroll-snap-type y mandatory (one slide = 100vh)
 * - Nav dots on right side, keyboard ↑/↓, mouse wheel handled natively
 * - Progress bar at top (current slide / total)
 * - Slide counter bottom-right
 * - Renders all typed slide components
 */
import { useRef, useState, useEffect, useCallback, forwardRef } from 'react'
import type { StorySlide } from '../lib/story'
import { CoverSlide } from './slides/CoverSlide'
import { WeatherSlide } from './slides/WeatherSlide'
import { HighlightsSlide } from './slides/HighlightsSlide'
import { DaySlide } from './slides/DaySlide'
import { PracticalSlide } from './slides/PracticalSlide'
import { PackingSlide } from './slides/PackingSlide'
import { ClosingSlide } from './slides/ClosingSlide'

interface Props {
  slides: StorySlide[]
}

export function StoryPlayer({ slides }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const slideRefs = useRef<(HTMLElement | null)[]>([])

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
      { root: container, threshold: 0.55 },
    )

    slideRefs.current.forEach((el) => { if (el) observer.observe(el) })
    return () => observer.disconnect()
  }, [slides])

  const scrollTo = useCallback((index: number) => {
    const el = slideRefs.current[index]
    if (el) el.scrollIntoView({ behavior: 'smooth' })
  }, [])

  // Keyboard navigation
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'ArrowDown' || e.key === 'PageDown') {
        e.preventDefault()
        scrollTo(Math.min(currentIndex + 1, slides.length - 1))
      } else if (e.key === 'ArrowUp' || e.key === 'PageUp') {
        e.preventDefault()
        scrollTo(Math.max(currentIndex - 1, 0))
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [currentIndex, slides.length, scrollTo])

  return (
    <div className="relative w-full h-screen" style={{ background: 'var(--story-bg)' }}>
      {/* Top progress bar */}
      <div
        className="fixed top-0 left-0 z-50 h-[2px] transition-all duration-500"
        style={{
          width: `${((currentIndex + 1) / slides.length) * 100}%`,
          background: 'var(--story-accent)',
        }}
      />

      {/* Scrollable slides container */}
      <div
        ref={containerRef}
        className="w-full h-screen overflow-y-scroll"
        style={{
          scrollSnapType: 'y mandatory',
          scrollBehavior: 'smooth',
        }}
      >
        {slides.map((slide, i) => (
          <SlideWrapper
            key={slide.id}
            slide={slide}
            ref={(el) => { slideRefs.current[i] = el }}
          />
        ))}
      </div>

      {/* Nav dots — right side */}
      <nav
        className="fixed right-6 top-1/2 -translate-y-1/2 z-50 flex flex-col gap-2.5"
        aria-label="Slide navigation"
      >
        {slides.map((slide, i) => (
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

      {/* Slide counter — bottom right */}
      <div
        className="fixed bottom-6 right-8 z-50 tabular-nums"
        style={{
          fontFamily: 'var(--font-data)',
          fontSize: '0.7rem',
          color: 'var(--story-text-muted)',
          letterSpacing: '0.1em',
        }}
      >
        {String(currentIndex + 1).padStart(2, '0')} / {String(slides.length).padStart(2, '0')}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Per-slide wrapper — applies scroll-snap-align: start + 100vh height
// ---------------------------------------------------------------------------

const SlideWrapper = forwardRef<HTMLElement, { slide: StorySlide }>(function SlideWrapper({ slide }, ref) {
  const style: React.CSSProperties = {
    scrollSnapAlign: 'start',
    scrollSnapStop: 'always',
    height: '100vh',
    overflow: 'hidden',
    flexShrink: 0,
  }

  const inner = renderSlide(slide)
  if (!inner) return null

  // Clone the inner element, injecting the scroll-snap style + ref onto its root
  // Instead, we wrap in a div to guarantee scroll-snap semantics
  return (
    <div ref={ref as React.Ref<HTMLDivElement>} style={style}>
      {inner}
    </div>
  )
})

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
