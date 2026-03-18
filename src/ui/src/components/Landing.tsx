import type { FormEvent } from 'react'
import { motion } from 'motion/react'
import type { ChatMessage } from '../types'
import { MarkdownMessage } from './MarkdownMessage'
import { TypewriterText } from './TypewriterText'

type LandingProps = {
  messages: ChatMessage[]
  input: string
  isStreaming: boolean
  liveNarration: string
  error: string | null
  onInputChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

export function Landing({ messages, input, isStreaming, liveNarration, error, onInputChange, onSubmit }: LandingProps) {
  const placeholder =
    messages.length === 0
      ? 'Where do you want to go, how long is the trip, and what matters most?'
      : 'Continue with the details above. You can reply with just the parts you already know.'
  const buttonLabel = messages.length === 0 ? 'Start planning' : 'Continue'

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
          <div className="flex-1 overflow-auto px-5 py-5 lg:px-6 lg:py-6">
            <div className="space-y-3">
              {liveNarration ? (
                <div className="rounded-[20px] border border-slate-800 bg-slate-900/70 px-4 py-4 text-sm leading-7 text-slate-200">
                  <TypewriterText text={liveNarration} animate={isStreaming} />
                </div>
              ) : null}

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

              {error ? (
                <div className="rounded-2xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                  {error}
                </div>
              ) : null}
            </div>
          </div>

          <div className="border-t border-white/10 px-5 py-5 lg:px-6 lg:py-6">
            <form className="space-y-4" onSubmit={onSubmit}>
              <textarea
                className="min-h-40 w-full rounded-[24px] border border-slate-800 bg-slate-950 px-5 py-4 text-base text-slate-100 outline-none"
                value={input}
                onChange={(event) => onInputChange(event.target.value)}
                placeholder={placeholder}
              />
              <div className="flex items-center justify-end">
                <button
                  className="rounded-[20px] bg-emerald-400 px-6 py-3 font-medium text-slate-950 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
                  disabled={isStreaming || !input.trim()}
                  type="submit"
                >
                  {buttonLabel}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </motion.section>
  )
}
