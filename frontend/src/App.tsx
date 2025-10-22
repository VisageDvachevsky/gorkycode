import { useEffect, useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import Hero from './components/Hero'
import RouteWizard from './components/RouteWizard'
import RouteViewer from './components/route-viewer'
import type { RouteResponse } from './types'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000,
    },
  },
})

type AppState = 'hero' | 'wizard' | 'viewing'

type CompactPoi = {
  i: number
  o?: number
  n: string
  lt: number
  ln: number
  w: string
  tp?: string
  vm: number
  ar: string
  lv: string
  cb?: number
  io?: number
  oh?: string
  an?: string
  c?: string
  tg?: string[]
  em?: string
  df?: number
}

type CompactRoute = {
  v: number
  s: string
  tm: number
  td: number
  wd: number
  tr: number
  nt: string[]
  at?: string
  wa?: string
  st?: string
  tw?: string[]
  rg?: number[][]
  rt: CompactPoi[]
  sh?: string
}

const encoder = new TextEncoder()
const decoder = new TextDecoder()
const BASE64_CHUNK_SIZE = 0x8000

const toBase64 = (bytes: Uint8Array) => {
  let binary = ''
  for (let i = 0; i < bytes.length; i += BASE64_CHUNK_SIZE) {
    const chunk = bytes.subarray(i, i + BASE64_CHUNK_SIZE)
    binary += String.fromCharCode(...chunk)
  }
  return window.btoa(binary).replace(/=+$/, '')
}

const fromBase64 = (encoded: string) => {
  const padding = encoded.length % 4 === 0 ? '' : '='.repeat(4 - (encoded.length % 4))
  const binary = window.atob(encoded + padding)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes
}

const toCompactRoute = (route: RouteResponse): CompactRoute => ({
  v: 1,
  s: route.summary,
  tm: route.total_est_minutes,
  td: route.total_distance_km,
  wd: route.walking_distance_km,
  tr: route.transit_distance_km,
  nt: route.notes,
  at: route.atmospheric_description ?? undefined,
  wa: route.weather_advice ?? undefined,
  st: route.start_time_used ? String(route.start_time_used) : undefined,
  tw: route.time_warnings && route.time_warnings.length ? route.time_warnings : undefined,
  rg: route.route_geometry && route.route_geometry.length ? route.route_geometry : undefined,
  rt: route.route.map(poi => ({
    i: poi.poi_id,
    o: poi.order,
    n: poi.name,
    lt: poi.lat,
    ln: poi.lon,
    w: poi.why,
    tp: poi.tip ?? undefined,
    vm: poi.est_visit_minutes,
    ar: String(poi.arrival_time),
    lv: String(poi.leave_time),
    cb: poi.is_coffee_break ? 1 : undefined,
    io: typeof poi.is_open === 'boolean' ? (poi.is_open ? 1 : 0) : undefined,
    oh: poi.opening_hours ?? undefined,
    an: poi.availability_note ?? undefined,
    c: poi.category ?? undefined,
    tg: poi.tags && poi.tags.length ? poi.tags : undefined,
    em: poi.emoji ?? undefined,
    df: poi.distance_from_previous_km ?? undefined,
  })),
  sh: route.share_token ?? undefined,
})

