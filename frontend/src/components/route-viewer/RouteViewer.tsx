import { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Home, Share2, Printer, MapIcon, List, Sparkles, Coffee } from 'lucide-react'
import type { RouteResponse } from '../../types'
import MapView from './MapView'
import ListView from './ListView'
import ShareModal from './ShareModal'
import ItineraryTimeline from './ItineraryTimeline'
import RouteShareCard from './RouteShareCard'

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
  const [activePoi, setActivePoi] = useState<number | null>(null)
  const timelineRef = useRef<HTMLDivElement>(null)

  const geometry = useMemo(() => resolveGeometry(route), [route])
  const coffeeBreaksCount = useMemo(
    () => route.route.filter(poi => poi.is_coffee_break).length,
    [route],
  )

  const hours = Math.floor(route.total_est_minutes / 60)
  const minutes = route.total_est_minutes % 60

  const emojiForTimeline = (poi: RouteResponse['route'][number]) => {
    if (poi.is_coffee_break) return '☕'
    if (poi.emoji) return poi.emoji
    if (poi.category?.toLowerCase().includes('park')) return '🌳'
    if (poi.category?.toLowerCase().includes('museum')) return '🏛'
    return '📍'
  }

  const timelineEntries = useMemo(() => {
    if (!route.route.length) return []
    const firstArrival = new Date(route.route[0].arrival_time).getTime()
    return route.route.map(poi => {
      const arrivalTs = new Date(poi.arrival_time).getTime()
      const diffMinutes = Math.max(0, Math.round((arrivalTs - firstArrival) / 60000))
      const relativeHours = Math.floor(diffMinutes / 60)
      const relativeMinutes = diffMinutes % 60
      const relativeLabel = `${relativeHours}:${relativeMinutes.toString().padStart(2, '0')}`
      const labelPrefix = route.route[0].poi_id === poi.poi_id ? 'Начало в ' : ''
      return {
        id: poi.poi_id,
        emoji: emojiForTimeline(poi),
        label: `${labelPrefix}${poi.name}`,
        timeLabel: formatTime(poi.arrival_time),
        relativeLabel,
        active: activePoi === poi.poi_id,
        isBreak: poi.is_coffee_break,
      }
    })
  }, [route, activePoi])

  const shareUrl = typeof window === 'undefined' ? '' : window.location.href

  useEffect(() => {
    if (route.route.length) {
      setActivePoi(route.route[0].poi_id)
    }
  }, [route])

  const scrollToPoi = (poiId: number) => {
    const element = document.getElementById(`poi-${poiId}`)
    if (!element) return

    element.scrollIntoView({ behavior: 'smooth', block: 'center' })
    setExpandedPoi(poiId)
    setActivePoi(poiId)
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

  const handleTimelineHover = (poiId: number | null) => {
    if (poiId === null) {
      setActivePoi(route.route.length ? route.route[0].poi_id : null)
      return
    }
    setActivePoi(poiId)
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white/90 backdrop-blur-lg border-b border-emerald-100 sticky top-0 z-50 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <button
                onClick={onBackToHero}
                className="p-2 hover:bg-emerald-50 rounded-lg transition-colors"
                title="На главную"
              >
                <Home className="w-5 h-5 text-slate-600" />
              </button>
              <div className="h-6 w-px bg-emerald-100" />
              <div>
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-emerald-500" />
                  <h1 className="text-xl font-bold text-slate-900">
                    Ваш маршрут готов!
                  </h1>
                </div>
                <p className="text-xs text-slate-600 mt-0.5">
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
              <div className="hidden sm:flex items-center gap-1 p-1 bg-emerald-50 rounded-lg">
                <button
                  onClick={() => setView('map')}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                    view === 'map'
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <MapIcon className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setView('list')}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                    view === 'list'
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <List className="w-4 h-4" />
                </button>
              </div>

              <button
                onClick={handleShare}
                className="p-2 hover:bg-emerald-50 rounded-lg transition-colors"
                title="Поделиться"
              >
                <Share2 className="w-5 h-5 text-slate-600" />
              </button>
              <button
                onClick={() => window.print()}
                className="hidden sm:block p-2 hover:bg-emerald-50 rounded-lg transition-colors"
                title="Печать"
              >
                <Printer className="w-5 h-5 text-slate-600" />
              </button>
              <button
                onClick={onNewRoute}
                className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-sky-500 text-white font-semibold rounded-lg hover:shadow-lg hover:scale-105 transition-all"
              >
                Новый маршрут
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 space-y-6">
          <RouteShareCard
            title={route.summary}
            distance={route.total_distance_km}
            durationMinutes={route.total_est_minutes}
            shareUrl={shareUrl}
            weatherAdvice={route.weather_advice}
          />
          <ItineraryTimeline entries={timelineEntries} onHover={handleTimelineHover} />
        </div>
        <AnimatePresence mode="wait">
          {view === 'map' ? (
            <motion.div
              key="map-view"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="h-full"
            >
              <MapView
                route={route}
                geometry={geometry}
                onPoiFocus={scrollToPoi}
                formatTime={formatTime}
                activePoiId={activePoi}
              />
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
                onPoiHover={handleTimelineHover}
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
