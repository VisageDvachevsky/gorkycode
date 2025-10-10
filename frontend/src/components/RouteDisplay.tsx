import { useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import type { RouteResponse } from '../types'

delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
})

const defaultIcon = L.icon({
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
})

const coffeeIcon = L.icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-orange.png',
  iconRetinaUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-orange.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
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

  const handlePrint = () => {
    window.print()
  }

  const scrollToPoi = (poiId: number) => {
    const element = document.getElementById(`poi-${poiId}`)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' })
      setActivePoiId(poiId)
      setTimeout(() => setActivePoiId(null), 2000)
    }
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header with actions */}
      <div className="bg-white rounded-2xl shadow-xl p-6 print:shadow-none">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b pb-6 mb-6">
          <div>
            <h2 className="text-3xl md:text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600 mb-2">
              Ваш маршрут
            </h2>
            <p className="text-gray-500">Персональная прогулка готова</p>
          </div>
          
          <div className="flex flex-wrap gap-2 print:hidden">
            <button
              onClick={onNewRoute}
              className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-semibold hover:shadow-lg transform hover:scale-105 transition-all duration-200"
            >
              ← Новый маршрут
            </button>
            <button
              onClick={handleShare}
              className="px-4 py-2 bg-white border-2 border-gray-200 text-gray-700 rounded-xl font-semibold hover:border-blue-600 hover:text-blue-600 transition-all duration-200"
            >
              📤 Поделиться
            </button>
            <button
              onClick={handlePrint}
              className="px-4 py-2 bg-white border-2 border-gray-200 text-gray-700 rounded-xl font-semibold hover:border-blue-600 hover:text-blue-600 transition-all duration-200"
            >
              🖨️ Печать
            </button>
          </div>
        </div>
        
        {/* Stats cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="relative overflow-hidden bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-4 transform hover:scale-105 transition-all duration-200 hover:shadow-md">
            <div className="flex items-center gap-3">
              <div className="text-4xl">⏱️</div>
              <div>
                <div className="text-2xl font-bold text-blue-900">
                  {hours > 0 && `${hours}ч `}{minutes}м
                </div>
                <div className="text-xs text-blue-700">Длительность</div>
              </div>
            </div>
            <div className="absolute -right-4 -bottom-4 text-8xl opacity-10">⏱️</div>
          </div>
          
          <div className="relative overflow-hidden bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-4 transform hover:scale-105 transition-all duration-200 hover:shadow-md">
            <div className="flex items-center gap-3">
              <div className="text-4xl">📍</div>
              <div>
                <div className="text-2xl font-bold text-green-900">{route.route.length}</div>
                <div className="text-xs text-green-700">Мест</div>
              </div>
            </div>
            <div className="absolute -right-4 -bottom-4 text-8xl opacity-10">📍</div>
          </div>
          
          <div className="relative overflow-hidden bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-4 transform hover:scale-105 transition-all duration-200 hover:shadow-md">
            <div className="flex items-center gap-3">
              <div className="text-4xl">🚶</div>
              <div>
                <div className="text-2xl font-bold text-purple-900">{route.total_distance_km.toFixed(1)} км</div>
                <div className="text-xs text-purple-700">Расстояние</div>
              </div>
            </div>
            <div className="absolute -right-4 -bottom-4 text-8xl opacity-10">🚶</div>
          </div>
        </div>
        
        {/* Summary */}
        {route.summary && (
          <div className="mb-6 p-6 bg-gradient-to-r from-blue-50 via-indigo-50 to-purple-50 rounded-2xl border-2 border-blue-200 animate-slideInLeft">
            <div className="flex items-start gap-3">
              <span className="text-3xl">🗺️</span>
              <p className="text-gray-800 leading-relaxed text-lg">{route.summary}</p>
            </div>
          </div>
        )}

        {/* Atmospheric description */}
        {route.atmospheric_description && (
          <div className="p-6 bg-gradient-to-r from-amber-50 via-orange-50 to-yellow-50 rounded-2xl border-2 border-amber-200 animate-slideInRight">
            <div className="flex items-start gap-3">
              <span className="text-3xl">✨</span>
              <p className="text-gray-800 italic leading-relaxed text-lg">{route.atmospheric_description}</p>
            </div>
          </div>
        )}
      </div>

      {/* Interactive Map */}
      <div className="bg-white rounded-2xl shadow-xl overflow-hidden print:break-inside-avoid animate-fadeIn">
        <div className="h-[600px] relative">
          <MapContainer 
            center={center} 
            zoom={13} 
            style={{ height: '100%', width: '100%' }}
            className="z-0"
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            />
            {route.route.map((poi) => (
              <Marker 
                key={poi.poi_id}
                position={[poi.lat, poi.lon]}
                icon={poi.is_coffee_break ? coffeeIcon : defaultIcon}
                eventHandlers={{
                  click: () => scrollToPoi(poi.poi_id)
                }}
              >
                <Popup>
                  <div className="text-sm max-w-xs p-2">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shadow-md">
                        {poi.order}
                      </span>
                      <strong className="text-base text-gray-900">{poi.name}</strong>
                      {poi.is_coffee_break && <span className="text-xl">☕</span>}
                    </div>
                    <p className="text-gray-700 mb-3 leading-relaxed">{poi.why}</p>
                    {poi.tip && (
                      <div className="bg-blue-50 border border-blue-200 p-3 rounded-lg mb-2">
                        <p className="text-sm text-blue-900">💡 {poi.tip}</p>
                      </div>
                    )}
                    <div className="flex items-center gap-3 text-xs text-gray-600 bg-gray-50 p-2 rounded">
                      <span>🕐 {formatTime(poi.arrival_time)}</span>
                      <span>•</span>
                      <span>⏱️ {poi.est_visit_minutes} мин</span>
                    </div>
                  </div>
                </Popup>
              </Marker>
            ))}
            <Polyline 
              positions={routeGeometry} 
              color="#3B82F6" 
              weight={5}
              opacity={0.7}
              dashArray="10, 10"
              className="animate-dashOffset"
            />
          </MapContainer>
        </div>
      </div>

      {/* Route Timeline */}
      <div className="bg-white rounded-2xl shadow-xl p-6 print:shadow-none">
        <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-3">
          <span className="text-3xl">📋</span>
          Детальный план
        </h3>
        
        <div className="space-y-4">
          {route.route.map((poi, index) => (
            <div
              key={poi.poi_id}
              id={`poi-${poi.poi_id}`}
              className={`group relative border-2 rounded-2xl p-6 transition-all duration-300 hover:shadow-xl ${
                activePoiId === poi.poi_id 
                  ? 'ring-4 ring-blue-300 border-blue-500 scale-[1.02]' 
                  : poi.is_coffee_break 
                    ? 'bg-gradient-to-r from-amber-50 to-orange-50 border-amber-300 hover:border-amber-400' 
                    : 'bg-gradient-to-r from-gray-50 to-white border-gray-200 hover:border-gray-300'
              } animate-slideInUp`}
              style={{ animationDelay: `${index * 100}ms` }}
            >
              <div className="flex items-start gap-4">
                {/* Step number */}
                <div className="flex-shrink-0">
                  <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-white font-black text-xl shadow-lg transform group-hover:scale-110 transition-transform ${
                    poi.is_coffee_break 
                      ? 'bg-gradient-to-br from-amber-500 to-orange-600' 
                      : 'bg-gradient-to-br from-blue-600 to-indigo-600'
                  }`}>
                    {poi.order}
                  </div>
                </div>
                
                <div className="flex-1 min-w-0">
                  {/* Title */}
                  <div className="flex items-center gap-3 mb-3 flex-wrap">
                    <h4 className="font-bold text-xl text-gray-900">{poi.name}</h4>
                    {poi.is_coffee_break && (
                      <span className="px-3 py-1 bg-amber-100 text-amber-800 text-xs font-semibold rounded-full">
                        ☕ Кофе-брейк
                      </span>
                    )}
                  </div>
                  
                  {/* Description */}
                  <p className="text-gray-700 mb-4 leading-relaxed">{poi.why}</p>
                  
                  {/* Tip */}
                  {poi.tip && (
                    <div className="mb-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border-l-4 border-blue-500">
                      <p className="text-sm text-blue-900">
                        <span className="font-bold">💡 Совет:</span> {poi.tip}
                      </p>
                    </div>
                  )}
                  
                  {/* Time info */}
                  <div className="flex flex-wrap items-center gap-4 text-sm">
                    <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-lg border border-gray-200">
                      <span className="text-lg">🕐</span>
                      <span className="font-semibold text-gray-700">
                        {formatTime(poi.arrival_time)} - {formatTime(poi.leave_time)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-lg border border-gray-200">
                      <span className="text-lg">⏱️</span>
                      <span className="font-semibold text-gray-700">{poi.est_visit_minutes} минут</span>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Connection line to next point */}
              {index < route.route.length - 1 && (
                <div className="mt-6 pt-6 border-t-2 border-dashed border-gray-300 flex items-center gap-3 text-sm text-gray-600">
                  <span className="text-xl">👣</span>
                  <span className="font-medium">Переход к следующей точке</span>
                  <div className="flex-1 h-px bg-gradient-to-r from-gray-300 to-transparent"></div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Notes */}
      {route.notes && route.notes.length > 0 && (
        <div className="bg-gradient-to-br from-yellow-50 to-amber-50 border-2 border-yellow-300 rounded-2xl p-6 shadow-xl print:break-inside-avoid animate-fadeIn">
          <h4 className="font-bold text-xl mb-4 text-gray-900 flex items-center gap-3">
            <span className="text-3xl">📝</span>
            Полезные заметки
          </h4>
          <ul className="space-y-3">
            {route.notes.map((note, i) => (
              <li key={i} className="flex items-start gap-4 animate-slideInLeft" style={{ animationDelay: `${i * 100}ms` }}>
                <span className="text-yellow-600 text-xl mt-1 flex-shrink-0">•</span>
                <span className="text-gray-800 leading-relaxed">{note}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Share Modal */}
      {showShareModal && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 animate-fadeIn"
          onClick={() => setShowShareModal(false)}
        >
          <div 
            className="bg-white rounded-2xl p-8 max-w-md w-full animate-scaleIn"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-2xl font-bold mb-4">Поделиться маршрутом</h3>
            <p className="text-gray-600 mb-4">Скопируйте ссылку:</p>
            <input
              type="text"
              value={window.location.href}
              readOnly
              className="w-full px-4 py-3 border-2 border-gray-300 rounded-xl mb-4 font-mono text-sm"
              onClick={(e) => (e.target as HTMLInputElement).select()}
            />
            <button
              onClick={() => {
                navigator.clipboard.writeText(window.location.href)
                setShowShareModal(false)
              }}
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3 rounded-xl font-semibold hover:shadow-lg transition-all"
            >
              Копировать ссылку
            </button>
          </div>
        </div>
      )}
    </div>
  )
}