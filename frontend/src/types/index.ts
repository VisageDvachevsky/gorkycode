export interface CoffeePreferences {
  enabled: boolean
  interval_minutes: number
  cuisine?: string
  dietary?: string
  outdoor_seating?: boolean
  wifi?: boolean
  search_radius_km?: number
}

export interface RouteRequest {
  interests: string
  categories?: string[]
  hours: number
  start_lat?: number
  start_lon?: number
  start_address?: string
  social_mode: 'solo' | 'friends' | 'family'
  coffee_preferences?: CoffeePreferences
  intensity: 'relaxed' | 'medium' | 'intense'
  allow_transit?: boolean
  start_time?: string
  client_timezone?: string
}

export interface POIInRoute {
  order: number
  poi_id: number
  name: string
  lat: number
  lon: number
  why: string
  tip?: string
  est_visit_minutes: number
  arrival_time: string
  leave_time: string
  is_coffee_break: boolean
  is_open?: boolean
  opening_hours?: string
}

export interface RouteResponse {
  summary: string
  route: POIInRoute[]
  total_est_minutes: number
  total_distance_km: number
  notes: string[]
  atmospheric_description?: string
  route_geometry?: number[][]
  start_time_used?: string
  time_warnings?: string[]
}

export interface Category {
  value: string
  label: string
  count: number
}