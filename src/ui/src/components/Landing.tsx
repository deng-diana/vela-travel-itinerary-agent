import { useEffect, useRef } from 'react'
import type { FormEvent } from 'react'
import { motion } from 'motion/react'
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
  "Hi, I'm **Vela** — your travel planning companion.\n\nTell me where you'd like to go, how many days you have, and what matters most to you (food, culture, hidden gems, relaxation…), and I'll start building your itinerary right away."

export function Landing({ messages, input, isStreaming, liveNarration, error, onInputChange, onSubmit }: LandingProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on every new message / narration
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, liveNarration, isStreaming])

  const placeholder =
    messages.length === 0
      ? 'e.g. "3 days in Paris, solo, love food and art, mid budget"'
      : 'Add more details or answer the question above…'

  const showThinking = isStreaming && !liveNarration

  return (
    <motion.section
      key="landing"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -18 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className="mx-auto flex min-h-screen max-w-6xl items-center justify-center px-5 py-10"
    >
      <div className="w-full max-w-4xl rounded-[40px] border border-white/10 bg-[linear-gradient(180deg,rgba(16,27,43,0.9),rgba(8,16,27,0.92))] p-8 shadow-[0_30px_120px_rgba(3,8,16,0.45)] lg:p-12">
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="text-6xl font-semibold tracking-[-0.07em] text-white lg:text-8xl">Vela</h1>
          <p className="mx-auto mt-6 max-w-2xl text-xl leading-9 text-slate-300 lg:text-2xl">
            A warmer way to turn a travel idea into a trip that feels thoughtful, useful, and deeply your own.
          </p>
        </div>

        <div className="mx-auto mt-10 flex min-h-[620px] max-w-3xl flex-col rounded-[32px] border border-white/10 bg-slate-950/70">
          {/* Messages area — newest always at bottom */}
          <div className="flex-1 overflow-auto px-5 py-5 lg:px-6 lg:py-6">
            <div className="flex flex-col gap-3">

              {/* Welcome message — only when no conversation yet */}
              {messages.length === 0 && !liveNarration && !isStreaming && (
                <article className="mr-6 rounded-[22px] border border-slate-700 bg-slate-950 px-4 py-4 text-sm leading-7 text-slate-200">
                  <div className="mb-2 text-[11px] uppercase tracking-[0.24em] text-slate-400">Vela</div>
                  <MarkdownMessage text={WELCOME_MESSAGE} />
                </article>
              )}

              {/* All committed messages in chronological order */}
              {messages.map((message, index) => (
                <article
                  key={`landing-${message.role}-${index}`}
                  className={`rounded-[22px] px-4 py-4 text-sm leading-7 ${
                    message.role === 'user'
                      ? 'ml-6 bg-emerald-500/18 text-emerald-50'
                      : 'mr-6 border border-slate-700 bg-slate-950 text-slate-200'
                  }`}
                >
                  <div className="mb-2 text-[11px] uppercase tracking-[0.24em] text-slate-400">
                    {message.role === 'user' ? 'You' : 'Vela'}
                  </div>
                  {message.role === 'assistant' ? (
                    <MarkdownMessage text={message.text} />
                  ) : (
                    <div className="whitespace-pre-line">{message.text}</div>
                  )}
                </article>
              ))}

              {/* Live narration — always at the bottom */}
              {liveNarration && (
                <div className="mr-6 rounded-[20px] border border-slate-700 bg-slate-950 px-4 py-4 text-sm leading-7 text-slate-200">
                  <div className="mb-2 text-[11px] uppercase tracking-[0.24em] text-slate-400">Vela</div>
                  {liveNarration}
                </div>
              )}

              {showThinking && <ThinkingDots />}

              {error && (
                <div className="rounded-2xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                  {error}
                </div>
              )}

              {/* Scroll anchor */}
              <div ref={bottomRef} />
            </div>
          </div>

          {/* Input */}
          <div className="border-t border-white/10 px-5 py-5 lg:px-6 lg:py-6">
            <form onSubmit={onSubmit}>
              <div className="relative">
                <textarea
                  className="min-h-28 w-full rounded-[24px] border border-slate-800 bg-slate-950 px-5 py-4 pr-16 text-base text-slate-100 outline-none resize-none"
                  value={input}
                  onChange={(event) => onInputChange(event.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      e.currentTarget.form?.requestSubmit()
                    }
                  }}
                  placeholder={placeholder}
                />
                <button
                  className="absolute bottom-3 right-3 flex h-10 w-10 items-center justify-center rounded-full bg-emerald-400 text-slate-950 transition-colors disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-500"
                  disabled={isStreaming || !input.trim()}
                  type="submit"
                  aria-label="Send"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
                    <path d="M3.105 2.288a.75.75 0 0 0-.826.95l1.414 4.926A1.5 1.5 0 0 0 5.135 9.25h6.115a.75.75 0 0 1 0 1.5H5.135a1.5 1.5 0 0 0-1.442 1.086l-1.414 4.926a.75.75 0 0 0 .826.95l14.095-5.637a.75.75 0 0 0 0-1.4L3.105 2.288Z" />
                  </svg>
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </motion.section>
  )
}
