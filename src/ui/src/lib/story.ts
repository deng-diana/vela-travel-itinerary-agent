/**
 * story.ts — transforms a completed ItineraryDraft into a typed StorySlide[]
 *
 * Slide sequence:
 *   1. COVER
 *   2. WEATHER (if available)
 *   3. HIGHLIGHTS — base hotel + top 3 must-experience moments (replaces standalone hotel/dining/experiences slides)
 *   4. DAY 1…N — comprehensive per-day plan (hotel + meals + activities + evening)
 *   5. PRACTICAL — budget + visa (conditional)
 *   6. PACKING (conditional)
 *   7. CLOSING
 */

import type {
  ItineraryDraft,
  DayPlan,
  RestaurantOption,
  ExperienceOption,
} from '../types'

// ---------------------------------------------------------------------------
// Slide type model
// ---------------------------------------------------------------------------

export type SlideType =
  | 'cover'
  | 'weather'
  | 'highlights'
  | 'day'
  | 'practical'
  | 'packing'
  | 'closing'

export interface CoverSlideData {
  destination: string
  trip_tone: string | null
  month: string
  trip_length_days: number
  travel_party: string | null
  interests: string[]
}

export interface WeatherSlideData {
  destination: string
  month: string
  avg_temp_c: number | null
  rainfall_mm: number | null
  conditions_summary: string
  packing_notes: string[]
}

export interface HighlightMoment {
  name: string
  photo_url: string | null
  caption: string        // must_order_dish / best_time / why_it_fits
  kind: 'dining' | 'experience'
  neighborhood: string
}

export interface HighlightSlideData {
  hotel: {
    name: string
    neighborhood: string
    photo_url: string | null
    rating?: number | null
    nightly_rate_usd: number
    affiliate_link: string
    short_description?: string
  } | null
  moments: HighlightMoment[]  // top 3 must-experience moments
}

export interface DaySlideData {
  day_number: number
  theme: string
  summary: string
  items: DayPlan['items']
  practical_tips: string[]
  day_estimated_cost_usd: number | null
  part?: number
}

export interface PracticalSlideData {
  budget: ItineraryDraft['budget_estimate']
  visa: ItineraryDraft['visa_requirements']
}

export interface PackingSlideData {
  weather_note: string
  categories: Array<{ category: string; items: string[] }>
}

export interface ClosingSlideData {
  destination: string
  summary: string
  key_moments: string[]
  cultural_notes: string[]
  trip_tone: string | null
}

export type StorySlideData =
  | { type: 'cover'; data: CoverSlideData }
  | { type: 'weather'; data: WeatherSlideData }
  | { type: 'highlights'; data: HighlightSlideData }
  | { type: 'day'; data: DaySlideData }
  | { type: 'practical'; data: PracticalSlideData }
  | { type: 'packing'; data: PackingSlideData }
  | { type: 'closing'; data: ClosingSlideData }

export interface StorySlide extends StorySlideData {
  id: string
}

// ---------------------------------------------------------------------------
// Viewport constraint — days with many items get split
// ---------------------------------------------------------------------------

const MAX_ITEMS_PER_SLIDE = 7

// ---------------------------------------------------------------------------
// Main transformer
// ---------------------------------------------------------------------------

