import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { MapPin, Navigation, Search, AlertCircle } from 'lucide-react'
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet'
import type { RouteRequest } from '../../types'
import 'leaflet/dist/leaflet.css'
import '../../lib/leaflet'

interface Props {
  formData: Partial<RouteRequest>
  updateFormData: (updates: Partial<RouteRequest>) => void
}

const DEFAULT_CENTER = { lat: 56.3287, lon: 44.002 }

const LOCATION_MODES = [
  { id: 'address', icon: Search, label: 'Адрес', desc: 'Введите адрес' },
  { id: 'coords', icon: MapPin, label: 'Координаты', desc: 'Точные координаты' },
  { id: 'map', icon: Navigation, label: 'На карте', desc: 'Выберите на карте' },
] as const

type LocationMode = typeof LOCATION_MODES[number]['id']

function LocationPicker({ onLocationSelect }: { onLocationSelect: (lat: number, lon: number) => void }) {
  const [position, setPosition] = useState<[number, number]>([DEFAULT_CENTER.lat, DEFAULT_CENTER.lon])

  useMapEvents({
    click(e) {
      const { lat, lng } = e.latlng
      setPosition([lat, lng])
      onLocationSelect(lat, lng)
    },
  })

  useEffect(() => {
    const removeFlag = () => {
      const flags = document.querySelectorAll('.leaflet-attribution-flag, svg.leaflet-attribution-flag')
      flags.forEach(flag => flag.remove())
      
      const attributionSvgs = document.querySelectorAll('.leaflet-control-attribution svg')
      attributionSvgs.forEach(svg => svg.remove())
    }

    removeFlag()
    const interval = setInterval(removeFlag, 500)

    return () => clearInterval(interval)
  }, [])

  return <Marker position={position} />
}

