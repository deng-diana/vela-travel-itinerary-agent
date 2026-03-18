import type { DayPlan, ItineraryDraft } from '../types'
import { DayItemCard, resolveVenue } from './DayItemCard'

export function DayCard({ day, itinerary }: { day: DayPlan; itinerary: ItineraryDraft }) {
  return (
    <article className="rounded-[22px] border border-slate-800 bg-slate-950 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-white">Day {day.day_number}</h3>
          <p className="mt-1 text-sm text-slate-400">{day.summary}</p>
        </div>
        <span className="text-xs uppercase tracking-[0.18em] text-emerald-300">{day.theme}</span>
      </div>

      <div className="mt-4 space-y-3">
        {day.items.map((item, index) => (
          <DayItemCard key={`${item.title}-${index}`} item={item} venue={resolveVenue(item, itinerary)} />
        ))}
      </div>
    </article>
  )
}
