import { useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { Share2, Printer, Clock, MapPin, Coffee } from 'lucide-react'
import type { RouteResponse } from '../types'

delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
})

const coffeeIcon = L.divIcon({
  html: `<div style="
    background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
    width: 40px;
    height: 40px;
    border-radius: 50% 50% 50% 0;
    transform: rotate(-45deg);
    border: 3px solid white;
    box-shadow: 0 4px 16px rgba(245, 158, 11, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
  ">
    <span style="
      transform: rotate(45deg);
      font-size: 22px;
      filter: drop-shadow(0 2px 2px rgba(0,0,0,0.2));
    ">☕</span>
  </div>`,
  className: '',
  iconSize: [40, 40],
  iconAnchor: [20, 40],
  popupAnchor: [0, -40]
})

interface Props {
  route: RouteResponse
}

export default function RouteDisplay({ route }: Props) {
  const [activePoiId, setActivePoiId] = useState<number | null>(null)
  const [showShareModal, setShowShareModal] = useState(false)

  const positions = route.route.map((poi) => [poi.lat, poi.lon] as [number, number])
  const center = positions[0] || [56.3287, 44.002]
  
  const routeGeometry = route.route_geometry && route.route_geometry.length > 0
    ? route.route_geometry.map(coord => [coord[0], coord[1]] as [number, number])
    : positions

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const hours = Math.floor(route.total_est_minutes / 60)
  const minutes = route.total_est_minutes % 60
  const coffeeBreaksCount = route.route.filter(poi => poi.is_coffee_break).length

  const scrollToPoi = (poiId: number) => {
    const element = document.getElementById(`poi-${poiId}`)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' })
      setActivePoiId(poiId)
      setTimeout(() => setActivePoiId(null), 2000)
    }
  }

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

  const stats = [
    {
      id: 'duration',
      icon: Clock,
      label: 'Длительность',
      value: `${hours > 0 ? `${hours}ч ` : ''}${minutes}м`,
      color: 'from-blue-500 to-cyan-500'
    },
    {
      id: 'points',
      icon: MapPin,
      label: 'Точек',
      value: route.route.length,
      color: 'from-green-500 to-emerald-500'
    },
    {
      id: 'distance',
      icon: '🚶',
      label: 'Расстояние',
      value: `${route.total_distance_km.toFixed(1)} км`,
      color: 'from-purple-500 to-pink-500'
    },
    {
      id: 'coffee',
      icon: Coffee,
      label: 'Кофе-брейков',
      value: coffeeBreaksCount,
      color: 'from-amber-500 to-orange-500'
    }
  ]

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="text-center mb-12 animate-fade-in">
        <div className="inline-block mb-6">
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-green-500 to-emerald-500 rounded-full blur-2xl opacity-50 animate-pulse-glow" />
            <div className="relative text-8xl animate-bounce-slow">
              ✨
            </div>
          </div>
        </div>
        <h2 className="text-5xl sm:text-6xl md:text-7xl font-black bg-gradient-to-r from-green-400 via-emerald-400 to-cyan-400 bg-clip-text text-transparent mb-4 animate-gradient">
          Ваш маршрут готов!
        </h2>
        <p className="text-xl text-blue-300/80">Персональная прогулка по Нижнему Новгороду</p>
      </div>

      {/* Action buttons */}
      <div className="flex flex-wrap gap-4 justify-center animate-fade-in" style={{ animationDelay: '100ms' }}>
        <button
          onClick={handleShare}
          className="group relative px-8 py-4 font-bold text-white overflow-hidden rounded-2xl transition-all hover:scale-105"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-cyan-600" />
          <span className="relative flex items-center gap-3">
            <Share2 className="w-5 h-5" />
            Поделиться
          </span>
        </button>
        <button
          onClick={() => window.print()}
          className="group relative px-8 py-4 font-bold text-white overflow-hidden rounded-2xl transition-all hover:scale-105"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-purple-600 to-pink-600" />
          <span className="relative flex items-center gap-3">
            <Printer className="w-5 h-5" />
            Печать
          </span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 animate-slide-in-up" style={{ animationDelay: '200ms' }}>
        {stats.map((stat, index) => (
          <div
            key={stat.id}
            className="group relative animate-fade-in"
            style={{ animationDelay: `${300 + index * 50}ms` }}
          >
            <div className={`absolute -inset-0.5 bg-gradient-to-r ${stat.color} rounded-3xl opacity-20 group-hover:opacity-40 blur transition-all`} />
            <div className="relative backdrop-blur-2xl bg-white/10 border border-white/20 rounded-3xl p-6 hover:border-white/40 transition-all">
              <div className="flex items-center gap-3 mb-3">
                {typeof stat.icon === 'string' ? (
                  <span className="text-4xl">{stat.icon}</span>
                ) : (
                  <stat.icon className="w-8 h-8 text-white" />
                )}
              </div>
              <div className="text-4xl font-black text-white mb-1">{stat.value}</div>
              <div className="text-sm text-blue-300/70">{stat.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Summary */}
      {route.summary && (
        <div className="group relative animate-slide-in-left" style={{ animationDelay: '400ms' }}>
          <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-600 to-purple-600 rounded-3xl opacity-20 group-hover:opacity-40 blur transition-all" />
          <div className="relative backdrop-blur-2xl bg-white/10 border border-white/20 rounded-3xl p-8 hover:border-white/40 transition-all">
            <div className="flex items-start gap-4">
              <span className="text-5xl">🗺️</span>
              <p className="text-xl text-white leading-relaxed">{route.summary}</p>
            </div>
          </div>
        </div>
      )}

      {/* Atmospheric description */}
      {route.atmospheric_description && (
        <div className="group relative animate-slide-in-right" style={{ animationDelay: '500ms' }}>
          <div className="absolute -inset-0.5 bg-gradient-to-r from-amber-600 to-orange-600 rounded-3xl opacity-20 group-hover:opacity-40 blur transition-all" />
          <div className="relative backdrop-blur-2xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-400/30 rounded-3xl p-8 hover:border-amber-400/50 transition-all">
            <div className="flex items-start gap-4">
              <span className="text-5xl">✨</span>
              <p className="text-xl text-amber-100 italic leading-relaxed">{route.atmospheric_description}</p>
            </div>
          </div>
        </div>
      )}

      {/* Map */}
      <div className="group relative animate-fade-in" style={{ animationDelay: '600ms' }}>
        <div className="absolute -inset-1 bg-gradient-to-r from-cyan-600 via-blue-600 to-purple-600 rounded-3xl opacity-30 group-hover:opacity-50 blur-xl transition-all" />
        <div className="relative h-[600px] rounded-3xl overflow-hidden border-4 border-white/20 shadow-2xl">
          <MapContainer 
            center={center} 
            zoom={13} 
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; OpenStreetMap'
            />
            
            {route.route.map((poi) => (
              <Marker 
                key={poi.poi_id}
                position={[poi.lat, poi.lon]}
                icon={poi.is_coffee_break ? coffeeIcon : new L.Icon.Default()}
              >
                <Popup>
                  <div className="text-center">
                    <h3 className="font-bold text-lg mb-1">{poi.name}</h3>
                    {poi.category && <p className="text-sm text-gray-600 mb-2">{poi.category}</p>}
                    {poi.is_coffee_break && (
                      <div className="text-orange-600 font-bold text-sm">☕ Кофе-брейк</div>
                    )}
                    <button
                      onClick={() => scrollToPoi(poi.poi_id)}
                      className="mt-2 px-4 py-1 bg-blue-500 text-white rounded-full text-sm hover:bg-blue-600 transition-colors"
                    >
                      Подробнее
                    </button>
                  </div>
                </Popup>
              </Marker>
            ))}
            
            {routeGeometry.length > 0 && (
              <Polyline 
                positions={routeGeometry} 
                color="#3B82F6" 
                weight={4}
                opacity={0.7}
              />
            )}
          </MapContainer>
        </div>
      </div>

      {/* Route points */}
      <div className="space-y-6 animate-fade-in" style={{ animationDelay: '700ms' }}>
        <h3 className="text-4xl font-black text-white mb-8 flex items-center gap-4">
          <span className="text-5xl">📍</span>
          Точки маршрута
        </h3>

        {route.route.map((poi, index) => (
          <div key={poi.poi_id}>
            <div
              id={`poi-${poi.poi_id}`}
              className={`group relative transition-all ${
                activePoiId === poi.poi_id ? 'scale-105' : ''
              }`}
            >
              <div className={`absolute -inset-1 bg-gradient-to-r ${
                poi.is_coffee_break
                  ? 'from-amber-600 to-orange-600'
                  : 'from-blue-600 via-purple-600 to-pink-600'
              } rounded-3xl opacity-20 group-hover:opacity-40 blur-xl transition-all`} />
              
              <div className={`relative backdrop-blur-2xl border-2 rounded-3xl p-8 hover:border-white/40 transition-all ${
                poi.is_coffee_break
                  ? 'bg-gradient-to-br from-amber-500/20 to-orange-500/20 border-amber-400/30'
                  : 'bg-white/10 border-white/20'
              }`}>
                {/* Header */}
                <div className="flex items-start gap-6 mb-6">
                  <div className="relative flex-shrink-0">
                    <div className={`absolute inset-0 bg-gradient-to-r ${
                      poi.is_coffee_break
                        ? 'from-amber-500 to-orange-500'
                        : 'from-blue-500 to-purple-500'
                    } rounded-2xl blur-lg opacity-50`} />
                    <div className={`relative w-20 h-20 rounded-2xl bg-gradient-to-br ${
                      poi.is_coffee_break
                        ? 'from-amber-500 to-orange-500'
                        : 'from-blue-500 to-purple-500'
                    } flex items-center justify-center text-4xl font-black text-white shadow-2xl`}>
                      {poi.is_coffee_break ? '☕' : index + 1}
                    </div>
                  </div>

                  <div className="flex-1">
                    <div className="flex items-start justify-between gap-4 mb-3">
                      <div>
                        <h4 className="text-3xl font-black text-white mb-2">{poi.name}</h4>
                        {poi.category && (
                          <span className={`inline-block px-4 py-2 rounded-full text-sm font-bold ${
                            poi.is_coffee_break
                              ? 'bg-amber-500/30 text-amber-200'
                              : 'bg-blue-500/30 text-blue-200'
                          }`}>
                            {poi.category}
                          </span>
                        )}
                      </div>
                      {poi.rating && (
                        <div className="flex items-center gap-2 px-4 py-2 bg-yellow-500/20 rounded-full">
                          <span className="text-2xl">⭐</span>
                          <span className="text-lg font-bold text-yellow-200">{poi.rating.toFixed(1)}</span>
                        </div>
                      )}
                    </div>

                    {poi.est_arrival && (
                      <div className="flex items-center gap-3 text-blue-300">
                        <Clock className="w-5 h-5" />
                        <span className="font-semibold">{formatTime(poi.est_arrival)}</span>
                        {poi.est_duration_minutes && (
                          <span className="text-blue-300/70">• {poi.est_duration_minutes} мин</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Description */}
                {poi.description && (
                  <div className="mb-6 p-6 bg-slate-900/50 rounded-2xl border border-white/10">
                    <p className="text-lg text-blue-100 leading-relaxed">{poi.description}</p>
                  </div>
                )}

                {/* AI Explanation */}
                {poi.ai_why && (
                  <div className="mb-6 p-6 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-2xl border border-purple-400/30">
                    <div className="flex items-start gap-3 mb-3">
                      <span className="text-3xl">🤖</span>
                      <h5 className="text-xl font-bold text-purple-200">Почему это место для вас:</h5>
                    </div>
                    <p className="text-lg text-purple-100 leading-relaxed pl-12">{poi.ai_why}</p>
                  </div>
                )}

                {/* AI Tip */}
                {poi.ai_tip && (
                  <div className="p-6 bg-gradient-to-br from-cyan-500/10 to-blue-500/10 rounded-2xl border border-cyan-400/30">
                    <div className="flex items-start gap-3">
                      <span className="text-3xl">💡</span>
                      <div>
                        <h5 className="text-xl font-bold text-cyan-200 mb-2">Совет:</h5>
                        <p className="text-lg text-cyan-100 leading-relaxed">{poi.ai_tip}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Transit info */}
            {index < route.route.length - 1 && (
              <div className="flex items-center gap-4 my-6 px-8 animate-fade-in">
                <div className="flex-1 h-px bg-gradient-to-r from-transparent via-blue-400/50 to-transparent" />
                <span className="font-medium text-blue-300">Переход к следующей точке</span>
                <div className="flex-1 h-px bg-gradient-to-r from-blue-400/50 to-transparent" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Notes */}
      {route.notes && route.notes.length > 0 && (
        <div className="group relative animate-fade-in" style={{ animationDelay: '1000ms' }}>
          <div className="absolute -inset-1 bg-gradient-to-r from-yellow-600 to-amber-600 rounded-3xl opacity-30 group-hover:opacity-50 blur-xl transition-all" />
          <div className="relative backdrop-blur-2xl bg-gradient-to-br from-yellow-500/20 to-amber-500/20 border-2 border-yellow-400/30 rounded-3xl p-8 hover:border-yellow-400/50 transition-all">
            <h4 className="flex items-center gap-3 font-black text-3xl text-white mb-6">
              <span className="text-4xl">📝</span>
              Полезные заметки
            </h4>
            <ul className="space-y-4">
              {route.notes.map((note, i) => (
                <li key={`note-${i}-${note.substring(0, 20)}`} className="flex items-start gap-4">
                  <span className="text-yellow-400 text-2xl mt-1">•</span>
                  <span className="text-lg text-yellow-100 leading-relaxed">{note}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Share Modal */}
      {showShareModal && (
        <div 
          className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in"
          onClick={() => setShowShareModal(false)}
        >
          <div 
            className="relative max-w-md w-full animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-3xl opacity-50 blur-xl" />
            <div className="relative backdrop-blur-2xl bg-slate-900 border-2 border-white/20 rounded-3xl p-8">
              <h3 className="text-3xl font-black text-white mb-6">Поделиться маршрутом</h3>
              <p className="text-blue-300 mb-4">Скопируйте ссылку:</p>
              <input
                type="text"
                value={window.location.href}
                readOnly
                className="w-full px-6 py-4 bg-slate-900/50 border-2 border-blue-500/30 rounded-2xl text-white font-mono text-sm mb-6 focus:ring-4 focus:ring-blue-500/30 focus:border-blue-500/50 transition-all"
                onClick={(e) => (e.target as HTMLInputElement).select()}
              />
              <button
                onClick={() => {
                  navigator.clipboard.writeText(window.location.href)
                  setShowShareModal(false)
                }}
                className="group relative w-full py-4 font-bold text-white overflow-hidden rounded-2xl transition-all hover:scale-105"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-purple-600" />
                <span className="relative">Копировать ссылку</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}