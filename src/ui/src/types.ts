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
  short_description?: string
  rating?: number | null
  maps_url?: string | null
  photo_name?: string | null
  photo_attribution?: string | null
}

export type RestaurantOption = {
  id: string
  name: string
  cuisine: string
  price_range?: string
  neighborhood: string
  must_order_dish?: string | null
  why_it_fits?: string
  reservation_link: string
  rating?: number | null
  maps_url?: string | null
  photo_name?: string | null
  photo_attribution?: string | null
}

export type ExperienceOption = {
  id: string
  name: string
  category: string
  duration_hours?: number
  estimated_cost_usd?: number
  neighborhood: string
  best_time?: string
  why_it_fits?: string
  booking_link: string
  rating?: number | null
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
  transport_note?: string | null
}

export type DayPlan = {
  day_number: number
  theme: string
  summary: string
  items: DayItem[]
  practical_tips?: string[]
  day_estimated_cost_usd?: number | null
}

export type BudgetLineItem = {
  category: string
  amount_usd: number
  detail: string
}

export type BudgetEstimate = {
  destination: string
  trip_length_days: number
  budget_tier: string
  currency: string
  accommodation_total_usd: number
  food_total_usd: number
  activities_total_usd: number
  transport_total_usd: number
  misc_total_usd: number
  grand_total_usd: number
  daily_average_usd: number
  line_items: BudgetLineItem[]
  notes: string[]
}

export type VisaRequirements = {
  destination: string
  nationality: string
  visa_type: string
  max_stay_days?: number | null
  required_docs: string[]
  processing_days?: number | null
  fee_usd?: number | null
  notes: string
  official_link?: string | null
}

export type PackingCategory = {
  category: string
  items: string[]
}

export type PackingSuggestions = {
  destination: string
  month: string
  weather_note: string
  categories: PackingCategory[]
}

export type ItineraryDraft = {
  destination: string
  month: string
  trip_length_days: number
  travel_party?: string | null
  budget?: string
  interests: string[]
  weather?: WeatherSummary | null
  selected_hotel?: HotelOption | null
  hotels: HotelOption[]
  restaurants: RestaurantOption[]
  experiences: ExperienceOption[]
  days: DayPlan[]
  budget_estimate?: BudgetEstimate | null
  visa_requirements?: VisaRequirements | null
  packing_suggestions?: PackingSuggestions | null
  trip_tone?: string | null
  key_moments?: string[]
  cultural_notes?: string[]
  summary: string
}

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export function buildPhotoUrl(photoName?: string | null) {
  if (!photoName) return null
  return `${API_BASE_URL}/places/photo?name=${encodeURIComponent(photoName)}`
}
