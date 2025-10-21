import { useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Home, Share2, Printer, MapIcon, List, Sparkles, Coffee } from 'lucide-react'
import type { RouteResponse } from '../../types'
import MapView from './MapView'
import ListView from './ListView'
import ShareModal from './ShareModal'

type ViewMode = 'map' | 'list'

interface Props {
  route: RouteResponse
  onNewRoute: () => void
  onBackToHero: () => void
}

const formatTime = (timestamp: string) =>
  new Date(timestamp).toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
  })

const resolveGeometry = (route: RouteResponse) =>
  route.route_geometry?.length
    ? route.route_geometry.map(([lat, lon]) => [lat, lon] as [number, number])
    : route.route.map(({ lat, lon }) => [lat, lon] as [number, number])

export default function RouteViewer({ route, onNewRoute, onBackToHero }: Props) {
  const [view, setView] = useState<ViewMode>('map')
  const [expandedPoi, setExpandedPoi] = useState<number | null>(null)
  const [showShareModal, setShowShareModal] = useState(false)
  const timelineRef = useRef<HTMLDivElement>(null)

  const geometry = useMemo(() => resolveGeometry(route), [route])
  const coffeeBreaksCount = useMemo(
    () => route.route.filter(poi => poi.is_coffee_break).length,
    [route],
  )

  const hours = Math.floor(route.total_est_minutes / 60)
  const minutes = route.total_est_minutes % 60

  const scrollToPoi = (poiId: number) => {
    const element = document.getElementById(`poi-${poiId}`)
    if (!element) return

    element.scrollIntoView({ behavior: 'smooth', block: 'center' })
    setExpandedPoi(poiId)
    setTimeout(() => setExpandedPoi(null), 3000)
  }

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: 'Мой маршрут по Нижнему Новгороду',
        text: route.summary,
        url: window.location.href,
      })
      return
    }

    setShowShareModal(true)
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white/95 dark:bg-slate-900/95 backdrop-blur-lg border-b border-slate-200 dark:border-slate-700 sticky top-0 z-50 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <button
                onClick={onBackToHero}
                className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                title="На главную"
              >
                <Home className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              </button>
              <div className="h-6 w-px bg-slate-300 dark:bg-slate-700" />
              <div>
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  <h1 className="text-xl font-bold text-slate-900 dark:text-white">
                    Ваш маршрут готов!
                  </h1>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                  {route.route.length} точек • {hours > 0 && `${hours}ч `}
                  {minutes}м • {route.total_distance_km.toFixed(1)} км • {coffeeBreaksCount}{' '}
                  <span className="inline-flex items-center gap-1">
                    <Coffee className="w-3 h-3" />
                    перерывов
                  </span>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="hidden sm:flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg">
                <button
                  onClick={() => setView('map')}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                    view === 'map'
                      ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  <MapIcon className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setView('list')}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                    view === 'list'
                      ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  <List className="w-4 h-4" />
                </button>
              </div>

              <button
                onClick={handleShare}
                className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                title="Поделиться"
              >
                <Share2 className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              </button>
              <button
                onClick={() => window.print()}
                className="hidden sm:block p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                title="Печать"
              >
                <Printer className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              </button>
              <button
                onClick={onNewRoute}
                className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-lg hover:shadow-lg hover:scale-105 transition-all"
              >
                Новый маршрут
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1">
        <AnimatePresence mode="wait">
          {view === 'map' ? (
            <motion.div
              key="map-view"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="h-full"
            >
              <MapView route={route} geometry={geometry} onPoiFocus={scrollToPoi} formatTime={formatTime} />
            </motion.div>
          ) : (
            <motion.div
              key="list-view"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="max-w-5xl mx-auto px-4 sm:px-6 py-8"
            >
              <ListView
                route={route}
                expandedPoi={expandedPoi}
                setExpandedPoi={setExpandedPoi}
                formatTime={formatTime}
                timelineRef={timelineRef}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <AnimatePresence>
        {showShareModal && <ShareModal onClose={() => setShowShareModal(false)} />}
      </AnimatePresence>
    </div>
  )
}
