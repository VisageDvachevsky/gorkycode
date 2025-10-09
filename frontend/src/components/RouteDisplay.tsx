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

interface Props {
  route: RouteResponse
}

export default function RouteDisplay({ route }: Props) {
  const positions = route.route.map((poi) => [poi.lat, poi.lon] as [number, number])
  const center = positions[0] || [56.3287, 44.002]

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-2xl font-semibold mb-4">Ваш маршрут</h2>
        
        {route.summary && (
          <p className="text-gray-700 mb-4">{route.summary}</p>
        )}

        <div className="flex items-center gap-4 text-sm text-gray-600 mb-4">
          <span>⏱️ {Math.floor(route.total_est_minutes / 60)}ч {route.total_est_minutes % 60}м</span>
          <span>📍 {route.route.length} точек</span>
          <span>🚶 {route.total_distance_km} км</span>
        </div>

        {route.atmospheric_description && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <p className="text-sm text-blue-900 italic">{route.atmospheric_description}</p>
          </div>
        )}

        <div className="h-96 rounded-lg overflow-hidden border border-gray-300 mb-6">
          <MapContainer center={center} zoom={13} style={{ height: '100%', width: '100%' }}>
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            />
            {route.route.map((poi) => (
              <Marker key={poi.poi_id} position={[poi.lat, poi.lon]}>
                <Popup>
                  <div className="text-sm">
                    <strong>{poi.order}. {poi.name}</strong>
                    <p className="mt-1">{poi.why}</p>
                  </div>
                </Popup>
              </Marker>
            ))}
            <Polyline positions={positions} color="blue" weight={3} />
          </MapContainer>
        </div>

        <div className="space-y-4">
          {route.route.map((poi) => (
            <div
              key={poi.poi_id}
              className={`border rounded-lg p-4 ${
                poi.is_coffee_break ? 'bg-amber-50 border-amber-300' : 'bg-gray-50 border-gray-300'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="bg-blue-600 text-white w-6 h-6 rounded-full flex items-center justify-center text-sm font-semibold">
                      {poi.order}
                    </span>
                    <h3 className="font-semibold text-lg">{poi.name}</h3>
                    {poi.is_coffee_break && <span className="text-amber-600">☕</span>}
                  </div>
                  
                  <p className="text-gray-700 mb-2">{poi.why}</p>
                  
                  {poi.tip && (
                    <p className="text-sm text-blue-600 mb-2">💡 {poi.tip}</p>
                  )}
                  
                  <div className="flex items-center gap-4 text-sm text-gray-600">
                    <span>🕐 {formatTime(poi.arrival_time)} - {formatTime(poi.leave_time)}</span>
                    <span>⏱️ {poi.est_visit_minutes} мин</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {route.notes.length > 0 && (
          <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h4 className="font-semibold mb-2">📝 Заметки</h4>
            <ul className="list-disc list-inside space-y-1">
              {route.notes.map((note, i) => (
                <li key={i} className="text-sm text-gray-700">{note}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}