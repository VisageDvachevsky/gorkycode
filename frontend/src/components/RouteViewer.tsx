import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import L from 'leaflet'
import {
  Home,
  ArrowLeft,
  Share2,
  Download,
  Printer,
  MapIcon,
  List,
  Clock,
  Navigation,
  Coffee,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Sparkles,
} from 'lucide-react'
import type { RouteResponse, POIInRoute } from '../types'
import 'leaflet/dist/leaflet.css'

// Fix Leaflet icons
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
})

// Custom coffee marker
const coffeeIcon = L.divIcon({
  html: `<div class="coffee-marker" style="
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
    border-radius: 50% 50% 50% 0;
    transform: rotate(-45deg);
    border: 3px solid white;
    box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
  ">
    <span style="transform: rotate(45deg); font-size: 22px;">☕</span>
  </div>`,
  className: '',
  iconSize: [40, 40],
  iconAnchor: [20, 40],
  popupAnchor: [0, -40],
})

// Map bounds adjuster
function MapBoundsAdjuster({ geometry }: { geometry: number[][] }) {
  const map = useMap()
  
  useEffect(() => {
    if (geometry.length > 0) {
      const bounds = L.latLngBounds(geometry.map(coord => [coord[0], coord[1]] as [number, number]))
      map.fitBounds(bounds, { padding: [50, 50] })
    }
  }, [geometry, map])
  
  return null
}

interface Props {
  route: RouteResponse
  onNewRoute: () => void
  onBackToHero: () => void
}

export default function RouteViewer({ route, onNewRoute, onBackToHero }: Props) {
  const [view, setView] = useState<'map' | 'list'>('map')
  const [expandedPoi, setExpandedPoi] = useState<number | null>(null)
  const [showShareModal, setShowShareModal] = useState(false)
  const timelineRef = useRef<HTMLDivElement>(null)

  const scrollToPoi = (poiId: number) => {
    const element = document.getElementById(`poi-${poiId}`)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' })
      setExpandedPoi(poiId)
      setTimeout(() => setExpandedPoi(null), 3000)
    }
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const hours = Math.floor(route.total_est_minutes / 60)
  const minutes = route.total_est_minutes % 60
  const coffeeBreaksCount = route.route.filter(poi => poi.is_coffee_break).length

  const routeGeometry = route.route_geometry && route.route_geometry.length > 0
    ? route.route_geometry.map(coord => [coord[0], coord[1]] as [number, number])
    : route.route.map(poi => [poi.lat, poi.lon] as [number, number])

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: 'Мой маршрут по Нижнему Новгороду',
        text: route.summary,
        url: window.location.href,
      })
    } else {
      setShowShareModal(true)
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
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
                  {route.route.length} точек • {hours > 0 && `${hours}ч `}{minutes}м • {route.total_distance_km.toFixed(1)} км
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* View Toggle */}
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

              {/* Action Buttons */}
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

      {/* Main Content */}
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
              <MapView
                route={route}
                routeGeometry={routeGeometry}
                scrollToPoi={scrollToPoi}
                formatTime={formatTime}
                coffeeIcon={coffeeIcon}
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
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Share Modal */}
      <AnimatePresence>
        {showShareModal && (
          <ShareModal onClose={() => setShowShareModal(false)} />
        )}
      </AnimatePresence>
    </div>
  )
}

