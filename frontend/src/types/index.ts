export interface RouteRequest {
  interests: string
  hours: number
  start_lat: number
  start_lon: number
  social_mode: 'solo' | 'friends' | 'family'
  coffee_preference?: number
  intensity: 'relaxed' | 'medium' | 'intense'
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
}

export interface RouteResponse {
  summary: string
  route: POIInRoute[]
  total_est_minutes: number
  total_distance_km: number
  notes: string[]
  atmospheric_description?: string
}