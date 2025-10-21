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

const encodeRouteForShare = (route: RouteResponse) => {
  const payload = JSON.stringify(route)
  const bytes = new TextEncoder().encode(payload)
  let binary = ''
  bytes.forEach(byte => {
    binary += String.fromCharCode(byte)
  })
  return window.btoa(binary).replace(/=+$/, '')
}

const decodeRouteFromShare = (encoded: string): RouteResponse | null => {
  try {
    const padding = encoded.length % 4 === 0 ? '' : '='.repeat(4 - (encoded.length % 4))
    const binary = window.atob(encoded + padding)
    const bytes = Uint8Array.from(binary, char => char.charCodeAt(0))
    const json = new TextDecoder().decode(bytes)
    return JSON.parse(json) as RouteResponse
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
