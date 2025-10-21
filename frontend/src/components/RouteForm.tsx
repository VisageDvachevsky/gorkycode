import { useState, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet'
import { api } from '../api/client'
import type { RouteRequest, RouteResponse, Category, CoffeePreferences } from '../types'
import {
  DEFAULT_ROUTE_HOURS,
  MAX_ROUTE_HOURS,
  MIN_ROUTE_HOURS,
  sanitizeRouteHours,
} from '../constants/route'
import 'leaflet/dist/leaflet.css'
import '../lib/leaflet'

interface Props {
  onRouteGenerated: (route: RouteResponse) => void
}

const DEFAULT_CENTER = { lat: 56.3287, lon: 44.002 }

function LocationPicker({ onLocationSelect }: { onLocationSelect: (lat: number, lon: number) => void }) {
  const [position, setPosition] = useState<[number, number]>([DEFAULT_CENTER.lat, DEFAULT_CENTER.lon])

  useMapEvents({
    click(e) {
      const { lat, lng } = e.latlng
      setPosition([lat, lng])
      onLocationSelect(lat, lng)
    },
  })

  return <Marker position={position} />
}

export default function RouteForm({ onRouteGenerated }: Props) {
  const [locationType, setLocationType] = useState<'address' | 'coords' | 'map'>('address')
  const [showMap, setShowMap] = useState(false)
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [validationError, setValidationError] = useState<string | null>(null)
  const [formProgress, setFormProgress] = useState(0)
  const [showCoffeeAdvanced, setShowCoffeeAdvanced] = useState(false)
  
  const [formData, setFormData] = useState<RouteRequest>({
    interests: '',
    hours: DEFAULT_ROUTE_HOURS,
    social_mode: 'solo',
    intensity: 'medium',
    allow_transit: true,
    start_address: '',
  })

  const [coffeePrefs, setCoffeePrefs] = useState<CoffeePreferences>({
    enabled: false,
    interval_minutes: 90,
    outdoor_seating: false,
    wifi: false,
    search_radius_km: 0.5,
  })

  const { data: categories = [], isLoading: categoriesLoading } = useQuery({
    queryKey: ['categories'],
    queryFn: api.getCategories,
  })

  const mutation = useMutation({
    mutationFn: api.planRoute,
    onSuccess: (data) => {
      onRouteGenerated(data)
    },
  })

  useEffect(() => {
    let progress = 0
    
    if (formData.interests.trim() || selectedCategories.length > 0) progress += 25
    if (formData.hours >= MIN_ROUTE_HOURS && formData.hours <= MAX_ROUTE_HOURS) progress += 25
    if (locationType === 'address' ? formData.start_address : (formData.start_lat !== undefined && formData.start_lon !== undefined)) progress += 25
    progress += 25
    
    setFormProgress(progress)
  }, [formData, selectedCategories, locationType])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    const hasInterests = formData.interests.trim().length > 0
    const hasCategories = selectedCategories.length > 0
    
    if (!hasInterests && !hasCategories) {
      setValidationError('Укажите ваши интересы или выберите хотя бы одну категорию')
      return
    }
    
    if (locationType === 'address' && !formData.start_address?.trim()) {
      setValidationError('Укажите адрес или выберите другой способ')
      return
    }
    
    if (locationType === 'coords' && (formData.start_lat === undefined || formData.start_lon === undefined)) {
      setValidationError('Укажите координаты')
      return
    }
    
    if (locationType === 'map' && (formData.start_lat === undefined || formData.start_lon === undefined)) {
      setValidationError('Выберите точку на карте')
      return
    }
    
    setValidationError(null)
    
    const requestData: RouteRequest = {
      ...formData,
      hours: sanitizeRouteHours(formData.hours),
      categories: selectedCategories.length > 0 ? selectedCategories : undefined,
      coffee_preferences: coffeePrefs.enabled ? coffeePrefs : undefined,
    }
    
    if (locationType === 'address') {
      delete requestData.start_lat
      delete requestData.start_lon
    } else {
      delete requestData.start_address
    }
    
    mutation.mutate(requestData)
  }

  const toggleCategory = (category: string) => {
    setSelectedCategories(prev =>
      prev.includes(category)
        ? prev.filter(c => c !== category)
        : [...prev, category]
    )
  }

  return (
    <div className="bg-white rounded-2xl shadow-2xl p-8 space-y-6 animate-fadeIn">
      <div className="border-b pb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
              Создать маршрут
            </h2>
            <p className="text-gray-500 mt-1">Персональная прогулка по вашим интересам</p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-blue-600">{formProgress}%</div>
            <div className="text-xs text-gray-500">готовность</div>
          </div>
        </div>
        
        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-blue-600 to-indigo-600 transition-all duration-500 ease-out"
            style={{ width: `${formProgress}%` }}
          />
        </div>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="animate-slideInLeft">
          <label className="block text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <span className="text-xl">✍️</span>
            Что вас интересует?
          </label>
          <textarea
            value={formData.interests}
            onChange={(e) => setFormData({ ...formData, interests: e.target.value })}
            placeholder="Например: уличное искусство, исторические здания, кофейни с видом..."
            className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all resize-none hover:border-gray-300"
            rows={3}
          />
          
          {formData.interests.trim() && (
            <div className="text-sm text-green-600 bg-green-50 px-3 py-2 rounded-lg mt-2 flex items-center gap-2 animate-slideInLeft">
              <span>✓</span>
              <span>Интересы указаны</span>
            </div>
          )}
        </div>

        <div className="animate-slideInLeft" style={{ animationDelay: '100ms' }}>
          <label className="block text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <span className="text-xl">🏷️</span>
            Категории мест
          </label>
          
          {categoriesLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {categories.map((cat, index) => (
                <button
                  key={cat.value}
                  type="button"
                  onClick={() => toggleCategory(cat.value)}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 transform hover:scale-105 animate-scaleIn ${
                    selectedCategories.includes(cat.value)
                      ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  {cat.label} ({cat.count})
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-slideInLeft" style={{ animationDelay: '200ms' }}>
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
              <span className="text-xl">⏱️</span>
              Длительность прогулки
            </label>
            <input
              type="number"
              value={formData.hours}
              onChange={(e) =>
                setFormData({ ...formData, hours: sanitizeRouteHours(parseFloat(e.target.value)) })
              }
              min={MIN_ROUTE_HOURS}
              max={MAX_ROUTE_HOURS}
              step="0.5"
              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all hover:border-gray-300"
              required
            />
             <span className="text-xs text-gray-500 mt-1 block">от 0.5 до 8 часов</span>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
              <span className="text-xl">👥</span>
              С кем идёте?
            </label>
            <select
              value={formData.social_mode}
              onChange={(e) => setFormData({ ...formData, social_mode: e.target.value as any })}
              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all hover:border-gray-300"
            >
              <option value="solo">🚶 Один/одна</option>
              <option value="friends">👥 С друзьями</option>
              <option value="family">👨‍👩‍👧 С семьёй</option>
            </select>
          </div>
        </div>

        <div className="animate-slideInLeft" style={{ animationDelay: '300ms' }}>
          <label className="block text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <span className="text-xl">⚡</span>
            Интенсивность прогулки
          </label>
          <div className="grid grid-cols-3 gap-3">
            {[
              { value: 'relaxed', emoji: '🌸', label: 'Спокойно' },
              { value: 'medium', emoji: '⚡', label: 'Средне' },
              { value: 'intense', emoji: '🔥', label: 'Интенсивно' }
            ].map((level) => (
              <button
                key={level.value}
                type="button"
                onClick={() => setFormData({ ...formData, intensity: level.value as any })}
                className={`px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 transform hover:scale-105 ${
                  formData.intensity === level.value
                    ? 'bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-lg'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <div className="text-2xl mb-1">{level.emoji}</div>
                {level.label}
              </button>
            ))}
          </div>
        </div>

        <div className="animate-slideInLeft" style={{ animationDelay: '400ms' }}>
          <label className="block text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <span className="text-xl">📍</span>
            Точка старта
          </label>
          <div className="flex flex-wrap gap-2 mb-3">
            {[
              { value: 'address', icon: '📍', label: 'Адрес' },
              { value: 'coords', icon: '🗺️', label: 'Координаты' },
              { value: 'map', icon: '🎯', label: 'На карте' }
            ].map((type) => (
              <button
                key={type.value}
                type="button"
                onClick={() => {
                  setLocationType(type.value as any)
                  if (type.value === 'map') {
                    setShowMap(true)
                    setFormData({ 
                      ...formData, 
                      start_lat: DEFAULT_CENTER.lat,
                      start_lon: DEFAULT_CENTER.lon,
                      start_address: undefined
                    })
                  } else if (type.value === 'coords') {
                    setFormData({
                      ...formData,
                      start_lat: DEFAULT_CENTER.lat,
                      start_lon: DEFAULT_CENTER.lon,
                      start_address: undefined
                    })
                  } else {
                    setFormData({
                      ...formData,
                      start_lat: undefined,
                      start_lon: undefined,
                      start_address: ''
                    })
                  }
                }}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 transform hover:scale-105 ${
                  locationType === type.value
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <span className="mr-2">{type.icon}</span>
                {type.label}
              </button>
            ))}
          </div>

          {locationType === 'address' && (
            <input
              type="text"
              value={formData.start_address || ''}
              onChange={(e) => setFormData({ ...formData, start_address: e.target.value })}
              placeholder="Например: площадь Минина и Пожарского"
              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all hover:border-gray-300 animate-fadeIn"
            />
          )}

          {locationType === 'coords' && (
            <div className="grid grid-cols-2 gap-4 animate-fadeIn">
              <input
                type="number"
                value={formData.start_lat ?? ''}
                onChange={(e) => setFormData({ ...formData, start_lat: e.target.value ? parseFloat(e.target.value) : undefined })}
                step="0.0001"
                placeholder="Широта"
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all hover:border-gray-300"
              />
              <input
                type="number"
                value={formData.start_lon ?? ''}
                onChange={(e) => setFormData({ ...formData, start_lon: e.target.value ? parseFloat(e.target.value) : undefined })}
                step="0.0001"
                placeholder="Долгота"
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all hover:border-gray-300"
              />
            </div>
          )}

          {locationType === 'map' && showMap && (
            <div className="h-64 rounded-xl overflow-hidden border-2 border-gray-200 animate-fadeIn">
              <MapContainer
                center={[formData.start_lat ?? DEFAULT_CENTER.lat, formData.start_lon ?? DEFAULT_CENTER.lon]}
                zoom={13}
                style={{ height: '100%', width: '100%' }}
              >
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                <LocationPicker
                  onLocationSelect={(lat, lon) => {
                    setFormData({ ...formData, start_lat: lat, start_lon: lon })
                  }}
                />
              </MapContainer>
            </div>
          )}
        </div>

        <div className="bg-gradient-to-br from-amber-50 to-orange-50 border-2 border-amber-200 rounded-2xl p-6 animate-slideInLeft" style={{ animationDelay: '500ms' }}>
          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={coffeePrefs.enabled}
              onChange={(e) => setCoffeePrefs({ ...coffeePrefs, enabled: e.target.checked })}
              className="w-6 h-6 rounded-lg text-amber-600 focus:ring-amber-500 transition-all"
            />
            <span className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <span className="text-2xl">☕</span>
              Умные кофе-брейки (через 2GIS Places API)
            </span>
          </label>
          
          {coffeePrefs.enabled && (
            <div className="mt-4 space-y-4 animate-fadeIn">
              <div>
                <label className="text-xs font-medium text-gray-700 mb-2 block">Интервал</label>
                <input
                  type="range"
                  value={coffeePrefs.interval_minutes}
                  onChange={(e) => setCoffeePrefs({ ...coffeePrefs, interval_minutes: parseInt(e.target.value) })}
                  min="30"
                  max="180"
                  step="15"
                  className="w-full h-2 bg-amber-200 rounded-lg appearance-none cursor-pointer accent-amber-600"
                />
                <div className="flex justify-between text-xs text-gray-700 mt-2 font-medium">
                  <span>30 мин</span>
                  <span className="text-lg font-bold text-amber-700">{coffeePrefs.interval_minutes} минут</span>
                  <span>180 мин</span>
                </div>
              </div>
              
              <button
                type="button"
                onClick={() => setShowCoffeeAdvanced(!showCoffeeAdvanced)}
                className="text-sm text-amber-700 font-medium hover:text-amber-800 flex items-center gap-2"
              >
                <span>{showCoffeeAdvanced ? '▼' : '▶'}</span>
                Дополнительные настройки
              </button>
              
              {showCoffeeAdvanced && (
                <div className="space-y-3 animate-fadeIn">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-medium text-gray-700 mb-1 block">Кухня</label>
                      <select
                        value={coffeePrefs.cuisine || ''}
                        onChange={(e) => setCoffeePrefs({ ...coffeePrefs, cuisine: e.target.value || undefined })}
                        className="w-full px-3 py-2 border border-amber-300 rounded-lg text-sm"
                      >
                        <option value="">Любая</option>
                        <option value="italian">Итальянская</option>
                        <option value="french">Французская</option>
                        <option value="japanese">Японская</option>
                        <option value="asian">Азиатская</option>
                      </select>
                    </div>
                    
                    <div>
                      <label className="text-xs font-medium text-gray-700 mb-1 block">Диета</label>
                      <select
                        value={coffeePrefs.dietary || ''}
                        onChange={(e) => setCoffeePrefs({ ...coffeePrefs, dietary: e.target.value || undefined })}
                        className="w-full px-3 py-2 border border-amber-300 rounded-lg text-sm"
                      >
                        <option value="">Без ограничений</option>
                        <option value="vegetarian">Вегетарианская</option>
                        <option value="vegan">Веганская</option>
                        <option value="halal">Халяль</option>
                        <option value="kosher">Кошерная</option>
                      </select>
                    </div>
                  </div>
                  
                  <div className="flex gap-4">
                    <label className="flex items-center space-x-2 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={coffeePrefs.outdoor_seating}
                        onChange={(e) => setCoffeePrefs({ ...coffeePrefs, outdoor_seating: e.target.checked })}
                        className="rounded text-amber-600"
                      />
                      <span>🪑 Терраса</span>
                    </label>
                    
                    <label className="flex items-center space-x-2 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={coffeePrefs.wifi}
                        onChange={(e) => setCoffeePrefs({ ...coffeePrefs, wifi: e.target.checked })}
                        className="rounded text-amber-600"
                      />
                      <span>📶 Wi-Fi</span>
                    </label>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200 rounded-2xl p-6 animate-slideInLeft" style={{ animationDelay: '550ms' }}>
          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.allow_transit}
              onChange={(e) => setFormData({ ...formData, allow_transit: e.target.checked })}
              className="w-6 h-6 rounded-lg text-green-600 focus:ring-green-500 transition-all"
            />
            <div className="flex-1">
              <span className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                <span className="text-2xl">🚍</span>
                Использовать общественный транспорт
              </span>
              <p className="text-xs text-gray-600 mt-1">Для больших расстояний (&gt;2 км) предложим автобус/трамвай</p>
            </div>
          </label>
        </div>

        {validationError && (
          <div className="bg-red-50 border-2 border-red-200 text-red-700 px-5 py-4 rounded-2xl animate-scaleIn">
            <p className="font-bold flex items-center gap-2">
              <span className="text-2xl">⚠️</span>
              {validationError}
            </p>
          </div>
        )}

        <button
          type="submit"
          disabled={mutation.isPending || formProgress < 100}
          className="w-full bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white py-4 px-6 rounded-2xl font-bold text-lg hover:shadow-2xl transition-all duration-300 transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none animate-slideInUp"
          style={{ animationDelay: '600ms' }}
        >
          {mutation.isPending ? (
            <span className="flex items-center justify-center gap-3">
              <div className="w-6 h-6 border-3 border-white border-t-transparent rounded-full animate-spin" />
              Создаём ваш маршрут...
            </span>
          ) : formProgress < 100 ? (
            `Заполните форму (${formProgress}%)`
          ) : (
            <span className="flex items-center justify-center gap-2">
              <span className="text-2xl">🗺️</span>
              Построить маршрут
            </span>
          )}
        </button>

        {mutation.isError && (
          <div className="bg-red-50 border-2 border-red-200 text-red-700 px-5 py-4 rounded-2xl animate-scaleIn">
            <p className="font-bold">Ошибка при создании маршрута</p>
            <p className="text-sm mt-1">
              {(mutation.error as any)?.response?.data?.detail || 'Проверьте введённые данные и попробуйте ещё раз.'}
            </p>
          </div>
        )}
      </form>
    </div>
  )
}
