import { useState, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import { api } from '../api/client'
import type { RouteRequest, RouteResponse, Category } from '../types'
import 'leaflet/dist/leaflet.css'

delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
})

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
  
  const [formData, setFormData] = useState<RouteRequest>({
    interests: '',
    hours: 3,
    social_mode: 'solo',
    intensity: 'medium',
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

  // Calculate form completion progress
  useEffect(() => {
    let progress = 0
    const steps = 4 // Total required steps
    
    if (formData.interests.trim() || selectedCategories.length > 0) progress += 25
    if (formData.hours) progress += 25
    if (locationType === 'address' ? formData.start_address : (formData.start_lat && formData.start_lon)) progress += 25
    progress += 25 // Social mode and intensity always have defaults
    
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
    
    if (locationType === 'coords' && (!formData.start_lat || !formData.start_lon)) {
      setValidationError('Укажите координаты')
      return
    }
    
    if (locationType === 'map' && (!formData.start_lat || !formData.start_lon)) {
      setValidationError('Выберите точку на карте')
      return
    }
    
    setValidationError(null)
    
    const requestData: RouteRequest = {
      ...formData,
      categories: selectedCategories.length > 0 ? selectedCategories : undefined,
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
      {/* Header with progress */}
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
        
        {/* Progress bar */}
        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-blue-600 to-indigo-600 transition-all duration-500 ease-out"
            style={{ width: `${formProgress}%` }}
          />
        </div>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Interests */}
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
          
          <p className="text-xs text-gray-500 mt-2 flex items-center gap-1">
            <span>💡</span>
            <span>Можно оставить пустым, если выбрали категории ниже</span>
          </p>
        </div>

        {/* Categories */}
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
          
          {selectedCategories.length > 0 && (
            <>
              <div className="text-sm text-green-600 bg-green-50 px-3 py-2 rounded-lg mt-3 flex items-center gap-2 animate-slideInLeft">
                <span>✓</span>
                <span>Выбрано категорий: {selectedCategories.length}</span>
              </div>
              <button
                type="button"
                onClick={() => setSelectedCategories([])}
                className="mt-2 text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1 transition-colors"
              >
                <span>↺</span>
                <span>Сбросить выбор</span>
              </button>
            </>
          )}
        </div>

        {/* Duration and Social mode */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-slideInLeft" style={{ animationDelay: '200ms' }}>
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
              <span className="text-xl">⏱️</span>
              Длительность прогулки
            </label>
            <input
              type="number"
              value={formData.hours}
              onChange={(e) => setFormData({ ...formData, hours: parseFloat(e.target.value) })}
              min="0.5"
              max="12"
              step="0.5"
              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all hover:border-gray-300"
              required
            />
            <span className="text-xs text-gray-500 mt-1 block">от 0.5 до 12 часов</span>
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

        {/* Intensity */}
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

        {/* Location */}
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
                  if (type.value === 'map') setShowMap(true)
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
                value={formData.start_lat || DEFAULT_CENTER.lat}
                onChange={(e) => setFormData({ ...formData, start_lat: parseFloat(e.target.value) })}
                step="0.0001"
                placeholder="Широта"
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all hover:border-gray-300"
              />
              <input
                type="number"
                value={formData.start_lon || DEFAULT_CENTER.lon}
                onChange={(e) => setFormData({ ...formData, start_lon: parseFloat(e.target.value) })}
                step="0.0001"
                placeholder="Долгота"
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all hover:border-gray-300"
              />
            </div>
          )}

          {locationType === 'map' && showMap && (
            <div className="h-64 rounded-xl overflow-hidden border-2 border-gray-200 animate-fadeIn">
              <MapContainer
                center={[DEFAULT_CENTER.lat, DEFAULT_CENTER.lon]}
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

        {/* Coffee breaks */}
        <div className="bg-gradient-to-br from-amber-50 to-orange-50 border-2 border-amber-200 rounded-2xl p-6 animate-slideInLeft" style={{ animationDelay: '500ms' }}>
          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.coffee_preference !== undefined}
              onChange={(e) => {
                if (e.target.checked) {
                  setFormData({ ...formData, coffee_preference: 90 })
                } else {
                  const { coffee_preference, ...rest } = formData
                  setFormData(rest)
                }
              }}
              className="w-6 h-6 rounded-lg text-amber-600 focus:ring-amber-500 transition-all"
            />
            <span className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <span className="text-2xl">☕</span>
              Добавить кофе-брейки
            </span>
          </label>
          
          {formData.coffee_preference !== undefined && (
            <div className="mt-4 animate-fadeIn">
              <input
                type="range"
                value={formData.coffee_preference}
                onChange={(e) => setFormData({ ...formData, coffee_preference: parseInt(e.target.value) })}
                min="30"
                max="180"
                step="15"
                className="w-full h-2 bg-amber-200 rounded-lg appearance-none cursor-pointer accent-amber-600"
              />
              <div className="flex justify-between text-xs text-gray-700 mt-2 font-medium">
                <span>30 мин</span>
                <span className="text-lg font-bold text-amber-700">{formData.coffee_preference} минут</span>
                <span>180 мин</span>
              </div>
            </div>
          )}
        </div>

        {/* Validation error */}
        {validationError && (
          <div className="bg-red-50 border-2 border-red-200 text-red-700 px-5 py-4 rounded-2xl animate-scaleIn">
            <p className="font-bold flex items-center gap-2">
              <span className="text-2xl">⚠️</span>
              {validationError}
            </p>
          </div>
        )}

        {/* Submit button */}
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

        {/* Error */}
        {mutation.isError && (
          <div className="bg-red-50 border-2 border-red-200 text-red-700 px-5 py-4 rounded-2xl animate-scaleIn">
            <p className="font-bold">Ошибка при создании маршрута</p>
            <p className="text-sm mt-1">Проверьте введённые данные и попробуйте ещё раз.</p>
          </div>
        )}
      </form>
    </div>
  )
}