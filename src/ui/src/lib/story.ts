/**
 * story.ts — transforms an ItineraryDraft (partial or complete) into StorySlide[]
 *
 * Works incrementally: as each tool completes, new slides appear.
 * Slide sequence (all conditional on data availability):
 *   1. COVER        — always present once destination is known
 *   2. WEATHER      — after get_weather completes
 *   3. HIGHLIGHTS   — after hotels + restaurants/experiences arrive
 *   4. DAY 1…N      — after get_daily_structure completes
 *   5. PRACTICAL    — after estimate_budget / get_visa_requirements
 *   6. PACKING      — after get_packing_suggestions
 *   7. CLOSING      — after final_response (summary populated)
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
  background_photo_url: string | null
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
  caption: string
  kind: 'dining' | 'experience'
  neighborhood: string
  booking_link: string | null
}

export interface HotelOption {
  name: string
  neighborhood: string
  photo_url: string | null
  rating?: number | null
  nightly_rate_usd: number
  affiliate_link: string
  short_description?: string
  why_selected?: string | null
  nearby_highlights?: string[]
}

export interface HighlightSlideData {
  hotels: HotelOption[]
  moments: HighlightMoment[]
}

export interface DaySlideItem {
  time_label: string
  kind: string
  title: string
  neighborhood?: string | null
  description: string
  booking_link?: string | null
  transport_note?: string | null
  photo_url?: string | null
}

export interface DaySlideData {
  destination: string
  day_number: number
  theme: string
  summary: string
  items: DaySlideItem[]
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

export type StorySlide =
  | ({ id: string } & { type: 'cover'; data: CoverSlideData })
  | ({ id: string } & { type: 'weather'; data: WeatherSlideData })
  | ({ id: string } & { type: 'highlights'; data: HighlightSlideData })
  | ({ id: string } & { type: 'day'; data: DaySlideData })
  | ({ id: string } & { type: 'practical'; data: PracticalSlideData })
  | ({ id: string } & { type: 'packing'; data: PackingSlideData })
  | ({ id: string } & { type: 'closing'; data: ClosingSlideData })

// ---------------------------------------------------------------------------
// Viewport constraint — days with many items get split
// ---------------------------------------------------------------------------

const MAX_ITEMS_PER_SLIDE = 7

// ---------------------------------------------------------------------------
// Main transformer — works with partial data for progressive rendering
// ---------------------------------------------------------------------------

export function buildStory(
  itinerary: ItineraryDraft | null,
  photoUrlBuilder: (name?: string | null) => string | null,
): StorySlide[] {
  if (!itinerary || !itinerary.destination) return []

  const slides: StorySlide[] = []
  let counter = 0
  const id = (type: string) => `${type}-${++counter}`

  // 1. COVER — always present once we have a destination
  // Background photo: iconic destination landmark via Unsplash (free, no key needed)
  // Falls back to hotel/experience photo if available
  const coverPhotoUrl =
    destinationLandmarkUrl(itinerary.destination) ??
    photoUrlBuilder(itinerary.selected_hotel?.photo_name) ??
    photoUrlBuilder(topExperiences(itinerary.experiences, 1)[0]?.photo_name) ??
    null

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
      background_photo_url: coverPhotoUrl,
    },
  })

  // 2. WEATHER (conditional — appears when get_weather completes)
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

  // 3. HIGHLIGHTS — multiple hotels + top moments (appears when hotels or venues arrive)
  const selectedHotels = itinerary.selected_hotel ? [itinerary.selected_hotel] : []
  const otherHotels = itinerary.hotels.filter(
    h => !itinerary.selected_hotel || h.name !== itinerary.selected_hotel.name
  ).slice(0, 2) // Include up to 2 alternative hotels
  const allHotels = [...selectedHotels, ...otherHotels].slice(0, 3) // Max 3 hotels displayed

  const moments = buildHighlightMoments(itinerary, photoUrlBuilder)

  if (allHotels.length > 0 || moments.length > 0) {
    slides.push({
      id: id('highlights'),
      type: 'highlights',
      data: {
        hotels: allHotels.map(hotel => ({
          name: hotel.name,
          neighborhood: hotel.neighborhood,
          photo_url: photoUrlBuilder(hotel.photo_name),
          rating: hotel.rating,
          nightly_rate_usd: hotel.nightly_rate_usd,
          affiliate_link: hotel.affiliate_link,
          short_description: hotel.short_description,
          why_selected: hotel.short_description, // Use short_description for why_selected
          nearby_highlights: hotel.key_highlights, // Use key_highlights for nearby highlights
        })),
        moments,
      },
    })
  }

  // Build photo lookup: venue title (lowercased) → photo_url
  const photoByTitle = new Map<string, string | null>()
  for (const r of itinerary.restaurants) {
    photoByTitle.set(r.name.toLowerCase(), photoUrlBuilder(r.photo_name))
  }
  for (const e of itinerary.experiences) {
    photoByTitle.set(e.name.toLowerCase(), photoUrlBuilder(e.photo_name))
  }

  // 4. DAY slides (appear when get_daily_structure completes)
  for (const day of itinerary.days) {
    const enrichedItems: DaySlideItem[] = day.items.map((item) => ({
      ...item,
      photo_url: photoByTitle.get(item.title.toLowerCase()) ?? null,
    }))
    const daySlides = splitDay({ ...day, items: enrichedItems }, itinerary.destination)
    for (const s of daySlides) {
      slides.push({ id: id('day'), type: 'day', data: s })
    }
  }

  // 5. PRACTICAL (conditional — appears when budget or visa arrive)
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

  // 7. CLOSING — only when summary is meaningful (after final_response)
  const hasMeaningfulSummary = itinerary.summary && itinerary.summary !== 'Trip plan updated.' && itinerary.days.length > 0
  if (hasMeaningfulSummary) {
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
  }

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

  // Top experiences (up to 4)
  const topExp = topExperiences(itinerary.experiences, 4)
  for (const e of topExp) {
    moments.push({
      name: e.name,
      photo_url: photoUrlBuilder(e.photo_name),
      caption: e.best_time ?? e.why_it_fits ?? e.category,
      kind: 'experience',
      neighborhood: e.neighborhood,
      booking_link: e.booking_link ?? null,
    })
  }

  // Top restaurants with signature dish callout (up to 3)
  const topRest = topRestaurants(itinerary.restaurants, 3)
  for (const r of topRest) {
    moments.push({
      name: r.must_order_dish ? r.must_order_dish : r.name,
      photo_url: photoUrlBuilder(r.photo_name),
      caption: r.must_order_dish
        ? `At ${r.name} · ${r.cuisine}`
        : (r.why_it_fits ?? r.cuisine),
      kind: 'dining',
      neighborhood: r.neighborhood,
      booking_link: r.reservation_link ?? null,
    })
  }

  // Prioritise moments with photos, then shuffle for variety
  const withPhoto = moments.filter((m) => m.photo_url)
  const withoutPhoto = moments.filter((m) => !m.photo_url)
  return [...withPhoto, ...withoutPhoto].slice(0, 6)
}

function splitDay(day: DayPlan & { items: DaySlideItem[] }, destination: string): DaySlideData[] {
  if (day.items.length <= MAX_ITEMS_PER_SLIDE) {
    return [{
      destination,
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
      destination,
      day_number: day.day_number,
      theme: day.theme,
      summary: day.summary,
      items: part1,
      practical_tips: [],
      day_estimated_cost_usd: null,
      part: 1,
    },
    {
      destination,
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

// ---------------------------------------------------------------------------
// Destination landmark photo — Unsplash Source API (free, no auth required)
// Maps known cities to curated search terms for iconic landmark shots.
// ---------------------------------------------------------------------------

const LANDMARK_KEYWORDS: Record<string, string> = {
  paris: 'paris,eiffel+tower,night',
  tokyo: 'tokyo,shibuya,cityscape',
  kyoto: 'kyoto,fushimi+inari,temple',
  osaka: 'osaka,dotonbori,japan',
  london: 'london,tower+bridge,thames',
  'new york': 'new+york,manhattan,skyline',
  'new york city': 'new+york,manhattan,skyline',
  nyc: 'new+york,manhattan,skyline',
  rome: 'rome,colosseum,italy',
  barcelona: 'barcelona,sagrada+familia,spain',
  amsterdam: 'amsterdam,canal,netherlands',
  dubai: 'dubai,burj+khalifa,skyline',
  singapore: 'singapore,marina+bay,skyline',
  sydney: 'sydney,opera+house,harbour',
  'hong kong': 'hong+kong,victoria+harbour,skyline',
  bali: 'bali,temple,rice+terrace',
  bangkok: 'bangkok,temple,thailand',
  istanbul: 'istanbul,hagia+sophia,bosphorus',
  prague: 'prague,old+town,castle',
  vienna: 'vienna,schonbrunn,austria',
  santorini: 'santorini,oia,white+buildings',
  athens: 'athens,acropolis,parthenon',
  lisbon: 'lisbon,tram,alfama',
  florence: 'florence,duomo,italy',
  venice: 'venice,canal,gondola',
  berlin: 'berlin,brandenburg+gate,germany',
  madrid: 'madrid,royal+palace,spain',
  seoul: 'seoul,gyeongbokgung,korea',
  taipei: 'taipei,101,skyline',
  beijing: 'beijing,great+wall,forbidden+city',
  shanghai: 'shanghai,bund,skyline',
  'mexico city': 'mexico+city,zocalo,cathedral',
  'rio de janeiro': 'rio+de+janeiro,christ+redeemer,copacabana',
  'buenos aires': 'buenos+aires,obelisk,argentina',
  cairo: 'cairo,pyramids,sphinx',
  marrakech: 'marrakech,medina,morocco',
  'cape town': 'cape+town,table+mountain,south+africa',
  'new zealand': 'new+zealand,milford+sound,fjord',
  auckland: 'auckland,harbour+bridge,new+zealand',
  toronto: 'toronto,cn+tower,skyline',
  vancouver: 'vancouver,mountains,harbour',
  'san francisco': 'san+francisco,golden+gate,bridge',
  'los angeles': 'los+angeles,hollywood,skyline',
  miami: 'miami,south+beach,art+deco',
  chicago: 'chicago,bean,skyline',
  edinburgh: 'edinburgh,castle,scotland',
  dublin: 'dublin,trinity+college,ireland',
  copenhagen: 'copenhagen,nyhavn,denmark',
  stockholm: 'stockholm,gamla+stan,sweden',
  oslo: 'oslo,fjord,norway',
  helsinki: 'helsinki,cathedral,finland',
  zurich: 'zurich,lake,switzerland',
  geneva: 'geneva,lake,switzerland',
  munich: 'munich,marienplatz,bavaria',
  budapest: 'budapest,parliament,danube',
  warsaw: 'warsaw,old+town,poland',
  krakow: 'krakow,wawel,castle',
  dubrovnik: 'dubrovnik,old+town,adriatic',
}

function destinationLandmarkUrl(destination: string): string | null {
  const key = destination.toLowerCase().trim()
  const keywords = LANDMARK_KEYWORDS[key] ?? `${encodeURIComponent(destination)},landmark,travel,cityscape`
  // Unsplash Source API — free, no authentication, redirects to a relevant photo
  return `https://source.unsplash.com/1920x1080/?${keywords}`
}
