import type { HotelOption } from '../types'
import { buildPhotoUrl } from '../types'

export function HotelGallery({ hotels, selectedHotel }: { hotels: HotelOption[]; selectedHotel?: HotelOption | null }) {
  if (!hotels.length) return null

  return (
    <div className="rounded-[24px] border border-slate-800 bg-slate-900/70 p-5">
      <div className="text-xs uppercase tracking-[0.22em] text-slate-400">Stay Options</div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {hotels.map((hotel) => {
          const isSelected = selectedHotel?.id === hotel.id
          const photoUrl = buildPhotoUrl(hotel.photo_name)
          const href = hotel.maps_url || hotel.affiliate_link

          return (
            <article
              key={hotel.id}
              className={`overflow-hidden rounded-[18px] border transition-all ${
                isSelected
                  ? 'border-emerald-500/50 bg-emerald-500/5 shadow-[0_0_20px_rgba(123,211,194,0.08)]'
                  : 'border-slate-800 bg-slate-950 hover:border-slate-700'
              }`}
            >
              {photoUrl ? (
                <div className="aspect-[16/10] w-full bg-slate-900">
                  <img className="h-full w-full object-cover" src={photoUrl} alt={hotel.name} loading="lazy" />
                </div>
              ) : (
                <div className="flex aspect-[16/10] w-full items-center justify-center bg-slate-900/50 text-sm text-slate-600">
                  No photo
                </div>
              )}

              <div className="space-y-2 px-4 py-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="text-sm font-medium text-slate-100">{hotel.name}</div>
                  {isSelected && (
                    <span className="shrink-0 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] uppercase tracking-[0.16em] text-emerald-300">
                      Selected
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-400">
                  {hotel.neighborhood} · {hotel.category} · ${hotel.nightly_rate_usd}/night
                </div>
                {hotel.key_highlights?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {hotel.key_highlights.slice(0, 3).map((highlight) => (
                      <span key={highlight} className="rounded-full border border-slate-800 px-2 py-0.5 text-[10px] text-slate-400">
                        {highlight}
                      </span>
                    ))}
                  </div>
                )}
                {href && (
                  <a
                    className="mt-1 inline-block rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs uppercase tracking-[0.14em] text-slate-200 transition-colors hover:border-slate-600 hover:text-white"
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                  >
                    View stay
                  </a>
                )}
              </div>
            </article>
          )
        })}
      </div>
    </div>
  )
}
