import type { WeatherSummary } from '../types'

export function WeatherStrip({ weather }: { weather: WeatherSummary | null | undefined }) {
  if (!weather) {
    return <p className="mt-4 text-sm text-slate-500">Waiting for live weather.</p>
  }

  return (
    <div className="space-y-3">
      <div className="text-lg font-semibold text-white">
        {weather.destination} {weather.avg_temp_c !== null ? `· ${weather.avg_temp_c}°C` : ''}
      </div>
      <p className="text-sm leading-6 text-slate-300">{weather.conditions_summary}</p>
      <div className="flex flex-wrap gap-2">
        {weather.packing_notes.map((note) => (
          <span key={note} className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs text-slate-300">
            {note}
          </span>
        ))}
      </div>
    </div>
  )
}
