import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { AgentStep, ChatMessage } from '../types'
import { MarkdownMessage } from './MarkdownMessage'
import { TypewriterText } from './TypewriterText'

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

export function ChatPanel({
  sessionId,
  messages,
  steps,
  liveNarration,
  isStreaming,
  error,
  input,
  onInputChange,
  onSubmit,
}: ChatPanelProps) {
  const [showHistory, setShowHistory] = useState(false)
  const [showConversationHistory, setShowConversationHistory] = useState(false)
  const transcriptEndRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, liveNarration, steps])

  const activeStep = [...steps].reverse().find((step) => step.status === 'active') ?? null
  const completedSteps = steps.filter((step) => step.status === 'completed').slice().reverse()
  const visibleMessages = showConversationHistory ? messages : messages.slice(-2)
  const hiddenMessageCount = Math.max(messages.length - visibleMessages.length, 0)

  return (
    <section className="flex min-h-[calc(100vh-2rem)] flex-col rounded-[32px] border border-slate-800 bg-slate-900/85 lg:sticky lg:top-4 lg:h-[calc(100vh-2rem)] self-start overflow-hidden">
      <div className="border-b border-slate-800 px-5 py-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Vela</p>
            <h2 className="mt-2 text-xl font-semibold tracking-[-0.04em] text-white">Planning in motion</h2>
          </div>
          <div className="rounded-full border border-slate-800 bg-slate-950 px-3 py-1 text-xs text-slate-400">
            {sessionId ? 'session live' : 'new session'}
          </div>
        </div>
      </div>

      <div className="border-b border-slate-800 px-5 py-5">
        <div className="rounded-[24px] border border-slate-800 bg-slate-950 px-4 py-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Agent</p>
              <p className="mt-1 text-sm font-medium text-white">
                {activeStep ? activeStep.title : isStreaming ? 'Thinking' : 'Ready'}
              </p>
            </div>
            <span
              className={`rounded-full px-3 py-1 text-[11px] uppercase tracking-[0.2em] ${
                isStreaming ? 'bg-emerald-400/15 text-emerald-200 agent-shimmer' : 'bg-slate-800 text-slate-400'
              }`}
            >
              {isStreaming ? 'Live' : 'Idle'}
            </span>
          </div>

          <div className="mt-4 min-h-20 rounded-[18px] border border-slate-800 bg-slate-900/70 px-3 py-3 text-sm leading-6 text-slate-200">
            <TypewriterText
              text={liveNarration || activeStep?.detail || 'Waiting for the next trip request.'}
              animate={isStreaming}
            />
          </div>

          <div className="mt-4">
            <button
              className="text-xs uppercase tracking-[0.22em] text-slate-400"
              onClick={() => setShowHistory((current) => !current)}
              type="button"
            >
              {showHistory ? 'Hide' : 'Show'} completed steps ({completedSteps.length})
            </button>

            {showHistory ? (
              <div className="mt-3 space-y-2">
                {completedSteps.length ? (
                  completedSteps.map((step) => (
                    <div key={step.id} className="rounded-2xl border border-slate-800 px-3 py-3 text-sm">
                      <div className="font-medium text-slate-100">{step.title}</div>
                      <div className="mt-1 text-slate-400">{step.detail}</div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-slate-500">Completed steps will appear here.</div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-hidden px-5 py-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Conversation</p>
            <p className="mt-1 text-sm text-slate-400">Current exchange and planning feedback.</p>
          </div>
          {messages.length > 2 ? (
            <button
              className="rounded-full border border-slate-800 bg-slate-950 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-slate-400"
              onClick={() => setShowConversationHistory((current) => !current)}
              type="button"
            >
              {showConversationHistory ? 'Hide history' : `Show history (${hiddenMessageCount})`}
            </button>
          ) : null}
        </div>

        <div className="h-full overflow-auto">
          <div className="space-y-3 pb-4">
            {visibleMessages.map((message, index) => (
              <article
                key={`${message.role}-${index}`}
                className={`rounded-[24px] px-4 py-4 text-sm leading-7 ${
                  message.role === 'user'
                    ? 'ml-6 bg-emerald-500/18 text-emerald-50'
                    : 'mr-4 border border-slate-700 bg-slate-950 text-slate-200'
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
            <div ref={transcriptEndRef} />
          </div>
        </div>
      </div>

      <div className="border-t border-slate-800 bg-slate-900/95 px-5 py-5">
        <form className="space-y-3" onSubmit={onSubmit}>
          <textarea
            className="min-h-28 w-full rounded-[24px] border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none"
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            placeholder="Refine the trip, change the pace, or add a new preference..."
          />
          <div className="flex items-center justify-end gap-3">
            <button
              className="rounded-[18px] bg-emerald-400 px-5 py-3 font-medium text-slate-950 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
              disabled={isStreaming || !input.trim()}
              type="submit"
            >
              {isStreaming ? 'Planning...' : 'Send'}
            </button>
          </div>
        </form>

        {error ? (
          <div className="mt-4 rounded-2xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        ) : null}
      </div>
    </section>
  )
}
