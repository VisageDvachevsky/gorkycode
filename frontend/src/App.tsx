import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import Hero from './components/Hero'
import RouteWizard from './components/RouteWizard'
import RouteViewer from './components/RouteViewer'
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

function App() {
  const [appState, setAppState] = useState<AppState>('hero')
  const [route, setRoute] = useState<RouteResponse | null>(null)

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
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-slate-900 dark:via-slate-800 dark:to-indigo-950 transition-colors duration-500">
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