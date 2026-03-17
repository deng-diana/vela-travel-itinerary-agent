import { Compass, CloudSun, Hotel, Sparkles, UtensilsCrossed } from 'lucide-react'

const conversation = [
  {
    role: 'user',
    text: "I'm going to Tokyo for 6 days in August. Mid-range budget, really into food and hidden gems. Travelling as a couple.",
  },
  {
    role: 'assistant',
    text: 'Great start. I can shape this into a live itinerary. Before I do, I need your preferred neighborhood, hotel style, and whether either of you has dietary restrictions.',
  },
]

const activity = [
  'Parsing trip intent',
  'Checking seasonal weather in August',
  'Shortlisting stays near Shibuya and Shinjuku',
  'Mapping food-led experiences with lighter pacing',
]

const days = [
  {
    title: 'Day 1',
    theme: 'Arrival + slow evening',
    items: ['Check into selected stay', 'Golden Gai dinner lane', 'Late-night jazz bar'],
  },
  {
    title: 'Day 2',
    theme: 'Markets + hidden food spots',
    items: ['Morning coffee in Kiyosumi', 'Chef-led food crawl', 'Riverside walk at sunset'],
  },
]

function App() {
  return (
    <main className="min-h-screen bg-[var(--bg)] text-[var(--text-primary)]">
      <div className="mx-auto flex min-h-screen max-w-[1600px] flex-col px-4 py-4 lg:px-6 lg:py-6">
        <div className="relative overflow-hidden rounded-[28px] border border-white/10 bg-[var(--panel)] shadow-[0_30px_120px_rgba(3,8,16,0.45)]">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(123,211,194,0.14),transparent_28%),radial-gradient(circle_at_top_right,rgba(244,178,97,0.12),transparent_24%),linear-gradient(180deg,rgba(255,255,255,0.03),rgba(255,255,255,0))]" />

          <header className="relative flex items-center justify-between border-b border-white/10 px-5 py-4 lg:px-8">
            <div>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/6">
                  <Compass className="h-5 w-5 text-[var(--accent)]" />
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.32em] text-[var(--text-muted)]">
                    Vela
                  </p>
                  <h1 className="text-lg font-semibold tracking-[-0.03em] text-white">
                    Live Itinerary Studio
                  </h1>
                </div>
              </div>
            </div>

            <div className="hidden items-center gap-3 lg:flex">
              <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1 text-xs text-emerald-100">
                Agent online
              </span>
              <span className="rounded-full border border-white/10 bg-white/6 px-3 py-1 text-xs text-[var(--text-muted)]">
                Tokyo / 6 days
              </span>
            </div>
          </header>

          <section className="relative grid min-h-[820px] grid-cols-1 lg:grid-cols-[420px_minmax(0,1fr)]">
            <aside className="border-b border-white/10 bg-[rgba(7,14,24,0.72)] lg:border-b-0 lg:border-r lg:border-white/10">
              <div className="flex h-full flex-col">
                <div className="border-b border-white/10 px-5 py-5 lg:px-6">
                  <p className="text-xs uppercase tracking-[0.28em] text-[var(--text-muted)]">
                    Conversation
                  </p>
                  <p className="mt-2 max-w-sm text-sm leading-6 text-[var(--text-secondary)]">
                    The agent asks before acting, shows progress, and keeps the plan adaptable.
                  </p>
                </div>

                <div className="flex-1 space-y-4 px-5 py-5 lg:px-6">
                  {conversation.map((message) => (
                    <div
                      key={`${message.role}-${message.text.slice(0, 12)}`}
                      className={
                        message.role === 'user'
                          ? 'ml-8 rounded-[24px] rounded-tr-md bg-[var(--bubble-user)] px-4 py-4 text-sm leading-6 text-white'
                          : 'mr-6 rounded-[24px] rounded-tl-md border border-white/10 bg-white/5 px-4 py-4 text-sm leading-6 text-[var(--text-secondary)]'
                      }
                    >
                      <div className="mb-2 text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">
                        {message.role === 'user' ? 'Traveller' : 'Vela'}
                      </div>
                      {message.text}
                    </div>
                  ))}
                </div>

                <div className="border-t border-white/10 px-5 py-5 lg:px-6">
                  <div className="rounded-[24px] border border-white/10 bg-black/20 p-4">
                    <div className="mb-3 flex items-center justify-between">
                      <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">
                        Agent activity
                      </p>
                      <Sparkles className="h-4 w-4 text-[var(--accent-warm)]" />
                    </div>
                    <div className="space-y-3">
                      {activity.map((item) => (
                        <div key={item} className="flex items-center gap-3 text-sm text-[var(--text-secondary)]">
                          <span className="h-2 w-2 rounded-full bg-[var(--accent)]" />
                          <span>{item}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </aside>

            <section className="bg-[rgba(9,17,29,0.78)] px-5 py-5 lg:px-7">
              <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_320px]">
                <div className="space-y-4">
                  <div className="rounded-[26px] border border-white/10 bg-[var(--card-strong)] p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-xs uppercase tracking-[0.28em] text-[var(--text-muted)]">
                          Seasonal brief
                        </p>
                        <div className="mt-3 flex items-center gap-3">
                          <CloudSun className="h-9 w-9 text-[var(--accent)]" />
                          <div>
                            <h2 className="text-xl font-semibold tracking-[-0.04em] text-white">
                              Tokyo in August
                            </h2>
                            <p className="mt-1 text-sm text-[var(--text-secondary)]">
                              Warm, humid, occasional rainfall. Plan shaded walks, slower afternoons, and breathable layers.
                            </p>
                          </div>
                        </div>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-right">
                        <p className="text-xs uppercase tracking-[0.22em] text-[var(--text-muted)]">Avg temp</p>
                        <p className="mt-1 text-2xl font-semibold text-white">29°C</p>
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
                      <div className="mb-4 flex items-center gap-3">
                        <Hotel className="h-5 w-5 text-[var(--accent)]" />
                        <p className="text-sm font-medium text-white">Selected stay</p>
                      </div>
                      <h3 className="text-lg font-semibold text-white">Aoyama Terrace Hotel</h3>
                      <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                        Mid-range boutique stay with calm interiors, strong food access, and easy evening movement.
                      </p>
                      <div className="mt-4 flex items-center justify-between">
                        <span className="text-sm text-[var(--text-muted)]">$220/night</span>
                        <button className="rounded-full bg-[var(--accent-warm)] px-4 py-2 text-sm font-medium text-slate-950">
                          Book stay
                        </button>
                      </div>
                    </article>

                    <article className="rounded-[24px] border border-white/10 bg-white/5 p-5">
                      <div className="mb-4 flex items-center gap-3">
                        <UtensilsCrossed className="h-5 w-5 text-[var(--accent-warm)]" />
                        <p className="text-sm font-medium text-white">Dining direction</p>
                      </div>
                      <h3 className="text-lg font-semibold text-white">Food-led hidden gems</h3>
                      <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                        Low-tourist neighborhoods, chef counters, kissaten mornings, and one memorable late-night spot.
                      </p>
                      <div className="mt-4 text-sm text-[var(--text-muted)]">
                        8 candidate venues shortlisted
                      </div>
                    </article>
                  </div>

                  <div className="rounded-[28px] border border-white/10 bg-[var(--card-soft)] p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs uppercase tracking-[0.28em] text-[var(--text-muted)]">
                          Day by day
                        </p>
                        <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-white">
                          Itinerary taking shape
                        </h2>
                      </div>
                      <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-[var(--text-muted)]">
                        live draft
                      </div>
                    </div>

                    <div className="mt-5 grid gap-4 lg:grid-cols-2">
                      {days.map((day) => (
                        <article key={day.title} className="rounded-[24px] border border-white/10 bg-black/15 p-4">
                          <div className="flex items-center justify-between">
                            <h3 className="text-lg font-semibold text-white">{day.title}</h3>
                            <span className="text-xs uppercase tracking-[0.22em] text-[var(--accent)]">
                              {day.theme}
                            </span>
                          </div>
                          <div className="mt-4 space-y-3">
                            {day.items.map((item) => (
                              <div
                                key={item}
                                className="rounded-2xl border border-white/8 bg-white/5 px-3 py-3 text-sm text-[var(--text-secondary)]"
                              >
                                {item}
                              </div>
                            ))}
                          </div>
                        </article>
                      ))}
                    </div>
                  </div>
                </div>

                <aside className="space-y-4">
                  <div className="rounded-[24px] border border-white/10 bg-white/5 p-5">
                    <p className="text-xs uppercase tracking-[0.28em] text-[var(--text-muted)]">
                      Route logic
                    </p>
                    <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
                      Days are being grouped by neighborhood to reduce transit drag and keep evenings flexible.
                    </p>
                  </div>

                  <div className="rounded-[24px] border border-white/10 bg-[linear-gradient(180deg,rgba(244,178,97,0.18),rgba(255,255,255,0.04))] p-5">
                    <p className="text-xs uppercase tracking-[0.28em] text-[var(--text-muted)]">
                      Next question
                    </p>
                    <h3 className="mt-3 text-xl font-semibold tracking-[-0.04em] text-white">
                      Do you want a quieter boutique stay, or something more central and energetic?
                    </h3>
                    <div className="mt-5 flex flex-wrap gap-3">
                      <button className="rounded-full border border-white/10 bg-white px-4 py-2 text-sm font-medium text-slate-900">
                        Quiet boutique
                      </button>
                      <button className="rounded-full border border-white/10 bg-transparent px-4 py-2 text-sm font-medium text-white">
                        Central energy
                      </button>
                    </div>
                  </div>
                </aside>
              </div>
            </section>
          </section>
        </div>
      </div>
    </main>
  )
}

export default App
