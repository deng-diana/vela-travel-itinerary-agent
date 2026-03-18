import { useEffect, useRef } from 'react'
import type { FormEvent } from 'react'
import type { ChatMessage } from '../types'
import { MarkdownMessage } from './MarkdownMessage'
import { ThinkingDots } from './ThinkingDots'

type ChatPanelProps = {
  sessionId: string | null
  messages: ChatMessage[]
  steps: unknown[]  // passed to ItineraryPanel instead
  liveNarration: string
  isStreaming: boolean
  error: string | null
  input: string
  onInputChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

export function ChatPanel({
  messages,
  liveNarration,
  isStreaming,
  error,
  input,
  onInputChange,
  onSubmit,
}: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, liveNarration, isStreaming])

  const showThinking = isStreaming && !liveNarration

  return (
    <section className="flex min-h-[calc(100vh-2rem)] flex-col rounded-[32px] border border-slate-800 bg-slate-900/85 lg:sticky lg:top-4 lg:h-[calc(100vh-2rem)] self-start overflow-hidden">
      {/* Header */}
      <div className="border-b border-slate-800 px-5 py-4 flex-shrink-0">
        <h2 className="text-lg font-semibold tracking-[-0.03em] text-white">Vela</h2>
        <p className="mt-0.5 text-xs text-slate-500 uppercase tracking-widest">Travel planner</p>
      </div>

      {/* Messages — newest at bottom, auto-scroll */}
      <div className="flex-1 overflow-auto px-5 py-4">
        <div className="flex flex-col gap-3">
          {messages.map((message, index) => (
            <article
              key={`${message.role}-${index}`}
              className={`rounded-[20px] px-4 py-3 text-sm leading-7 ${
                message.role === 'user'
                  ? 'ml-4 bg-emerald-500/18 text-emerald-50'
                  : 'mr-4 border border-slate-700 bg-slate-950 text-slate-200'
              }`}
            >
              <div className="mb-1.5 text-[10px] uppercase tracking-[0.24em] text-slate-500">
                {message.role === 'user' ? 'You' : 'Vela'}
              </div>
              {message.role === 'assistant' ? (
                <MarkdownMessage text={message.text} />
              ) : (
                <div className="whitespace-pre-line">{message.text}</div>
              )}
            </article>
          ))}

          {/* Live narration at the bottom */}
          {liveNarration && (
            <div className="mr-4 rounded-[20px] border border-slate-700 bg-slate-950 px-4 py-3 text-sm leading-7 text-slate-300">
              <div className="mb-1.5 text-[10px] uppercase tracking-[0.24em] text-slate-500">Vela</div>
              {liveNarration}
            </div>
          )}

          {showThinking && <ThinkingDots />}

          {error && (
            <div className="rounded-2xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-slate-800 bg-slate-900/95 px-4 py-4 flex-shrink-0">
        <form onSubmit={onSubmit}>
          <div className="relative">
            <textarea
              className="min-h-20 w-full rounded-[20px] border border-slate-700 bg-slate-950 px-4 py-3 pr-12 text-sm text-slate-100 outline-none resize-none"
              value={input}
              onChange={(e) => onInputChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  e.currentTarget.form?.requestSubmit()
                }
              }}
              placeholder="Refine the trip, change the pace, add a preference…"
            />
            <button
              className="absolute bottom-2.5 right-2.5 flex h-8 w-8 items-center justify-center rounded-full bg-emerald-400 text-slate-950 transition-colors disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-500"
              disabled={isStreaming || !input.trim()}
              type="submit"
              aria-label="Send"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                <path d="M3.105 2.288a.75.75 0 0 0-.826.95l1.414 4.926A1.5 1.5 0 0 0 5.135 9.25h6.115a.75.75 0 0 1 0 1.5H5.135a1.5 1.5 0 0 0-1.442 1.086l-1.414 4.926a.75.75 0 0 0 .826.95l14.095-5.637a.75.75 0 0 0 0-1.4L3.105 2.288Z" />
              </svg>
            </button>
          </div>
        </form>
      </div>
    </section>
  )
}
