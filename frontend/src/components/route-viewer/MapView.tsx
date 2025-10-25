import { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import { motion } from 'framer-motion'
import 'leaflet/dist/leaflet.css'
import type { RouteResponse } from '../../types'
import Leaflet from '../../lib/leaflet'

interface Props {
  route: RouteResponse
  geometry: [number, number][]
  onPoiFocus: (id: number) => void
  formatTime: (timestamp: string) => string
  activePoiId?: number | null
}

const MapBoundsAdjuster = ({ geometry }: { geometry: [number, number][] }) => {
  const map = useMap()

  useEffect(() => {
    if (!geometry.length) return
    const bounds = Leaflet.latLngBounds(geometry.map(([lat, lon]) => [lat, lon] as [number, number]))
    map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 })
  }, [geometry, map])

  return null
}

const StatsCard = ({ icon, value, label }: { icon: string; value: string | number; label: string }) => (
  <div className="text-center">
    <div className="text-xl sm:text-2xl mb-1">{icon}</div>
    <div className="text-base sm:text-lg font-bold text-slate-900">{value}</div>
    <div className="text-xs text-slate-600">{label}</div>
  </div>
)

const AnimatedPolyline = ({ positions }: { positions: [number, number][] }) => {
  const polylineRef = useRef<Leaflet.Polyline | null>(null)

  useEffect(() => {
    const polyline = polylineRef.current
    if (!polyline) return
    let frame = 0
    let offset = 0

    const tick = () => {
      if (!polylineRef.current) return
      offset = (offset - 1) % 800
      polylineRef.current.setStyle({ dashOffset: `${offset}` })
      frame = requestAnimationFrame(tick)
    }

    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [positions])

  return (
    <Polyline
      ref={polylineRef as unknown as any}
      positions={positions}
      pathOptions={{
        color: '#2563eb',
        weight: 4,
        opacity: 0.85,
        dashArray: '18 26',
        lineCap: 'round',
        lineJoin: 'round',
      }}
    />
  )
}

const resolveEmoji = (poi: RouteResponse['route'][number]) => {
  if (poi.is_coffee_break) return '☕'
  if (poi.emoji) return poi.emoji
  const category = poi.category?.toLowerCase() || ''
  const tags = (poi.tags || []).map(tag => tag.toLowerCase())
  if (tags.some(tag => tag.includes('набереж'))) return '🌉'
  if (tags.some(tag => tag.includes('арт') || tag.includes('art'))) return '🎨'
  if (category.includes('museum') || tags.some(tag => tag.includes('музей'))) return '🏛'
  if (category.includes('park') || tags.some(tag => tag.includes('парк'))) return '🌳'
  if (category.includes('monument') || category.includes('memorial') || tags.some(tag => tag.includes('история'))) return '🗿'
  return '📍'
}

const createEmojiMarker = (emoji: string, highlighted: boolean) => {
  const size = highlighted ? 44 : 36
  const shadow = highlighted ? '0 8px 20px rgba(56, 189, 248, 0.45)' : '0 4px 14px rgba(37, 99, 235, 0.35)'
  const background = highlighted
    ? 'linear-gradient(135deg, #34d399 0%, #38bdf8 100%)'
    : 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)'
  return Leaflet.divIcon({
    html: `<div style="
        width: ${size}px;
        height: ${size}px;
        background: ${background};
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        border: 3px solid #fff;
        box-shadow: ${shadow};
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <span style="transform: rotate(45deg); font-size: ${highlighted ? 22 : 18}px;">${emoji}</span>
      </div>`,
    className: '',
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size],
  })
}