export function buildStory(itinerary: ItineraryDraft, photoUrlBuilder: (name?: string | null) => string | null): StorySlide[] {
  const slides: StorySlide[] = []
  let counter = 0
  const id = (type: string) => `${type}-${++counter}`

  // 1. COVER
  slides.push({
    id: id('cover'),
    type: 'cover',
    data: {
      destination: itinerary.destination,
      trip_tone: itinerary.trip_tone ?? null,
      month: itinerary.month,
      trip_length_days: itinerary.trip_length_days,
      travel_party: itinerary.travel_party ?? null,
      interests: itinerary.interests,
    },
  })

  // 2. WEATHER (conditional)
  if (itinerary.weather) {
    slides.push({
      id: id('weather'),
      type: 'weather',
      data: {
        destination: itinerary.weather.destination,
        month: itinerary.weather.month,
        avg_temp_c: itinerary.weather.avg_temp_c,
        rainfall_mm: itinerary.weather.rainfall_mm,
        conditions_summary: itinerary.weather.conditions_summary,
        packing_notes: itinerary.weather.packing_notes.slice(0, 4),
      },
    })
  }

  // 3. HIGHLIGHTS — hotel + top moments (replaces standalone Hotel/Dining/Experiences slides)
  const hotel = itinerary.selected_hotel ?? null
  const moments = buildHighlightMoments(itinerary, photoUrlBuilder)

  if (hotel || moments.length > 0) {
    slides.push({
      id: id('highlights'),
      type: 'highlights',
      data: {
        hotel: hotel
          ? {
              name: hotel.name,
              neighborhood: hotel.neighborhood,
              photo_url: photoUrlBuilder(hotel.photo_name),
              rating: hotel.rating,
              nightly_rate_usd: hotel.nightly_rate_usd,
              affiliate_link: hotel.affiliate_link,
              short_description: hotel.short_description,
            }
          : null,
        moments,
      },
    })
  }

  // 4. DAY slides
  for (const day of itinerary.days) {
    const daySlides = splitDay(day)
    for (const s of daySlides) {
      slides.push({ id: id('day'), type: 'day', data: s })
    }
  }

  // 5. PRACTICAL (conditional)
  if (itinerary.budget_estimate || itinerary.visa_requirements) {
    slides.push({
      id: id('practical'),
      type: 'practical',
      data: {
        budget: itinerary.budget_estimate ?? null,
        visa: itinerary.visa_requirements ?? null,
      },
    })
  }

  // 6. PACKING (conditional)
  if (itinerary.packing_suggestions) {
    slides.push({
      id: id('packing'),
      type: 'packing',
      data: {
        weather_note: itinerary.packing_suggestions.weather_note,
        categories: itinerary.packing_suggestions.categories,
      },
    })
  }

  // 7. CLOSING
  slides.push({
    id: id('closing'),
    type: 'closing',
    data: {
      destination: itinerary.destination,
      summary: itinerary.summary,
      key_moments: itinerary.key_moments ?? [],
      cultural_notes: itinerary.cultural_notes ?? [],
      trip_tone: itinerary.trip_tone ?? null,
    },
  })

  return slides
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildHighlightMoments(
  itinerary: ItineraryDraft,
  photoUrlBuilder: (name?: string | null) => string | null,
): HighlightMoment[] {
  const moments: HighlightMoment[] = []

  // Top experience
  const topExp = topExperiences(itinerary.experiences, 2)
  for (const e of topExp) {
    moments.push({
      name: e.name,
      photo_url: photoUrlBuilder(e.photo_name),
      caption: e.best_time ?? e.why_it_fits ?? e.category,
      kind: 'experience',
      neighborhood: e.neighborhood,
    })
  }

  // Top restaurant
  const topRest = topRestaurants(itinerary.restaurants, 1)
  for (const r of topRest) {
    moments.push({
      name: r.name,
      photo_url: photoUrlBuilder(r.photo_name),
      caption: r.must_order_dish ? `Try: ${r.must_order_dish}` : (r.why_it_fits ?? r.cuisine),
      kind: 'dining',
      neighborhood: r.neighborhood,
    })
  }

  return moments.slice(0, 3)
}

function splitDay(day: DayPlan): DaySlideData[] {
  if (day.items.length <= MAX_ITEMS_PER_SLIDE) {
    return [{
      day_number: day.day_number,
      theme: day.theme,
      summary: day.summary,
      items: day.items,
      practical_tips: day.practical_tips ?? [],
      day_estimated_cost_usd: day.day_estimated_cost_usd ?? null,
    }]
  }

  const part1 = day.items.slice(0, MAX_ITEMS_PER_SLIDE)
  const part2 = day.items.slice(MAX_ITEMS_PER_SLIDE)

  return [
    {
      day_number: day.day_number,
      theme: day.theme,
      summary: day.summary,
      items: part1,
      practical_tips: [],
      day_estimated_cost_usd: null,
      part: 1,
    },
    {
      day_number: day.day_number,
      theme: day.theme,
      summary: '',
      items: part2,
      practical_tips: day.practical_tips ?? [],
      day_estimated_cost_usd: day.day_estimated_cost_usd ?? null,
      part: 2,
    },
  ]
}

function topRestaurants(restaurants: RestaurantOption[], n: number): RestaurantOption[] {
  return [...restaurants]
    .sort((a, b) => {
      const aScore = (a.photo_name ? 2 : 0) + (a.rating ?? 0)
      const bScore = (b.photo_name ? 2 : 0) + (b.rating ?? 0)
      return bScore - aScore
    })
    .slice(0, n)
}

function topExperiences(experiences: ExperienceOption[], n: number): ExperienceOption[] {
  return [...experiences]
    .sort((a, b) => {
      const aScore = (a.photo_name ? 2 : 0) + (a.rating ?? 0)
      const bScore = (b.photo_name ? 2 : 0) + (b.rating ?? 0)
      return bScore - aScore
    })
    .slice(0, n)
}
