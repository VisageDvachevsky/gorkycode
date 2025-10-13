import { useState, useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RouteForm from './components/RouteForm'
import RouteDisplay from './components/RouteDisplay'
import Hero from './components/Hero'
import type { RouteResponse } from './types'

const queryClient = new QueryClient()

function App() {
  const [route, setRoute] = useState<RouteResponse | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY })
    }
    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

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
        {/* Animated background gradient orbs */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          <div 
            className="absolute w-[600px] h-[600px] rounded-full bg-blue-500/20 blur-3xl animate-float"
            style={{
              left: `${mousePosition.x / 20}px`,
              top: `${mousePosition.y / 20}px`,
              transition: 'all 0.5s ease-out'
            }}
          />
          <div 
            className="absolute w-[800px] h-[800px] rounded-full bg-purple-500/15 blur-3xl animate-float-delayed"
            style={{
              right: `${mousePosition.x / 30}px`,
              bottom: `${mousePosition.y / 30}px`,
              transition: 'all 0.7s ease-out'
            }}
          />
          <div className="absolute top-1/4 left-1/4 w-[400px] h-[400px] rounded-full bg-cyan-500/10 blur-3xl animate-pulse-slow" />
          <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] rounded-full bg-pink-500/10 blur-3xl animate-pulse-slower" />
        </div>

        {/* Starfield effect */}
        <div className="fixed inset-0 pointer-events-none">
          {[...Array(50)].map((_, i) => (
            <div
              key={i}
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

          {showForm && (
            <div id="route-form" className="min-h-screen pt-12 pb-24">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <RouteForm onRouteGenerated={handleRouteGenerated} />
              </div>
            </div>
          )}

          {route && (
            <div id="route-display" className="min-h-screen pt-12 pb-24">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <RouteDisplay route={route} onNewRoute={handleNewRoute} />
              </div>
            </div>
          )}
        </main>

        {/* Footer */}
        <footer className="relative z-10 mt-24 border-t border-white/10 backdrop-blur-xl bg-white/5">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <div className="text-center">
              <p className="text-blue-300/70 mb-4">
                Создано с ❤️ для любителей прогулок
              </p>
              <div className="flex items-center justify-center gap-6 text-sm text-blue-400/50">
                <span>Powered by AI</span>
                <span>•</span>
                <span>2GIS API</span>
                <span>•</span>
                <span>v0.2.0</span>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </QueryClientProvider>
  )
}

export default App