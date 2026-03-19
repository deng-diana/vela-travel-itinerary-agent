import { useEffect, useRef, useState, memo, useCallback } from 'react'
import type { FormEvent } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { ArrowUp, CheckCircle2, ChevronDown, Check, ChevronLeft } from 'lucide-react'
import type { ChatMessage, AgentStep } from '../types'
import { MarkdownMessage } from './MarkdownMessage'

// ---------------------------------------------------------------------------
// Typewriter hook — reveals text character by character
// ---------------------------------------------------------------------------

function useTypewriter(text: string, speed = 18): { displayed: string; done: boolean } {
  const [charIndex, setCharIndex] = useState(0)
  const [done, setDone] = useState(false)

  useEffect(() => {
    setCharIndex(0)
    setDone(false)
  }, [text])

  useEffect(() => {
    if (charIndex >= text.length) {
      setDone(true)
      return
    }
    const timer = setTimeout(() => {
      // Skip ahead for spaces and punctuation to feel more natural
      const ch = text[charIndex]
      const skip = ch === ' ' || ch === '\n' ? 2 : 1
      setCharIndex((prev) => Math.min(prev + skip, text.length))
    }, speed)
    return () => clearTimeout(timer)
  }, [charIndex, text, speed])

  return { displayed: text.slice(0, charIndex), done }
}

