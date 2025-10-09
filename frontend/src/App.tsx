import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RouteForm from './components/RouteForm'
import RouteDisplay from './components/RouteDisplay'
import type { RouteResponse } from './types'

const queryClient = new QueryClient()

function App() {
  const [route, setRoute] = useState<RouteResponse | null>(null)

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 py-6">
            <h1 className="text-3xl font-bold text-gray-900">
              🧭 AI-Tourist
            </h1>
            <p className="text-gray-600 mt-1">
              Персональные прогулки по Нижнему Новгороду
            </p>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div>
              <RouteForm onRouteGenerated={setRoute} />
            </div>
            
            <div>
              {route ? (
                <RouteDisplay route={route} />
              ) : (
                <div className="bg-white rounded-lg shadow-lg p-8 text-center">
                  <div className="text-gray-400 text-6xl mb-4">🗺️</div>
                  <p className="text-gray-500">
                    Заполните форму слева, чтобы получить персональный маршрут
                  </p>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </QueryClientProvider>
  )
}

export default App