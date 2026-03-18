import type { DayItem, ItineraryDraft } from '../types'
import { buildPhotoUrl } from '../types'

export type ResolvedVenue = {
  title: string
  subtitle: string
  href?: string | null
  photoName?: string | null
  attribution?: string | null
  ctaLabel: string
}

export function resolveVenue(item: DayItem, itinerary: ItineraryDraft): ResolvedVenue | null {
  const hotel = itinerary.hotels.find(
    (entry) =>
      sameVenueTitle(entry.name, item.title) || sameVenueLink(entry.maps_url || entry.affiliate_link, item.booking_link),
  )
  if (hotel) {
    return {
      title: hotel.name,
      subtitle: `${hotel.neighborhood} · ${hotel.category} · $${hotel.nightly_rate_usd}/night`,
      href: hotel.maps_url || hotel.affiliate_link,
      photoName: hotel.photo_name,
      attribution: hotel.photo_attribution,
      ctaLabel: 'View stay',
    }
  }

  const restaurant = itinerary.restaurants.find(
    (entry) =>
      sameVenueTitle(entry.name, item.title) ||
      sameVenueLink(entry.maps_url || entry.reservation_link, item.booking_link),
  )
  if (restaurant) {
    return {
      title: restaurant.name,
      subtitle: `${restaurant.neighborhood} · ${restaurant.cuisine}`,
      href: restaurant.maps_url || restaurant.reservation_link,
      photoName: restaurant.photo_name,
      attribution: restaurant.photo_attribution,
      ctaLabel: 'Open place',
    }
  }

  const experience = itinerary.experiences.find(
    (entry) =>
      sameVenueTitle(entry.name, item.title) || sameVenueLink(entry.maps_url || entry.booking_link, item.booking_link),
  )
  if (experience) {
    return {
      title: experience.name,
      subtitle: `${experience.neighborhood} · ${experience.category}`,
      href: experience.maps_url || experience.booking_link,
      photoName: experience.photo_name,
      attribution: experience.photo_attribution,
      ctaLabel: 'View stop',
    }
  }

  return null
}

function normalizeText(value: string) {
  return value
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim()
}

function sameVenueTitle(left: string, right: string) {
  const a = normalizeText(left)
  const b = normalizeText(right)
  return a === b || a.includes(b) || b.includes(a)
}

function normalizeLink(value?: string | null) {
  if (!value) return ''
  return value.replace(/\/+$/, '')
}

function sameVenueLink(left?: string | null, right?: string | null) {
  const a = normalizeLink(left)
  const b = normalizeLink(right)
  return Boolean(a && b && a === b)
}

export function DayItemCard({ item, venue }: { item: DayItem; venue: ResolvedVenue | null }) {
  const photoUrl = buildPhotoUrl(venue?.photoName)
  const href = venue?.href || item.booking_link

  return (
    <article className="overflow-hidden rounded-[18px] border border-slate-800 bg-slate-950">
      {photoUrl ? (
        <div className="aspect-[16/9] w-full bg-slate-900">
          <img className="h-full w-full object-cover" src={photoUrl} alt={venue?.title || item.title} loading="lazy" />
        </div>
      ) : null}

      <div className="space-y-3 px-4 py-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-xs uppercase tracking-[0.18em] text-slate-400">{item.time_label}</div>
            <div className="mt-1 text-sm font-medium text-slate-100">{item.title}</div>
            {venue?.subtitle ? <div className="mt-1 text-xs text-slate-400">{venue.subtitle}</div> : null}
          </div>
          {item.neighborhood ? (
            <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">{item.neighborhood}</div>
          ) : null}
        </div>

        <div className="text-sm leading-6 text-slate-300">{item.description}</div>

        {href ? (
          <div className="flex items-center justify-between gap-3">
            <a
              className="rounded-full border border-slate-700 bg-slate-900 px-3 py-2 text-xs uppercase tracking-[0.16em] text-slate-200 transition-colors hover:border-slate-600 hover:text-white"
              href={href}
              target="_blank"
              rel="noreferrer"
            >
              {venue?.ctaLabel || 'Open'}
            </a>
            {venue?.attribution ? (
              <span className="line-clamp-1 text-[10px] text-slate-500">Photo: {venue.attribution}</span>
            ) : null}
          </div>
        ) : null}
      </div>
    </article>
  )
}