export default function MapView({ route, geometry, onPoiFocus, formatTime, activePoiId = null }: Props) {
  const center = geometry[0] || [56.3287, 44.002]

  return (
    <div className="relative h-[calc(100vh-180px)] sm:h-[calc(100vh-140px)] md:h-[calc(100vh-100px)] overflow-hidden">
      <div className="absolute inset-0 bg-[#fef6d8]" />
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.18),transparent_55%)]" />
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_bottom,_rgba(248,180,0,0.18),transparent_60%)]" />

      <div className="relative h-full z-10">
        <MapContainer 
          center={center as [number, number]} 
          zoom={13} 
          style={{ height: '100%', width: '100%' }}
          zoomControl={true}
          scrollWheelZoom={true}
          doubleClickZoom={true}
          touchZoom={true}
        >
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />
          <MapBoundsAdjuster geometry={geometry} />
          <AnimatedPolyline positions={geometry} />

          {route.route.map(poi => {
            const emoji = resolveEmoji(poi)
            const icon = createEmojiMarker(emoji, activePoiId === poi.poi_id)
            return (
              <Marker
                key={poi.poi_id}
                position={[poi.lat, poi.lon]}
                icon={icon}
                eventHandlers={{ click: () => onPoiFocus(poi.poi_id) }}
              >
                <Popup 
                  maxWidth={280} 
                  minWidth={240} 
                  closeButton={true}
                  closeOnClick={false}
                  autoClose={false}
                  className="mobile-friendly-popup"
                >
                  <div className="p-2 sm:p-3 touch-pan-y">
                    <div className="flex items-start gap-2 mb-2">
                      <span className="flex items-center justify-center w-7 h-7 sm:w-8 sm:h-8 bg-gradient-to-br from-emerald-500 to-sky-500 text-white rounded-full text-xs sm:text-sm font-bold flex-shrink-0">
                        {poi.order}
                      </span>
                      <div className="flex-1 min-w-0">
                        <strong className="text-sm sm:text-base font-bold block leading-tight mb-1">{poi.name}</strong>
                        <span className="text-lg inline-block">{emoji}</span>
                      </div>
                    </div>
                    <p className="text-xs sm:text-sm text-slate-700 mb-2 leading-relaxed">{poi.why}</p>
                    {poi.tip && (
                      <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-2 mb-2">
                        <p className="text-xs text-emerald-900">💡 {poi.tip}</p>
                      </div>
                    )}
                    <div className="flex items-center gap-2 text-xs text-slate-600 bg-white/80 p-2 rounded flex-wrap">
                      <span className="whitespace-nowrap">🕐 {formatTime(poi.arrival_time)}</span>
                      <span>•</span>
                      <span className="whitespace-nowrap">⏱️ {poi.est_visit_minutes} мин</span>
                    </div>
                  </div>
                </Popup>
              </Marker>
            )
          })}
        </MapContainer>
      </div>

      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="hidden md:block absolute top-4 left-4 z-[1100] pointer-events-auto max-w-sm"
      >
        <div className="bg-white/90 backdrop-blur-md border border-emerald-100 rounded-xl px-4 py-3 shadow-lg">
          <p className="text-xs font-semibold text-slate-700">Нажмите на маркер для просмотра деталей</p>
          <p className="text-xs text-slate-500 mt-1">Маршрут показан анимированной линией</p>
        </div>
      </motion.div>

      <div className="absolute bottom-4 left-4 right-4 md:bottom-6 md:left-auto md:right-6 md:w-80 lg:w-96 z-[1100] pointer-events-none">
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="bg-white/95 backdrop-blur-lg border border-emerald-100 rounded-2xl p-4 sm:p-5 shadow-xl pointer-events-auto"
        >
          <h3 className="text-base sm:text-lg font-bold text-slate-900 mb-2 line-clamp-2">{route.summary}</h3>
          {route.atmospheric_description && (
            <p className="text-xs sm:text-sm text-slate-600 italic mb-3 line-clamp-2">{route.atmospheric_description}</p>
          )}
          <div className="grid grid-cols-3 gap-2 sm:gap-3">
            <StatsCard icon="📍" value={route.route.length} label="Точек" />
            <StatsCard
              icon="⏱️"
              value={`${Math.floor(route.total_est_minutes / 60)}ч ${route.total_est_minutes % 60}м`}
              label="Время"
            />
            <StatsCard icon="🚶" value={`${route.total_distance_km.toFixed(1)}`} label="км" />
          </div>
        </motion.div>
      </div>
    </div>
  )
}