const fromCompactRoute = (data: any): RouteResponse | null => {
  if (!data || typeof data !== 'object') return null
  if ('route' in data && Array.isArray((data as RouteResponse).route)) {
    return data as RouteResponse
  }
  if (typeof data.s !== 'string' || !Array.isArray(data.rt)) {
    return null
  }

  const items = (data.rt as CompactPoi[]).map((poi, index) => ({
    order: typeof poi.o === 'number' ? poi.o : index + 1,
    poi_id: poi.i,
    name: poi.n,
    lat: Number(poi.lt),
    lon: Number(poi.ln),
    why: poi.w,
    tip: poi.tp ?? undefined,
    est_visit_minutes: typeof poi.vm === 'number' ? poi.vm : 0,
    arrival_time: String(poi.ar),
    leave_time: String(poi.lv),
    is_coffee_break: Boolean(poi.cb),
    is_open: poi.io === undefined ? undefined : poi.io === 1,
    opening_hours: poi.oh ?? undefined,
    availability_note: poi.an ?? undefined,
    category: poi.c ?? undefined,
    tags: Array.isArray(poi.tg) ? poi.tg : [],
    emoji: poi.em ?? undefined,
    distance_from_previous_km: typeof poi.df === 'number' ? poi.df : undefined,
  }))

  return {
    summary: data.s,
    route: items,
    total_est_minutes: typeof data.tm === 'number' ? data.tm : 0,
    total_distance_km: typeof data.td === 'number' ? data.td : 0,
    notes: Array.isArray(data.nt) ? data.nt : [],
    atmospheric_description: data.at ?? undefined,
    route_geometry: Array.isArray(data.rg) ? data.rg : [],
    start_time_used: data.st ?? undefined,
    time_warnings: Array.isArray(data.tw) ? data.tw : [],
    movement_legs: [],
    walking_distance_km: typeof data.wd === 'number' ? data.wd : 0,
    transit_distance_km: typeof data.tr === 'number' ? data.tr : 0,
    weather_advice: data.wa ?? undefined,
    share_token: data.sh ?? undefined,
  }
}

const encodeRouteForShare = (route: RouteResponse) => {
  const compact = toCompactRoute(route)
  const json = JSON.stringify(compact)
  const bytes = encoder.encode(json)
  return toBase64(bytes)
}

const decodeRouteFromShare = (encoded: string): RouteResponse | null => {
  try {
    const bytes = fromBase64(encoded)
    const json = decoder.decode(bytes)
    const payload = JSON.parse(json)
    const restored = fromCompactRoute(payload)
    return restored
  } catch (error) {
    console.error('Failed to restore route from share link', error)
    return null
  }
}

function App() {
  const [appState, setAppState] = useState<AppState>('hero')
  const [route, setRoute] = useState<RouteResponse | null>(null)
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const encoded = params.get('itinerary')
    if (encoded) {
      const restored = decodeRouteFromShare(encoded)
      if (restored) {
        setRoute(restored)
        setAppState('viewing')
      }
    }
    setHydrated(true)
  }, [])

  useEffect(() => {
    if (!hydrated) return
    const url = new URL(window.location.href)
    if (!route) {
      url.searchParams.delete('itinerary')
    } else {
      const encoded = encodeRouteForShare(route)
      url.searchParams.set('itinerary', encoded)
    }
    const query = url.searchParams.toString()
    const next = `${url.pathname}${query ? `?${query}` : ''}`
    window.history.replaceState({}, '', next)
  }, [route, hydrated])

  const handleStartJourney = () => {
    setAppState('wizard')
  }

  const handleRouteGenerated = (newRoute: RouteResponse) => {
    setRoute(newRoute)
    setAppState('viewing')
  }

  const handleNewRoute = () => {
    setRoute(null)
    setAppState('wizard')
  }

  const handleBackToHero = () => {
    setRoute(null)
    setAppState('hero')
  }

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gradient-to-br from-amber-50 via-emerald-50 to-sky-50 transition-colors duration-500">
        <AnimatePresence mode="wait">
          {appState === 'hero' && (
            <motion.div
              key="hero"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.5 }}
            >
              <Hero onStartJourney={handleStartJourney} />
            </motion.div>
          )}

          {appState === 'wizard' && (
            <motion.div
              key="wizard"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.4 }}
              className="min-h-screen"
            >
              <RouteWizard
                onRouteGenerated={handleRouteGenerated}
                onBack={handleBackToHero}
              />
            </motion.div>
          )}

          {appState === 'viewing' && route && (
            <motion.div
              key="viewer"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={{ duration: 0.4 }}
            >
              <RouteViewer
                route={route}
                onNewRoute={handleNewRoute}
                onBackToHero={handleBackToHero}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </QueryClientProvider>
  )
}

export default App
