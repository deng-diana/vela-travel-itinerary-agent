export type ChatMessage = { role: 'user' | 'assistant'; text: string }
export type StreamEvent = { type: string; message?: string | null; tool_name?: string | null; payload?: unknown }
export type AgentStep = { id: string; title: string; detail: string; status: 'active' | 'completed' }

export type WeatherSummary = {
  destination: string
  month: string
  avg_temp_c: number | null
  rainfall_mm: number | null
  conditions_summary: string
  packing_notes: string[]
}

export type HotelOption = {
  id: string
  name: string
  neighborhood: string
  category: string
  nightly_rate_usd: number
  affiliate_link: string
  key_highlights: string[]
  maps_url?: string | null
  photo_name?: string | null
  photo_attribution?: string | null
}

export type RestaurantOption = {
  id: string
  name: string
  cuisine: string
  neighborhood: string
  must_order_dish?: string | null
  reservation_link: string
  maps_url?: string | null
  photo_name?: string | null
  photo_attribution?: string | null
}

export type ExperienceOption = {
  id: string
  name: string
  category: string
  neighborhood: string
  booking_link: string
  maps_url?: string | null
  photo_name?: string | null
  photo_attribution?: string | null
}

export type DayItem = {
  time_label: string
  kind: string
  title: string
  neighborhood?: string | null
  description: string
  booking_link?: string | null
}

export type DayPlan = { day_number: number; theme: string; summary: string; items: DayItem[] }

export type ItineraryDraft = {
  destination: string
  month: string
  trip_length_days: number
  interests: string[]
  weather?: WeatherSummary | null
  selected_hotel?: HotelOption | null
  hotels: HotelOption[]
  restaurants: RestaurantOption[]
  experiences: ExperienceOption[]
  days: DayPlan[]
  summary: string
}

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export function buildPhotoUrl(photoName?: string | null) {
  if (!photoName) return null
  return `${API_BASE_URL}/places/photo?name=${encodeURIComponent(photoName)}`
}
