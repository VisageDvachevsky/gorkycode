import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RouteForm from './components/RouteForm'
import RouteDisplay from './components/RouteDisplay'
import Hero from './components/Hero'
import type { RouteResponse } from './types'

const queryClient = new QueryClient()

function App() {
  const [route, setRoute] = useState<RouteResponse | null>(null)
  const [showForm, setShowForm] = useState(false)

  const handleStartJourney = () => {
    setShowForm(true)
    setTimeout(() => {
      document.getElementById('route-form')?.scrollIntoView({ behavior: 'smooth' })
    }, 100)
  }

  const handleRouteGenerated = (newRoute: RouteResponse) => {
    setRoute(newRoute)
    setTimeout(() => {
      document.getElementById('route-display')?.scrollIntoView({ behavior: 'smooth' })
    }, 100)
  }

  const handleNewRoute = () => {
    setRoute(null)
    setTimeout(() => {
      document.getElementById('route-form')?.scrollIntoView({ behavior: 'smooth' })
    }, 100)
  }

  return (
    <QueryClientProvider client={queryClient}>
      <div className="relative min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-indigo-950 overflow-hidden">
        {/* Static background decorative elements */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none opacity-30">
          <div className="absolute top-0 left-1/4 w-[600px] h-[600px] rounded-full bg-blue-500/30 blur-3xl animate-float-slow" />
          <div className="absolute bottom-0 right-1/4 w-[800px] h-[800px] rounded-full bg-purple-500/20 blur-3xl animate-float-delayed" />
          <div className="absolute top-1/3 right-1/3 w-[500px] h-[500px] rounded-full bg-cyan-500/20 blur-3xl animate-pulse-slow" />
          <div className="absolute bottom-1/3 left-1/3 w-[400px] h-[400px] rounded-full bg-pink-500/15 blur-3xl animate-pulse-slower" />
        </div>

        {/* Starfield effect */}
        <div className="fixed inset-0 pointer-events-none">
          {Array.from({ length: 50 }).map((_, i) => (
            <div
              key={`star-${i}`}
              className="absolute w-1 h-1 bg-white rounded-full animate-twinkle"
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
                animationDelay: `${Math.random() * 3}s`,
                opacity: Math.random() * 0.7 + 0.3
              }}
            />
          ))}
        </div>

        {/* Header */}
        <header className="relative z-50 backdrop-blur-xl bg-white/5 border-b border-white/10 sticky top-0">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-20">
              <div className="flex items-center gap-4 group cursor-pointer">
                <div className="relative">
                  <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-purple-500 rounded-2xl blur-xl opacity-50 group-hover:opacity-100 transition-opacity" />
                  <div className="relative text-5xl transform group-hover:scale-110 transition-transform">
                    🧭
                  </div>
                </div>
                <div>
                  <h1 className="text-3xl font-black bg-gradient-to-r from-blue-400 via-cyan-400 to-purple-400 bg-clip-text text-transparent animate-gradient">
                    AI-Tourist
                  </h1>
                  <p className="text-sm text-blue-300/70">Нижний Новгород</p>
                </div>
              </div>
              
              {route && (
                <button
                  onClick={handleNewRoute}
                  className="group relative px-6 py-3 font-bold text-white overflow-hidden rounded-2xl transition-all hover:scale-105"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-purple-600 transition-transform group-hover:scale-110" />
                  <div className="absolute inset-0 bg-gradient-to-r from-purple-600 to-pink-600 opacity-0 group-hover:opacity-100 transition-opacity" />
                  <span className="relative flex items-center gap-2">
                    ← Новый маршрут
                  </span>
                </button>
              )}
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="relative z-10">
          {!showForm && !route && (
            <Hero onStartJourney={handleStartJourney} />
          )}
          
          {showForm && !route && (
            <div id="route-form" className="py-20 px-4 sm:px-6 lg:px-8">
              <div className="max-w-4xl mx-auto">
                <RouteForm onRouteGenerated={handleRouteGenerated} />
              </div>
            </div>
          )}
          
          {route && (
            <div id="route-display" className="py-20 px-4 sm:px-6 lg:px-8">
              <div className="max-w-6xl mx-auto">
                <RouteDisplay route={route} />
              </div>
            </div>
          )}
        </main>

        {/* Footer */}
        <footer className="relative z-10 backdrop-blur-xl bg-white/5 border-t border-white/10 mt-20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="text-center text-blue-300/50">
              <p>© 2025 AI-Tourist. Powered by AI & ❤️</p>
            </div>
          </div>
        </footer>
      </div>
    </QueryClientProvider>
  )
}

export default App