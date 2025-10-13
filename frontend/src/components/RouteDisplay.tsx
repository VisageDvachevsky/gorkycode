import { useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { Share2, Printer, Clock, MapPin, Coffee, Calendar } from 'lucide-react'
import type { RouteResponse } from '../types'

// Fix Leaflet icons
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
  onNewRoute: () => void
}

export default function RouteDisplay({ route, onNewRoute }: Props) {
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
        <p className="text-xl text-blue-300/70">Персональная прогулка по Нижнему Новгороду</p>
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
        {[
          { icon: Clock, label: 'Длительность', value: `${hours > 0 ? `${hours}ч ` : ''}${minutes}м`, color: 'from-blue-500 to-cyan-500' },
          { icon: MapPin, label: 'Точек', value: route.route.length, color: 'from-green-500 to-emerald-500' },
          { icon: '🚶', label: 'Расстояние', value: `${route.total_distance_km.toFixed(1)} км`, color: 'from-purple-500 to-pink-500' },
          { icon: Coffee, label: 'Кофе-брейков', value: coffeeBreaksCount, color: 'from-amber-500 to-orange-500' },
        ].map((stat, i) => (
          <div key={i} className="group relative animate-fade-in" style={{ animationDelay: `${300 + i * 50}ms` }}>
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
                icon={poi.is_coffee_break ? coffeeIcon : L.icon({
                  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
                  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
                  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
                  iconSize: [25, 41],
                  iconAnchor: [12, 41],
                })}
                eventHandlers={{
                  click: () => scrollToPoi(poi.poi_id)
                }}
              >
                <Popup>
                  <div className="p-2">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="bg-gradient-to-r from-blue-600 to-purple-600 text-white w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold">
                        {poi.order}
                      </span>
                      <strong>{poi.name}</strong>
                      {poi.is_coffee_break && <span>☕</span>}
                    </div>
                    <p className="text-sm">{poi.why}</p>
                  </div>
                </Popup>
              </Marker>
            ))}
            
            <Polyline 
              positions={routeGeometry} 
              color="#3B82F6" 
              weight={6}
              opacity={0.8}
              dashArray="15, 10"
            />
          </MapContainer>
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-6">
        <h3 className="text-4xl font-black text-center bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent mb-8 animate-fade-in">
          Детальный план
        </h3>
        
        {route.route.map((poi, index) => (
          <div
            key={poi.poi_id}
            id={`poi-${poi.poi_id}`}
            className={`group relative animate-slide-in-up ${
              activePoiId === poi.poi_id ? 'scale-105' : ''
            }`}
            style={{ animationDelay: `${700 + index * 100}ms` }}
          >
            <div className={`absolute -inset-1 rounded-3xl opacity-30 group-hover:opacity-50 blur-xl transition-all ${
              poi.is_coffee_break 
                ? 'bg-gradient-to-r from-amber-600 to-orange-600' 
                : 'bg-gradient-to-r from-blue-600 to-purple-600'
            }`} />
            
            <div className={`relative backdrop-blur-2xl border-2 rounded-3xl p-8 transition-all ${
              poi.is_coffee_break
                ? 'bg-gradient-to-br from-amber-500/20 to-orange-500/20 border-amber-400/30 hover:border-amber-400/50'
                : 'bg-white/10 border-white/20 hover:border-white/40'
            }`}>
              <div className="flex items-start gap-6">
                {/* Number badge */}
                <div className="flex-shrink-0">
                  <div className={`w-20 h-20 rounded-3xl flex items-center justify-center text-white font-black text-3xl shadow-2xl transform group-hover:scale-110 transition-transform ${
                    poi.is_coffee_break 
                      ? 'bg-gradient-to-br from-amber-500 to-orange-600' 
                      : 'bg-gradient-to-br from-blue-600 to-purple-600'
                  }`}>
                    {poi.is_coffee_break ? '☕' : poi.order}
                  </div>
                </div>
                
                <div className="flex-1 min-w-0">
                  {/* Title */}
                  <div className="flex items-center gap-3 mb-4 flex-wrap">
                    <h4 className="font-black text-3xl text-white">{poi.name}</h4>
                    {poi.is_coffee_break && (
                      <span className="px-4 py-2 bg-amber-100 text-amber-900 text-sm font-bold rounded-full">
                        Кофе-брейк
                      </span>
                    )}
                  </div>
                  
                  {/* Description */}
                  <p className="text-lg text-blue-100 mb-6 leading-relaxed">{poi.why}</p>
                  
                  {/* Tip */}
                  {poi.tip && (
                    <div className={`mb-6 p-6 rounded-2xl border-2 ${
                      poi.is_coffee_break
                        ? 'bg-amber-900/20 border-amber-500/30'
                        : 'bg-blue-900/20 border-blue-500/30'
                    }`}>
                      <div className="flex items-start gap-3">
                        <span className="text-3xl">💡</span>
                        <p className="text-white">{poi.tip}</p>
                      </div>
                    </div>
                  )}
                  
                  {/* Time info */}
                  <div className="flex flex-wrap items-center gap-4">
                    <div className="flex items-center gap-3 px-6 py-3 bg-white/5 rounded-2xl border border-white/10">
                      <Clock className="w-5 h-5 text-blue-400" />
                      <span className="font-bold text-white">
                        {formatTime(poi.arrival_time)} - {formatTime(poi.leave_time)}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 px-6 py-3 bg-white/5 rounded-2xl border border-white/10">
                      <Calendar className="w-5 h-5 text-purple-400" />
                      <span className="font-bold text-white">{poi.est_visit_minutes} минут</span>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Connection line */}
              {index < route.route.length - 1 && (
                <div className="mt-8 pt-8 border-t-2 border-dashed border-white/20 flex items-center gap-4 text-blue-300/70">
                  <span className="text-3xl">👣</span>
                  <span className="font-medium">Переход к следующей точке</span>
                  <div className="flex-1 h-px bg-gradient-to-r from-blue-400/50 to-transparent" />
                </div>
              )}
            </div>
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
                <li key={i} className="flex items-start gap-4">
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
                className="w-full px-6 py-4 bg-white/5 border-2 border-white/10 rounded-2xl text-white font-mono text-sm mb-6"
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