type ChatPanelProps = {
  sessionId: string | null
  messages: ChatMessage[]
  steps: AgentStep[]
  liveNarration: string
  isStreaming: boolean
  error: string | null
  input: string
  onInputChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

export const ChatPanel = memo(function ChatPanel({
  messages,
  steps,
  liveNarration,
  isStreaming,
  error,
  input,
  onInputChange,
  onSubmit,
}: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, liveNarration, isStreaming, steps])

  // Reset textarea height when input is cleared (e.g., after submit)
  useEffect(() => {
    if (!input && textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [input])

  // Split messages: show tool steps BEFORE the last assistant message
  const hasSteps = steps.length > 0
  const lastMsg = messages[messages.length - 1]
  const lastIsAssistant = lastMsg?.role === 'assistant'
  const messagesBeforeFinal = hasSteps && lastIsAssistant && !isStreaming
    ? messages.slice(0, -1)
    : messages
  const finalAssistantMsg = hasSteps && lastIsAssistant && !isStreaming
    ? lastMsg
    : null

  return (
    <section
      className="flex h-screen flex-col overflow-hidden"
      style={{
        borderRight: '1px solid var(--story-border)',
        background: 'var(--story-bg)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center px-4 py-4 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--story-border)' }}
      >
        <button
          onClick={() => window.location.href = '/'}
          className="flex-shrink-0 rounded-lg p-1 transition-opacity hover:opacity-70"
          style={{ color: 'var(--story-text)' }}
          aria-label="Back to home"
        >
          <ChevronLeft size={18} strokeWidth={2} />
        </button>
        <img
          src="/logo.svg"
          alt="Vela"
          width={24}
          height={24}
          style={{ flexShrink: 0, marginLeft: '4px' }}
        />
        <h2
          className="text-base tracking-[-0.02em]"
          style={{ color: 'var(--story-text)', fontFamily: 'var(--font-editorial)', fontWeight: 400, marginLeft: '6px' }}
        >
          Vela
        </h2>
      </div>

      {/* Messages */}
      <div className="messages-area flex-1 overflow-auto px-5 py-4">
        <div className="flex flex-col gap-3">
          {messagesBeforeFinal.map((message, index) =>
            message.role === 'user' ? (
              <div key={`user-${index}`} className="flex justify-end mb-4">
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
                key={`assistant-${index}`}
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

          {/* Tool Steps — live chain shown BEFORE final assistant message */}
          {steps.length > 0 && (
            <ToolChain steps={steps} isStreaming={isStreaming} />
          )}

          {/* Final assistant message — rendered AFTER tool steps with typewriter */}
          {finalAssistantMsg && (
            <TypewriterAssistantMessage text={finalAssistantMsg.text} />
          )}

          {/* Thinking dots — only before any steps or narration */}
          {isStreaming && steps.length === 0 && !liveNarration && (
            <div
              className="mr-6 flex items-center gap-3 rounded-2xl px-4 py-4"
              style={{ border: '1px solid var(--story-border)', background: 'var(--story-bg)' }}
            >
              <img src="/vela-avatar.svg" alt="Vela" width={24} height={24} style={{ borderRadius: '50%', flexShrink: 0 }} />
              <div className="flex items-center gap-1.5">
                <span className="thinking-dot h-2 w-2 rounded-full" style={{ background: 'var(--story-text-muted)', animationDelay: '0ms' }} />
                <span className="thinking-dot h-2 w-2 rounded-full" style={{ background: 'var(--story-text-muted)', animationDelay: '150ms' }} />
                <span className="thinking-dot h-2 w-2 rounded-full" style={{ background: 'var(--story-text-muted)', animationDelay: '300ms' }} />
              </div>
            </div>
          )}

          {error && (
            <div
              className="rounded-2xl px-4 py-3 text-sm"
              style={{ border: '1px solid rgba(239,68,68,0.3)', background: 'rgba(239,68,68,0.08)', color: '#fca5a5' }}
            >
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input — consistent with Landing page style */}
      <div
        className="px-5 py-4 flex-shrink-0"
        style={{ borderTop: '1px solid var(--color-border)' }}
      >
        <form onSubmit={onSubmit}>
          <div
            className="relative flex items-end rounded-lg"
            style={{
              background: 'var(--bg-input)',
              border: '1px solid var(--color-border)',
              padding: '16px 24px',
            }}
          >
            <div className="relative flex-1">
              {/* Custom thick blinking caret — visible when input is empty */}
              {!input && <div className="custom-caret" style={{ position: 'absolute', left: 0, top: '12px' }} />}
              <textarea
                ref={textareaRef}
                className="w-full outline-none resize-none bg-transparent"
                style={{
                  color: 'var(--color-text)',
                  fontFamily: 'var(--font-editorial)',
                  fontSize: '1rem',
                  minHeight: '24px',
                  maxHeight: '160px',
                  overflowY: 'auto',
                  lineHeight: '1.5',
                  caretColor: input ? 'var(--color-accent)' : 'transparent',
                }}
              value={input}
              onChange={(e) => {
                onInputChange(e.target.value)
                // Auto-resize: reset height to auto, then set to scrollHeight
                const el = e.target
                el.style.height = 'auto'
                el.style.height = Math.min(el.scrollHeight, 160) + 'px'
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  e.currentTarget.form?.requestSubmit()
                  // Reset height after submit
                  if (textareaRef.current) {
                    textareaRef.current.style.height = 'auto'
                  }
                }
              }}
              placeholder="Refine the trip, change the pace, add a preference..."
              rows={1}
            />
            </div>
            <button
              className="flex-shrink-0 h-9 w-9 rounded-full flex items-center justify-center transition-opacity hover:opacity-80 mb-[2px]"
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
    </section>
  )
})

// ---------------------------------------------------------------------------
// Typewriter assistant message — reveals text like typing
// ---------------------------------------------------------------------------

function TypewriterAssistantMessage({ text }: { text: string }) {
  const { displayed, done } = useTypewriter(text, 15)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll as text reveals
  useEffect(() => {
    if (!done) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [displayed, done])

  return (
    <article
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
        <MarkdownMessage text={displayed} />
        {!done && (
          <span
            className="inline-block ml-0.5"
            style={{
              width: '2px',
              height: '1em',
              background: 'var(--color-accent)',
              animation: 'caret-blink 1s ease-in-out infinite',
              verticalAlign: 'text-bottom',
            }}
          />
        )}
      </div>
      <div ref={bottomRef} />
    </article>
  )
}

// ---------------------------------------------------------------------------
// Tool Chain — ChatGPT-style live chain of tool calls
// Shows each step inline as it happens. Collapses when done.
// ---------------------------------------------------------------------------

function buildToolSummary(completedSteps: AgentStep[]): string {
  const toolNames = completedSteps.map((s) => s.id.replace(/-completed-\d+$/, ''))

  const parts: string[] = []
  const toolCount = toolNames.filter(
    (n) => !['analyze_preferences', 'plan_research', 'write_summary'].includes(n)
  ).length

  // Count data sources
  const dataTools = ['get_weather', 'get_hotels', 'get_restaurants', 'get_experiences']
  const dataCount = dataTools.filter((t) => toolNames.includes(t)).length

  if (dataCount > 0) {
    parts.push(`queried ${dataCount} data sources`)
  }

  if (toolNames.includes('get_daily_structure')) {
    parts.push('built day-by-day plan')
  }

  if (toolNames.includes('estimate_budget')) {
    parts.push('estimated costs')
  }

  if (toolNames.includes('get_packing_suggestions')) {
    parts.push('prepared packing list')
  }

  const prefix = `Ran ${toolCount} tools`
  return parts.length > 0 ? `${prefix} · ${parts.join(', ')}` : `Ran ${toolCount} tools`
}

function ToolChain({ steps, isStreaming }: { steps: AgentStep[]; isStreaming: boolean }) {
  const [collapsed, setCollapsed] = useState(false)

  const completedSteps = steps.filter((s) => s.status === 'completed')
  const activeStep = steps.find((s) => s.status === 'active')
  const allDone = !activeStep && completedSteps.length > 0 && !isStreaming

  const summary = allDone ? buildToolSummary(completedSteps) : ''

  // Auto-collapse when streaming ends
  const wasStreaming = useRef(isStreaming)
  useEffect(() => {
    if (wasStreaming.current && !isStreaming && !activeStep) {
      setCollapsed(true)
    }
    wasStreaming.current = isStreaming
  }, [isStreaming, activeStep])

  const cardStyle: React.CSSProperties = {
    background: '#1C2210',
    borderRadius: '12px',
    padding: '12px 16px',
  }

  return (
    <div className="mb-2">
      {/* Collapsed summary — click to expand */}
      {collapsed && allDone && (
        <button
          onClick={() => setCollapsed(false)}
          className="flex items-start gap-2.5 py-3 px-4 text-left w-full group"
          style={cardStyle}
        >
          <CheckCircle2 className="h-4 w-4 flex-shrink-0 mt-[1px]" style={{ color: 'var(--color-accent)' }} />
          <span
            className="flex-1 text-xs leading-5"
            style={{
              fontFamily: 'var(--font-data)',
              letterSpacing: '0.02em',
              color: 'var(--color-text-muted)',
            }}
          >
            {summary}
          </span>
          <ChevronDown
            className="h-3.5 w-3.5 flex-shrink-0 mt-[1px] transition-opacity opacity-40 group-hover:opacity-80"
            style={{ color: 'var(--color-text-muted)' }}
          />
        </button>
      )}

      {/* Expanded chain — visible during streaming or when expanded */}
      {!collapsed && (
        <div style={cardStyle}>
          {/* Collapse header when done */}
          {allDone && (
            <button
              onClick={() => setCollapsed(true)}
              className="flex items-start gap-2.5 text-left w-full mb-2 pb-2"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
            >
              <CheckCircle2 className="h-4 w-4 flex-shrink-0 mt-[1px]" style={{ color: 'var(--color-accent)' }} />
              <span
                className="flex-1 text-xs leading-5"
                style={{
                  fontFamily: 'var(--font-data)',
                  letterSpacing: '0.02em',
                  color: 'var(--color-text-muted)',
                }}
              >
                {summary}
              </span>
              <ChevronDown
                className="h-3.5 w-3.5 flex-shrink-0 mt-[1px]"
                style={{ color: 'var(--color-text-muted)', transform: 'rotate(180deg)' }}
              />
            </button>
          )}

          {/* Each step as a single line */}
          {completedSteps.map((step) => (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
              className="flex items-start gap-2.5 py-1"
            >
              <motion.div
                className="flex-shrink-0 mt-[2px]"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 400, damping: 15 }}
              >
                <Check className="h-3.5 w-3.5" style={{ color: 'var(--color-accent)' }} />
              </motion.div>
              <span
                className="text-xs leading-5"
                style={{
                  fontFamily: 'var(--font-data)',
                  letterSpacing: '0.02em',
                  color: 'var(--color-text-muted)',
                }}
              >
                {step.title}
              </span>
            </motion.div>
          ))}

          {/* Active step with wave dots */}
          <AnimatePresence>
            {activeStep && (
              <motion.div
                key={activeStep.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="flex items-start gap-2.5 py-1"
              >
                <span className="flex items-center gap-[3px] h-3.5 w-3.5 flex-shrink-0 justify-center mt-[2px]">
                  <span className="thinking-dot h-[4px] w-[4px] rounded-full" style={{ background: 'var(--color-accent)', animationDelay: '0ms' }} />
                  <span className="thinking-dot h-[4px] w-[4px] rounded-full" style={{ background: 'var(--color-accent)', animationDelay: '150ms' }} />
                  <span className="thinking-dot h-[4px] w-[4px] rounded-full" style={{ background: 'var(--color-accent)', animationDelay: '300ms' }} />
                </span>
                <span
                  className="text-xs leading-5 active-step-shimmer"
                  style={{
                    fontFamily: 'var(--font-data)',
                    letterSpacing: '0.02em',
                  }}
                >
                  {activeStep.title}
                </span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  )
}
