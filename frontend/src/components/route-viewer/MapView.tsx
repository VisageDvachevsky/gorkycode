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
    map.fitBounds(bounds, { padding: [50, 50] })
  }, [geometry, map])

  return null
}

const StatsCard = ({ icon, value, label }: { icon: string; value: string | number; label: string }) => (
  <div className="text-center">
    <div className="text-2xl mb-1">{icon}</div>
    <div className="text-lg font-bold text-slate-900">{value}</div>
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
        weight: 5,
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
  const size = highlighted ? 48 : 40
  const shadow = highlighted ? '0 10px 24px rgba(56, 189, 248, 0.45)' : '0 6px 18px rgba(37, 99, 235, 0.35)'
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
        <span style="transform: rotate(45deg); font-size: ${highlighted ? 24 : 20}px;">${emoji}</span>
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
    <div className="relative h-[calc(100vh-80px)] overflow-hidden">
      <div className="absolute inset-0 bg-[#fef6d8]" />
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.18),transparent_55%)]" />
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_bottom,_rgba(248,180,0,0.18),transparent_60%)]" />

      <div className="relative h-full z-10">
        <MapContainer center={center as [number, number]} zoom={13} style={{ height: '100%', width: '100%' }}>
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
                <Popup maxWidth={320} className="custom-popup">
                  <div className="p-2">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="flex items-center justify-center w-8 h-8 bg-gradient-to-br from-emerald-500 to-sky-500 text-white rounded-full text-sm font-bold">
                        {poi.order}
                      </span>
                      <strong className="text-base">{poi.name}</strong>
                      <span className="text-lg">{emoji}</span>
                    </div>
                    <p className="text-sm text-slate-700 mb-2 leading-relaxed">{poi.why}</p>
                    {poi.tip && (
                      <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-2 mb-2">
                        <p className="text-xs text-emerald-900">💡 {poi.tip}</p>
                      </div>
                    )}
                    <div className="flex items-center gap-3 text-xs text-slate-600 bg-white/80 p-2 rounded">
                      <span>🕐 {formatTime(poi.arrival_time)}</span>
                      <span>•</span>
                      <span>⏱️ {poi.est_visit_minutes} мин</span>
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
        transition={{ delay: 0.6 }}
        className="absolute top-6 left-6 z-[1100] pointer-events-auto"
      >
        <div className="bg-white/90 backdrop-blur-md border border-emerald-100 rounded-2xl px-5 py-4 shadow-lg">
          <p className="text-sm font-semibold text-slate-700">Наводите курсор на карточку — на карте подсветится активная точка</p>
          <p className="text-xs text-slate-500 mt-1">Маршрут плавно проявляется, чтобы было легче ориентироваться</p>
        </div>
      </motion.div>

      <div className="absolute bottom-6 left-6 right-6 md:left-auto md:w-96 z-[1100] pointer-events-none">
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="bg-white/90 backdrop-blur-lg border border-emerald-100 rounded-2xl p-6 shadow-xl pointer-events-auto"
        >
          <h3 className="text-lg font-bold text-slate-900 mb-3">{route.summary}</h3>
          {route.atmospheric_description && (
            <p className="text-sm text-slate-600 italic mb-4">{route.atmospheric_description}</p>
          )}
          <div className="grid grid-cols-3 gap-3">
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