export default function StepLocation({ formData, updateFormData }: Props) {
  const [locationMode, setLocationMode] = useState<LocationMode>('address')
  const [geoStatus, setGeoStatus] = useState<'idle' | 'locating' | 'success' | 'error'>('idle')
  const [geoError, setGeoError] = useState<string>('')

  const handleModeChange = (mode: LocationMode) => {
    setLocationMode(mode)
    setGeoStatus('idle')
    setGeoError('')
    
    if (mode === 'address') {
      updateFormData({ start_lat: undefined, start_lon: undefined })
    } else {
      updateFormData({
        start_address: undefined,
        start_lat: formData.start_lat || DEFAULT_CENTER.lat,
        start_lon: formData.start_lon || DEFAULT_CENTER.lon,
      })
    }
  }

  const locateUser = () => {
    if (!navigator.geolocation) {
      setGeoStatus('error')
      setGeoError('Ваш браузер не поддерживает геолокацию')
      return
    }

    setGeoStatus('locating')
    setGeoError('')

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords
        updateFormData({ 
          start_lat: latitude, 
          start_lon: longitude, 
          start_address: undefined 
        })
        setLocationMode('map')
        setGeoStatus('success')
        setGeoError('')
      },
      (error) => {
        setGeoStatus('error')
        let errorMessage = 'Не удалось определить местоположение'
        
        switch (error.code) {
          case error.PERMISSION_DENIED:
            errorMessage = 'Доступ к геолокации запрещён. Разрешите доступ в настройках браузера'
            break
          case error.POSITION_UNAVAILABLE:
            errorMessage = 'Информация о местоположении недоступна'
            break
          case error.TIMEOUT:
            errorMessage = 'Истекло время ожидания. Попробуйте снова'
            break
          default:
            errorMessage = `Ошибка геолокации: ${error.message}`
        }
        
        setGeoError(errorMessage)
      },
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 0
      }
    )
  }

  return (
    <div className="space-y-8">
      <div className="text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 200 }}
          className="inline-block mb-4"
        >
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-4xl shadow-xl">
            📍
          </div>
        </motion.div>
        <h2 className="text-4xl font-black text-slate-900 dark:text-white mb-3">
          Откуда начнём?
        </h2>
        <p className="text-lg text-slate-600 dark:text-slate-400">
          Укажите точку старта вашей прогулки
        </p>
        <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
          <button
            type="button"
            onClick={locateUser}
            disabled={geoStatus === 'locating'}
            className="hide-geolocation-btn inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-sky-500 text-white font-semibold shadow-lg hover:shadow-emerald-300/50 transition-transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation"
          >
            <Navigation className={`w-4 h-4 ${geoStatus === 'locating' ? 'animate-pulse' : ''}`} />
            {geoStatus === 'locating' ? 'Определяем...' : 'Определить автоматически'}
          </button>
        </div>
        
        {geoStatus === 'success' && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="hide-geolocation-btn mt-3 flex items-center justify-center gap-2 text-sm text-emerald-600 dark:text-emerald-400"
          >
            <span className="text-lg">✓</span>
            <span className="font-medium">Местоположение определено</span>
          </motion.div>
        )}
        
        {geoStatus === 'error' && geoError && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="hide-geolocation-btn mt-3 mx-auto max-w-md"
          >
            <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-left">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-red-800 font-medium">Ошибка геолокации</p>
                <p className="text-xs text-red-600 mt-1">{geoError}</p>
              </div>
            </div>
          </motion.div>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {LOCATION_MODES.map((mode, index) => {
          const Icon = mode.icon
          const isSelected = locationMode === mode.id
          return (
            <motion.button
              key={mode.id}
              type="button"
              onClick={() => handleModeChange(mode.id)}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              className={`p-5 rounded-xl font-semibold transition-all touch-manipulation ${
                isSelected
                  ? 'bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/30'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 border-2 border-slate-200 dark:border-slate-700'
              }`}
            >
              <Icon className="w-8 h-8 mx-auto mb-3" />
              <div className="text-base font-bold mb-1">{mode.label}</div>
              <div className="text-xs opacity-70">{mode.desc}</div>
            </motion.button>
          )
        })}
      </div>

      <motion.div
        key={locationMode}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3 }}
      >
        {locationMode === 'address' && (
          <div>
            <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
              Введите адрес
            </label>
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                value={formData.start_address || ''}
                onChange={(e) => updateFormData({ start_address: e.target.value })}
                placeholder="Например: площадь Минина и Пожарского"
                className="w-full pl-12 pr-4 py-4 bg-white dark:bg-slate-900 border-2 border-slate-200 dark:border-slate-700 rounded-xl focus:ring-4 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all text-lg"
              />
            </div>
            {formData.start_address && formData.start_address.trim() && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-3 flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 px-4 py-2 rounded-lg"
              >
                <span className="text-lg">✓</span>
                <span className="font-medium">Адрес будет геокодирован автоматически</span>
              </motion.div>
            )}
          </div>
        )}

        {locationMode === 'coords' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">
                Широта (Latitude)
              </label>
              <input
                type="number"
                step="0.0001"
                value={formData.start_lat ?? ''}
                onChange={(e) => updateFormData({ start_lat: e.target.value ? parseFloat(e.target.value) : undefined })}
                placeholder="56.3287"
                className="w-full px-4 py-3 bg-white dark:bg-slate-900 border-2 border-slate-200 dark:border-slate-700 rounded-xl focus:ring-4 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
              />
            </div>
            <div>
              <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">
                Долгота (Longitude)
              </label>
              <input
                type="number"
                step="0.0001"
                value={formData.start_lon ?? ''}
                onChange={(e) => updateFormData({ start_lon: e.target.value ? parseFloat(e.target.value) : undefined })}
                placeholder="44.002"
                className="w-full px-4 py-3 bg-white dark:bg-slate-900 border-2 border-slate-200 dark:border-slate-700 rounded-xl focus:ring-4 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
              />
            </div>
            {formData.start_lat && formData.start_lon && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 px-4 py-3 rounded-lg"
              >
                <span className="text-lg">✓</span>
                <span className="font-medium">
                  Координаты установлены: {formData.start_lat.toFixed(4)}, {formData.start_lon.toFixed(4)}
                </span>
              </motion.div>
            )}
          </div>
        )}

        {locationMode === 'map' && (
          <div className="space-y-4">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Кликните на карту, чтобы выбрать точку старта
            </p>
            <div className="h-96 rounded-2xl overflow-hidden border-2 border-slate-200 dark:border-slate-700 shadow-xl">
              <MapContainer
                center={[formData.start_lat || DEFAULT_CENTER.lat, formData.start_lon || DEFAULT_CENTER.lon]}
                zoom={13}
                style={{ height: '100%', width: '100%' }}
              >
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                />
                <LocationPicker
                  onLocationSelect={(lat, lon) => {
                    updateFormData({ start_lat: lat, start_lon: lon })
                  }}
                />
              </MapContainer>
            </div>
            {formData.start_lat && formData.start_lon && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex items-center justify-between p-4 bg-emerald-50 dark:bg-emerald-900/20 border-2 border-emerald-200 dark:border-emerald-800 rounded-xl"
              >
                <div className="flex items-center gap-3">
                  <MapPin className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                  <div>
                    <div className="text-sm font-bold text-emerald-900 dark:text-emerald-100">
                      Точка выбрана
                    </div>
                    <div className="text-xs text-emerald-700 dark:text-emerald-300">
                      {formData.start_lat.toFixed(4)}, {formData.start_lon.toFixed(4)}
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </div>
        )}
      </motion.div>

      <div className="bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 border-2 border-emerald-200 dark:border-emerald-800 rounded-xl p-5">
        <p className="text-sm text-emerald-900 dark:text-emerald-100">
          <span className="font-bold">💡 Совет:</span> Если выберете центр города, AI построит компактный маршрут с известными местами. Если укажете окраину — добавит уникальные локации поблизости
        </p>
      </div>
    </div>
  )
}