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
  "Hi, I'm **Vela** — your travel planning companion.\n\nShare your destination, dates, trip length, who's traveling, budget, and the kind of trip you want. I'll start building an itinerary that fits."

export function Landing({ messages, input, isStreaming, liveNarration, error, onInputChange, onSubmit }: LandingProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom on every new message / narration
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, liveNarration, isStreaming])

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
              marginTop: '48px',
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
            {messages.map((message, index) => (
              <article
                key={`landing-${message.role}-${index}`}
                className={`rounded-lg text-sm leading-7 ${
                  message.role === 'user'
                    ? 'ml-6'
                    : 'mr-6 flex gap-3'
                }`}
                style={
                  message.role === 'user'
                    ? {
                        background: 'var(--bg-user)',
                        color: 'var(--color-text)',
                        padding: '16px',
                      }
                    : {
                        border: '1px solid var(--color-border)',
                        color: 'var(--color-text)',
                        padding: '20px',
                      }
                }
              >
                {message.role === 'user' ? (
                  <div className="whitespace-pre-line">{message.text}</div>
                ) : (
                  <>
                    <div className="flex-shrink-0 mt-0.5">
                      <img src="/vela-avatar.svg" alt="Vela" width={24} height={24} style={{ borderRadius: '50%' }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <MarkdownMessage text={message.text} />
                    </div>
                  </>
                )}
              </article>
            ))}

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

        {/* Input — 48px below onboarding/messages */}
        <div style={{ marginTop: '48px', paddingBottom: '48px' }}>
          <form onSubmit={onSubmit}>
            <div
              className="relative flex items-center rounded-lg"
              style={{
                background: 'var(--bg-input)',
                border: '1px solid var(--color-border)',
                padding: '24px',
              }}
            >
              {/* Custom thick blinking caret — visible when input is empty */}
              {!input && <div className="custom-caret" />}
              <textarea
                ref={textareaRef}
                className="flex-1 outline-none resize-none bg-transparent"
                style={{
                  color: 'var(--color-text)',
                  fontFamily: 'var(--font-editorial)',
                  fontSize: '1rem',
                  minHeight: '24px',
                  caretColor: input ? 'var(--color-accent)' : 'transparent',
                }}
                value={input}
                onChange={(event) => onInputChange(event.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    e.currentTarget.form?.requestSubmit()
                  }
                }}
                onBlur={() => {
                  // Re-focus after blur to keep cursor always visible
                  if (isInitial) {
                    setTimeout(() => textareaRef.current?.focus(), 0)
                  }
                }}
                placeholder={'"3 days in Paris, solo, love food and art, mid-range budget"'}
                rows={1}
              />
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
          </form>
        </div>
      </div>
    </motion.section>
  )
}