// Map View Component
function MapView({
  route,
  routeGeometry,
  scrollToPoi,
  formatTime,
  coffeeIcon,
}: {
  route: RouteResponse
  routeGeometry: [number, number][]
  scrollToPoi: (id: number) => void
  formatTime: (time: string) => string
  coffeeIcon: L.DivIcon
}) {
  const center = routeGeometry[0] || [56.3287, 44.002]

  return (
    <div className="relative h-[calc(100vh-80px)]">
      <MapContainer
        center={center as [number, number]}
        zoom={13}
        style={{ height: '100%', width: '100%' }}
        className="z-0"
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; OpenStreetMap'
        />
        <MapBoundsAdjuster geometry={routeGeometry} />
        
        {/* Route Line */}
        <Polyline
          positions={routeGeometry}
          color="#3B82F6"
          weight={4}
          opacity={0.7}
          dashArray="10, 10"
        />

        {/* POI Markers */}
        {route.route.map((poi) => (
          <Marker
            key={poi.poi_id}
            position={[poi.lat, poi.lon]}
            icon={poi.is_coffee_break ? coffeeIcon : L.icon(L.Icon.Default.prototype.options)}
            eventHandlers={{ click: () => scrollToPoi(poi.poi_id) }}
          >
            <Popup maxWidth={320} className="custom-popup">
              <div className="p-2">
                <div className="flex items-center gap-2 mb-2">
                  <span className="flex items-center justify-center w-7 h-7 bg-gradient-to-br from-blue-600 to-indigo-600 text-white rounded-full text-sm font-bold">
                    {poi.order}
                  </span>
                  <strong className="text-base">{poi.name}</strong>
                  {poi.is_coffee_break && (
                    <span className="px-2 py-0.5 bg-amber-100 text-amber-800 text-xs font-semibold rounded-full">
                      ☕
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-700 mb-2 leading-relaxed">{poi.why}</p>
                {poi.tip && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-2 mb-2">
                    <p className="text-xs text-blue-900">💡 {poi.tip}</p>
                  </div>
                )}
                <div className="flex items-center gap-3 text-xs text-slate-600 bg-slate-50 p-2 rounded">
                  <span>🕐 {formatTime(poi.arrival_time)}</span>
                  <span>•</span>
                  <span>⏱️ {poi.est_visit_minutes} мин</span>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {/* Floating Summary Card */}
      <div className="absolute bottom-6 left-6 right-6 md:left-auto md:w-96 z-[1000] pointer-events-none">
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="glass-strong rounded-2xl p-6 shadow-2xl pointer-events-auto"
        >
          <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-3">
            {route.summary}
          </h3>
          {route.atmospheric_description && (
            <p className="text-sm text-slate-600 dark:text-slate-400 italic mb-4">
              {route.atmospheric_description}
            </p>
          )}
          <div className="grid grid-cols-3 gap-3">
            <StatsCard icon="📍" value={route.route.length} label="Точек" />
            <StatsCard icon="⏱️" value={`${Math.floor(route.total_est_minutes / 60)}ч ${route.total_est_minutes % 60}м`} label="Время" />
            <StatsCard icon="🚶" value={`${route.total_distance_km.toFixed(1)}`} label="км" />
          </div>
        </motion.div>
      </div>
    </div>
  )
}

function StatsCard({ icon, value, label }: { icon: string; value: string | number; label: string }) {
  return (
    <div className="text-center">
      <div className="text-2xl mb-1">{icon}</div>
      <div className="text-lg font-bold text-slate-900 dark:text-white">{value}</div>
      <div className="text-xs text-slate-600 dark:text-slate-400">{label}</div>
    </div>
  )
}

// List View Component  
function ListView({
  route,
  expandedPoi,
  setExpandedPoi,
  formatTime,
  timelineRef,
}: {
  route: RouteResponse
  expandedPoi: number | null
  setExpandedPoi: (id: number | null) => void
  formatTime: (time: string) => string
  timelineRef: React.RefObject<HTMLDivElement>
}) {
  return (
    <div className="space-y-6">
      {/* Summary */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-blue-900/20 dark:via-indigo-900/20 dark:to-purple-900/20 border-2 border-blue-200 dark:border-blue-800 rounded-2xl p-6"
      >
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-3">
          {route.summary}
        </h2>
        {route.atmospheric_description && (
          <p className="text-lg text-slate-700 dark:text-slate-300 italic leading-relaxed">
            ✨ {route.atmospheric_description}
          </p>
        )}
      </motion.div>

      {/* Timeline */}
      <div ref={timelineRef} className="space-y-4">
        {route.route.map((poi, index) => (
          <motion.div
            key={poi.poi_id}
            id={`poi-${poi.poi_id}`}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            className={`relative ${expandedPoi === poi.poi_id ? 'ring-4 ring-blue-300 dark:ring-blue-700' : ''}`}
          >
            <POICard
              poi={poi}
              index={index}
              isExpanded={expandedPoi === poi.poi_id}
              onToggle={() => setExpandedPoi(expandedPoi === poi.poi_id ? null : poi.poi_id)}
              formatTime={formatTime}
              isLast={index === route.route.length - 1}
            />
          </motion.div>
        ))}
      </div>

      {/* Notes */}
      {route.notes && route.notes.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-amber-50 dark:bg-amber-900/20 border-2 border-amber-200 dark:border-amber-800 rounded-2xl p-6"
        >
          <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">
            📝 Полезные заметки
          </h3>
          <ul className="space-y-2">
            {route.notes.map((note, i) => (
              <li key={i} className="flex items-start gap-3 text-sm text-slate-700 dark:text-slate-300">
                <span className="text-amber-600 dark:text-amber-400 mt-0.5">•</span>
                <span>{note}</span>
              </li>
            ))}
          </ul>
        </motion.div>
      )}
    </div>
  )
}

// POI Card Component
function POICard({
  poi,
  index,
  isExpanded,
  onToggle,
  formatTime,
  isLast,
}: {
  poi: POIInRoute
  index: number
  isExpanded: boolean
  onToggle: () => void
  formatTime: (time: string) => string
  isLast: boolean
}) {
  return (
    <div
      className={`bg-white dark:bg-slate-800 border-2 rounded-2xl overflow-hidden transition-all ${
        poi.is_coffee_break
          ? 'border-amber-300 dark:border-amber-700'
          : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
      } ${isExpanded ? 'shadow-2xl scale-[1.02]' : 'shadow-lg hover:shadow-xl'}`}
    >
      <button
        onClick={onToggle}
        className="w-full p-6 text-left"
      >
        <div className="flex items-start gap-4">
          {/* Order Badge */}
          <div
            className={`flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-lg shadow-lg ${
              poi.is_coffee_break
                ? 'bg-gradient-to-br from-amber-500 to-orange-600'
                : 'bg-gradient-to-br from-blue-600 to-indigo-600'
            }`}
          >
            {poi.is_coffee_break ? '☕' : poi.order}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-4 mb-2">
              <div>
                <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-1">
                  {poi.name}
                </h3>
                <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                  <span className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    {formatTime(poi.arrival_time)} - {formatTime(poi.leave_time)}
                  </span>
                  <span>•</span>
                  <span>{poi.est_visit_minutes} минут</span>
                  {poi.is_coffee_break && (
                    <>
                      <span>•</span>
                      <span className="px-2 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-full text-xs font-semibold">
                        Кофе-брейк
                      </span>
                    </>
                  )}
                </div>
              </div>
              {isExpanded ? (
                <ChevronUp className="w-5 h-5 text-slate-400 flex-shrink-0" />
              ) : (
                <ChevronDown className="w-5 h-5 text-slate-400 flex-shrink-0" />
              )}
            </div>

            <p className="text-slate-700 dark:text-slate-300 leading-relaxed">
              {poi.why}
            </p>
          </div>
        </div>
      </button>

      <AnimatePresence>
        {isExpanded && poi.tip && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t-2 border-slate-100 dark:border-slate-700 px-6 pb-6"
          >
            <div className="pt-4 bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500 rounded-r-lg p-4">
              <p className="text-sm text-blue-900 dark:text-blue-100">
                <strong className="font-bold">💡 Совет:</strong> {poi.tip}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {!isLast && (
        <div className="px-6 pb-4 flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
          <Navigation className="w-4 h-4" />
          <span>Переход к следующей точке</span>
          <div className="flex-1 h-px bg-gradient-to-r from-slate-300 dark:from-slate-700 to-transparent" />
        </div>
      )}
    </div>
  )
}

// Share Modal Component
function ShareModal({ onClose }: { onClose: () => void }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => {
      setCopied(false)
      onClose()
    }, 1500)
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white dark:bg-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl"
      >
        <h3 className="text-2xl font-bold text-slate-900 dark:text-white mb-4">
          Поделиться маршрутом
        </h3>
        <p className="text-slate-600 dark:text-slate-400 mb-4">
          Скопируйте ссылку:
        </p>
        <input
          type="text"
          value={window.location.href}
          readOnly
          className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border-2 border-slate-200 dark:border-slate-700 rounded-xl font-mono text-sm mb-4"
          onClick={(e) => (e.target as HTMLInputElement).select()}
        />
        <button
          onClick={handleCopy}
          className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3 rounded-xl font-semibold hover:shadow-lg transition-all"
        >
          {copied ? '✓ Скопировано!' : 'Копировать ссылку'}
        </button>
      </motion.div>
    </motion.div>
  )
}