import { useEffect, useRef } from 'react'
import type { FormEvent } from 'react'
import { motion } from 'motion/react'
import { ArrowUp, ChevronLeft } from 'lucide-react'
import type { ChatMessage } from '../types'
import { MarkdownMessage } from './MarkdownMessage'
import { ThinkingDots } from './ThinkingDots'

type LandingProps = {
  messages: ChatMessage[]
  input: string
  isStreaming: boolean
  liveNarration: string
  error: string | null
  onInputChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

const WELCOME_MESSAGE =
  "Hi, I'm **Vela** — your travel planning companion.\n\nTell me about your trip and I'll build a personalized itinerary. Here's what helps:\n\n— **Where** you're going and **when**\n— **How long** and **who's** coming\n— **Budget** style (budget / mid-range / luxury)\n— **Interests** — food, art, nightlife, nature, anything\n— **Dietary** needs and **stay** preference (hotel, hostel, Airbnb)\n\nShare as much as you'd like — I'll ask about anything I still need."

export function Landing({ messages, input, isStreaming, liveNarration, error, onInputChange, onSubmit }: LandingProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom on every new message / narration
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, liveNarration, isStreaming])

  // Reset textarea height when input is cleared
  useEffect(() => {
    if (!input && textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [input])

  // Always keep textarea focused so cursor is visible
  useEffect(() => {
    const timer = setTimeout(() => {
      textareaRef.current?.focus()
    }, 400) // wait for entrance animation
    return () => clearTimeout(timer)
  }, [])

  const showThinking = isStreaming && !liveNarration
  const isInitial = messages.length === 0 && !liveNarration && !isStreaming

  return (
    <motion.section
      key="landing"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -18 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className="flex min-h-screen w-full flex-col items-center px-6"
      style={{ background: 'var(--bg-dark)', position: 'relative' }}
    >
      {/* Back button — shown when conversation has started */}
      {messages.length > 0 && (
        <button
          onClick={() => window.location.reload()}
          className="absolute top-6 left-6 p-2 transition-opacity hover:opacity-70"
          style={{ color: 'var(--color-text-muted)' }}
          title="Return to home"
        >
          <ChevronLeft size={24} />
        </button>
      )}

      {/* Vertical centering wrapper — centers the content group on the page */}
      <div
        className="w-full max-w-2xl flex flex-col"
        style={{
          flex: isInitial ? '1 1 auto' : '0 0 auto',
          justifyContent: isInitial ? 'center' : 'flex-start',
          paddingTop: isInitial ? '0' : '80px',
        }}
      >
        {/* Header: Logo + Title + Description (only show when no messages) */}
        {isInitial && (
          <motion.div
            className="w-full text-center"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            {/* Logo */}
            <div className="flex justify-center" style={{ marginBottom: '16px' }}>
              <img src="/logo.svg" alt="Vela" width={96} height={96} style={{ display: 'block' }} />
            </div>

            {/* Title: 32px */}
            <h1
              style={{
                fontFamily: 'var(--font-editorial)',
                color: 'var(--color-text)',
                fontSize: '32px',
                fontWeight: 600,
                lineHeight: '1.2',
                marginBottom: '16px',
              }}
            >
              Vela Travel Planner
            </h1>

            {/* Description: 16px, single line */}
            <p
              style={{
                fontFamily: 'var(--font-editorial)',
                color: 'var(--color-text-muted)',
                fontSize: '16px',
                lineHeight: '1.5',
                margin: 0,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              A warmer way to turn travel ideas into journeys planned with care.
            </p>
          </motion.div>
        )}

        {/* Onboarding message — 48px below description */}
        {isInitial && (
          <article
            className="rounded-lg flex gap-3"
            style={{
              border: '1px solid var(--color-border)',
              color: 'var(--color-text)',
              padding: '20px',
              marginTop: '36px',
            }}
          >
            <div className="flex-shrink-0 mt-0.5">
              <img src="/vela-avatar.svg" alt="Vela" width={24} height={24} style={{ borderRadius: '50%' }} />
            </div>
            <div className="flex-1 min-w-0">
              <MarkdownMessage text={WELCOME_MESSAGE} />
            </div>
          </article>
        )}

        {/* Conversation messages */}
        {messages.length > 0 && (
          <div className="flex flex-col gap-6">
            {messages.map((message, index) =>
              message.role === 'user' ? (
                <div key={`landing-user-${index}`} className="flex justify-end mb-4">
                  <article
                    className="rounded-lg text-sm leading-7 max-w-[85%]"
                    style={{
                      background: 'var(--bg-user)',
                      color: 'var(--color-text)',
                      padding: '12px 16px',
                    }}
                  >
                    <div className="whitespace-pre-line">{message.text}</div>
                  </article>
                </div>
              ) : (
                <article
                  key={`landing-assistant-${index}`}
                  className="rounded-lg text-sm leading-7 mb-4 flex gap-3"
                  style={{
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-text)',
                    padding: '20px',
                  }}
                >
                  <div className="flex-shrink-0 mt-0.5">
                    <img src="/vela-avatar.svg" alt="Vela" width={24} height={24} style={{ borderRadius: '50%' }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <MarkdownMessage text={message.text} />
                  </div>
                </article>
              )
            )}

            {/* Live narration */}
            {liveNarration && (
              <div
                className="rounded-lg flex gap-3"
                style={{
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text)',
                  padding: '20px',
                }}
              >
                <div className="flex-shrink-0 mt-0.5">
                  <img src="/vela-avatar.svg" alt="Vela" width={24} height={24} style={{ borderRadius: '50%' }} />
                </div>
                <div className="flex-1 min-w-0">
                  {liveNarration}
                </div>
              </div>
            )}

            {showThinking && <ThinkingDots />}

            {error && (
              <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {error}
              </div>
            )}

            {/* Scroll anchor */}
            <div ref={bottomRef} />
          </div>
        )}

        {/* Input — 36px below onboarding/messages */}
        <div style={{ marginTop: '36px', paddingBottom: '48px' }}>
          <form onSubmit={onSubmit}>
            <div
              className="flex rounded-lg overflow-hidden"
              style={{
                background: 'var(--bg-input)',
                border: '1px solid var(--color-border)',
              }}
            >
              <textarea
                  ref={textareaRef}
                  className="flex-1 outline-none resize-none bg-transparent"
                  style={{
                    color: 'var(--color-text)',
                    fontFamily: 'var(--font-editorial)',
                    fontSize: '1rem',
                    lineHeight: '1.5rem',
                    minHeight: '52px',
                    maxHeight: '160px',
                    overflowY: 'auto',
                    padding: '14px 0 14px 24px',
                    caretColor: 'var(--color-accent)',
                  }}
                  value={input}
                  onChange={(event) => {
                    onInputChange(event.target.value)
                    const el = event.target
                    el.style.height = 'auto'
                    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      e.currentTarget.form?.requestSubmit()
                      if (textareaRef.current) {
                        textareaRef.current.style.height = 'auto'
                      }
                    }
                  }}
                  onBlur={() => {
                    // Re-focus after blur to keep cursor always visible
                    if (isInitial) {
                      setTimeout(() => textareaRef.current?.focus(), 0)
                    }
                  }}
                  placeholder={messages.length > 0 ? 'Add details, change preferences, or ask a question...' : 'Describe your dream trip...'}
                  rows={1}
                />
              {/* Button wrapper centers button vertically when textarea expands */}
              <div className="flex items-end pb-[10px] pr-4 flex-shrink-0">
              <button
                className="flex-shrink-0 h-9 w-9 rounded-full flex items-center justify-center transition-opacity hover:opacity-80"
                style={{
                  background: 'var(--color-accent)',
                  color: '#000000',
                  opacity: isStreaming ? 0.5 : 1,
                  cursor: isStreaming ? 'not-allowed' : 'pointer',
                }}
                disabled={isStreaming}
                type="submit"
                aria-label="Send"
                title="Send message"
              >
                <ArrowUp size={18} strokeWidth={2.5} />
              </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </motion.section>
  )
}
