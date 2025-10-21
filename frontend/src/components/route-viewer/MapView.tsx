import { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import { motion } from 'framer-motion'
import 'leaflet/dist/leaflet.css'
import type { RouteResponse } from '../../types'
import Leaflet, { coffeeMarkerIcon, defaultMarkerIcon } from '../../lib/leaflet'

interface Props {
  route: RouteResponse
  geometry: [number, number][]
  onPoiFocus: (id: number) => void
  formatTime: (timestamp: string) => string
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
    <div className="text-lg font-bold text-slate-900 dark:text-white">{value}</div>
    <div className="text-xs text-slate-600 dark:text-slate-400">{label}</div>
  </div>
)

export default function MapView({ route, geometry, onPoiFocus, formatTime }: Props) {
  const center = geometry[0] || [56.3287, 44.002]

  return (
    <div className="relative h-[calc(100vh-80px)]">
      <MapContainer center={center as [number, number]} zoom={13} style={{ height: '100%', width: '100%' }} className="z-0">
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />
        <MapBoundsAdjuster geometry={geometry} />

        <Polyline positions={geometry} color="#3B82F6" weight={4} opacity={0.7} dashArray="10, 10" />

        {route.route.map(poi => (
          <Marker
            key={poi.poi_id}
            position={[poi.lat, poi.lon]}
            icon={poi.is_coffee_break ? coffeeMarkerIcon : defaultMarkerIcon}
            eventHandlers={{ click: () => onPoiFocus(poi.poi_id) }}
          >
            <Popup maxWidth={320} className="custom-popup">
              <div className="p-2">
                <div className="flex items-center gap-2 mb-2">
                  <span className="flex items-center justify-center w-7 h-7 bg-gradient-to-br from-blue-600 to-indigo-600 text-white rounded-full text-sm font-bold">
                    {poi.order}
                  </span>
                  <strong className="text-base">{poi.name}</strong>
                  {poi.is_coffee_break && (
                    <span className="px-2 py-0.5 bg-amber-100 text-amber-800 text-xs font-semibold rounded-full">☕</span>
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

      <div className="absolute bottom-6 left-6 right-6 md:left-auto md:w-96 z-[1000] pointer-events-none">
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="glass-strong rounded-2xl p-6 shadow-2xl pointer-events-auto"
        >
          <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-3">{route.summary}</h3>
          {route.atmospheric_description && (
            <p className="text-sm text-slate-600 dark:text-slate-400 italic mb-4">{route.atmospheric_description}</p>
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
