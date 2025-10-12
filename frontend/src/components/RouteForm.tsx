import { useState, useEffect } from 'react'
import { useMutation, useQuery } from '@tantml:react-query'
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import { Clock, MapPin, Users, Zap, Calendar, Coffee, Bus } from 'lucide-react'
import { api } from '../api/client'
import type { RouteRequest, RouteResponse, Category, CoffeePreferences } from '../types'
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
  const [showCoffeeAdvanced, setShowCoffeeAdvanced] = useState(false)
  const [currentStep, setCurrentStep] = useState(1)
  
  const [formData, setFormData] = useState<RouteRequest>({
    interests: '',
    hours: 3,
    social_mode: 'solo',
    intensity: 'medium',
    allow_transit: true,
    start_address: '',
    start_time: '',
    client_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Moscow',
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
    if (formData.hours) progress += 20
    if (locationType === 'address' ? formData.start_address : (formData.start_lat !== undefined && formData.start_lon !== undefined)) progress += 25
    if (formData.start_time) progress += 10
    progress += 20
    
    setFormProgress(Math.min(progress, 100))
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

  const steps = [
    { num: 1, title: 'Интересы', icon: '✨' },
    { num: 2, title: 'Детали', icon: '⚙️' },
    { num: 3, title: 'Локация', icon: '📍' },
    { num: 4, title: 'Время', icon: '🕐' },
  ]

  return (
    <div className="relative">
      {/* Progress indicator */}
      <div className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-gray-200 px-8 py-4 mb-6 rounded-2xl shadow-lg animate-slideInUp">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 animate-pulse">
              Создать маршрут
            </h2>
            <p className="text-gray-500 mt-1 text-sm">Ваша персональная прогулка за 4 шага</p>
          </div>
          <div className="text-right">
            <div className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-green-500 to-emerald-600">
              {formProgress}%
            </div>
            <div className="text-xs text-gray-500 uppercase tracking-wider">Готовность</div>
          </div>
        </div>
        
        {/* Progress bar */}
        <div className="relative w-full h-3 bg-gray-200 rounded-full overflow-hidden">
          <div 
            className="absolute h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 transition-all duration-1000 ease-out rounded-full"
            style={{ width: `${formProgress}%` }}
          >
            <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
          </div>
        </div>

        {/* Step indicators */}
        <div className="flex justify-between mt-6">
          {steps.map((step, idx) => (
            <div
              key={step.num}
              className={`flex flex-col items-center transition-all duration-300 ${
                currentStep >= step.num
                  ? 'opacity-100 scale-100'
                  : 'opacity-40 scale-90'
              }`}
            >
              <div
                className={`w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold transition-all duration-300 ${
                  currentStep >= step.num
                    ? 'bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-lg scale-110'
                    : 'bg-gray-200 text-gray-500'
                }`}
              >
                {step.icon}
              </div>
              <span className="text-xs mt-2 font-semibold text-gray-600">{step.title}</span>
            </div>
          ))}
        </div>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Step 1: Interests */}
        <div className="bg-white rounded-3xl shadow-2xl p-8 hover:shadow-3xl transition-all duration-300 animate-fadeIn border-2 border-transparent hover:border-blue-300">
          <div className="flex items-center gap-3 mb-6">
            <div className="text-4xl">✨</div>
            <div>
              <h3 className="text-2xl font-bold text-gray-900">Шаг 1: Что вас интересует?</h3>
              <p className="text-sm text-gray-500">Расскажите о своих предпочтениях</p>
            </div>
          </div>
          
          <textarea
            value={formData.interests}
            onChange={(e) => {
              setFormData({ ...formData, interests: e.target.value })
              setCurrentStep(Math.max(currentStep, 1))
            }}
            placeholder="Например: советские мозаики, панорамные виды, исторические здания, уличное искусство..."
            className="w-full px-6 py-4 border-2 border-gray-200 rounded-2xl focus:ring-4 focus:ring-blue-500/30 focus:border-blue-500 transition-all resize-none hover:border-gray-300 text-lg"
            rows={4}
          />
          
          {formData.interests.trim() && (
            <div className="text-sm text-green-600 bg-gradient-to-r from-green-50 to-emerald-50 px-4 py-3 rounded-xl mt-3 flex items-center gap-3 animate-slideInLeft border-2 border-green-200">
              <span className="text-2xl">✓</span>
              <span className="font-semibold">Отлично! Интересы указаны</span>
            </div>
          )}

          {/* Categories */}
          <div className="mt-6">
            <label className="block text-sm font-bold text-gray-700 mb-4 flex items-center gap-2">
              <span className="text-2xl">🏷️</span>
              Или выберите категории
            </label>
            
            {categoriesLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="relative">
                  <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-500 rounded-full animate-pulse"></div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-wrap gap-3">
                {categories.map((cat, index) => (
                  <button
                    key={cat.value}
                    type="button"
                    onClick={() => {
                      toggleCategory(cat.value)
                      setCurrentStep(Math.max(currentStep, 1))
                    }}
                    className={`group relative px-6 py-3 rounded-2xl text-sm font-bold transition-all duration-300 transform hover:scale-110 animate-scaleIn ${
                      selectedCategories.includes(cat.value)
                        ? 'bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white shadow-2xl'
                        : 'bg-gradient-to-r from-gray-100 to-gray-200 text-gray-700 hover:from-gray-200 hover:to-gray-300 shadow-md'
                    }`}
                    style={{ animationDelay: `${index * 30}ms` }}
                  >
                    <span className="relative z-10">{cat.label} ({cat.count})</span>
                    {selectedCategories.includes(cat.value) && (
                      <div className="absolute inset-0 bg-white/20 rounded-2xl animate-pulse"></div>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Step 2: Details */}
        <div className="bg-white rounded-3xl shadow-2xl p-8 hover:shadow-3xl transition-all duration-300 animate-fadeIn" style={{ animationDelay: '100ms' }}>
          <div className="flex items-center gap-3 mb-6">
            <div className="text-4xl">⚙️</div>
            <div>
              <h3 className="text-2xl font-bold text-gray-900">Шаг 2: Детали прогулки</h3>
              <p className="text-sm text-gray-500">Настройте параметры маршрута</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Duration */}
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-sm font-bold text-gray-700">
                <Clock className="w-5 h-5 text-blue-600" />
                Длительность прогулки
              </label>
              <div className="relative">
                <input
                  type="number"
                  value={formData.hours}
                  onChange={(e) => {
                    setFormData({ ...formData, hours: parseFloat(e.target.value) || 3 })
                    setCurrentStep(Math.max(currentStep, 2))
                  }}
                  min="0.5"
                  max="12"
                  step="0.5"
                  className="w-full px-6 py-4 border-2 border-gray-200 rounded-2xl focus:ring-4 focus:ring-blue-500/30 focus:border-blue-500 transition-all hover:border-gray-300 text-lg font-semibold"
                  required
                />
                <div className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 font-semibold">
                  часов
                </div>
              </div>
              <span className="text-xs text-gray-500 block">от 0.5 до 12 часов</span>
            </div>

            {/* Social mode */}
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-sm font-bold text-gray-700">
                <Users className="w-5 h-5 text-indigo-600" />
                С кем идёте?
              </label>
              <select
                value={formData.social_mode}
                onChange={(e) => {
                  setFormData({ ...formData, social_mode: e.target.value as any })
                  setCurrentStep(Math.max(currentStep, 2))
                }}
                className="w-full px-6 py-4 border-2 border-gray-200 rounded-2xl focus:ring-4 focus:ring-indigo-500/30 focus:border-indigo-500 transition-all hover:border-gray-300 text-lg font-semibold appearance-none bg-white cursor-pointer"
              >
                <option value="solo">🚶 Один/одна</option>
                <option value="friends">👥 С друзьями</option>
                <option value="family">👨‍👩‍👧 С семьёй</option>
              </select>
            </div>
          </div>

          {/* Intensity */}
          <div className="mt-6 space-y-3">
            <label className="flex items-center gap-2 text-sm font-bold text-gray-700">
              <Zap className="w-5 h-5 text-purple-600" />
              Интенсивность прогулки
            </label>
            <div className="grid grid-cols-3 gap-4">
              {[
                { value: 'relaxed', emoji: '🌸', label: 'Спокойно', gradient: 'from-green-400 to-emerald-500' },
                { value: 'medium', emoji: '⚡', label: 'Средне', gradient: 'from-blue-400 to-indigo-500' },
                { value: 'intense', emoji: '🔥', label: 'Интенсивно', gradient: 'from-orange-400 to-red-500' }
              ].map((level) => (
                <button
                  key={level.value}
                  type="button"
                  onClick={() => {
                    setFormData({ ...formData, intensity: level.value as any })
                    setCurrentStep(Math.max(currentStep, 2))
                  }}
                  className={`relative px-6 py-6 rounded-2xl text-sm font-bold transition-all duration-300 transform hover:scale-105 group ${
                    formData.intensity === level.value
                      ? `bg-gradient-to-br ${level.gradient} text-white shadow-2xl scale-105`
                      : 'bg-gradient-to-br from-gray-100 to-gray-200 text-gray-700 hover:shadow-lg'
                  }`}
                >
                  <div className="text-4xl mb-2 group-hover:scale-110 transition-transform">{level.emoji}</div>
                  <div>{level.label}</div>
                  {formData.intensity === level.value && (
                    <div className="absolute inset-0 bg-white/20 rounded-2xl animate-pulse"></div>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Step 3: Location */}
        <div className="bg-white rounded-3xl shadow-2xl p-8 hover:shadow-3xl transition-all duration-300 animate-fadeIn" style={{ animationDelay: '200ms' }}>
          <div className="flex items-center gap-3 mb-6">
            <div className="text-4xl">📍</div>
            <div>
              <h3 className="text-2xl font-bold text-gray-900">Шаг 3: Точка старта</h3>
              <p className="text-sm text-gray-500">Откуда начнём прогулку?</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-3 mb-6">
            {[
              { value: 'address', icon: '📍', label: 'Адрес', color: 'from-red-500 to-pink-600' },
              { value: 'coords', icon: '🗺️', label: 'Координаты', color: 'from-blue-500 to-cyan-600' },
              { value: 'map', icon: '🎯', label: 'На карте', color: 'from-green-500 to-emerald-600' }
            ].map((type) => (
              <button
                key={type.value}
                type="button"
                onClick={() => {
                  setLocationType(type.value as any)
                  setCurrentStep(Math.max(currentStep, 3))
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
                className={`px-6 py-3 rounded-2xl text-sm font-bold transition-all duration-300 transform hover:scale-105 ${
                  locationType === type.value
                    ? `bg-gradient-to-r ${type.color} text-white shadow-2xl scale-105`
                    : 'bg-gradient-to-r from-gray-100 to-gray-200 text-gray-700 hover:shadow-lg'
                }`}
              >
                <span className="mr-2 text-xl">{type.icon}</span>
                {type.label}
              </button>
            ))}
          </div>

          {locationType === 'address' && (
            <div className="animate-fadeIn">
              <input
                type="text"
                value={formData.start_address || ''}
                onChange={(e) => setFormData({ ...formData, start_address: e.target.value })}
                placeholder="Например: площадь Минина и Пожарского"
                className="w-full px-6 py-4 border-2 border-gray-200 rounded-2xl focus:ring-4 focus:ring-blue-500/30 focus:border-blue-500 transition-all hover:border-gray-300 text-lg"
              />
            </div>
          )}

          {locationType === 'coords' && (
            <div className="grid grid-cols-2 gap-4 animate-fadeIn">
              <div>
                <label className="text-xs text-gray-500 mb-2 block font-semibold">Широта</label>
                <input
                  type="number"
                  value={formData.start_lat ?? ''}
                  onChange={(e) => setFormData({ ...formData, start_lat: e.target.value ? parseFloat(e.target.value) : undefined })}
                  step="0.0001"
                  placeholder="56.3287"
                  className="w-full px-6 py-4 border-2 border-gray-200 rounded-2xl focus:ring-4 focus:ring-blue-500/30 focus:border-blue-500 transition-all hover:border-gray-300"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-2 block font-semibold">Долгота</label>
                <input
                  type="number"
                  value={formData.start_lon ?? ''}
                  onChange={(e) => setFormData({ ...formData, start_lon: e.target.value ? parseFloat(e.target.value) : undefined })}
                  step="0.0001"
                  placeholder="44.002"
                  className="w-full px-6 py-4 border-2 border-gray-200 rounded-2xl focus:ring-4 focus:ring-blue-500/30 focus:border-blue-500 transition-all hover:border-gray-300"
                />
              </div>
            </div>
          )}

          {locationType === 'map' && showMap && (
            <div className="h-80 rounded-2xl overflow-hidden border-4 border-gray-200 shadow-lg animate-fadeIn hover:border-blue-300 transition-all">
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

        {/* Step 4: Time */}
        <div className="bg-white rounded-3xl shadow-2xl p-8 hover:shadow-3xl transition-all duration-300 animate-fadeIn" style={{ animationDelay: '300ms' }}>
          <div className="flex items-center gap-3 mb-6">
            <div className="text-4xl">🕐</div>
            <div>
              <h3 className="text-2xl font-bold text-gray-900">Шаг 4: Время прогулки</h3>
              <p className="text-sm text-gray-500">Когда хотите начать?</p>
            </div>
          </div>

          <div className="space-y-6">
            <div>
              <label className="flex items-center gap-2 text-sm font-bold text-gray-700 mb-3">
                <Calendar className="w-5 h-5 text-orange-600" />
                Желаемое время старта (необязательно)
              </label>
              <input
                type="time"
                value={formData.start_time || ''}
                onChange={(e) => {
                  setFormData({ ...formData, start_time: e.target.value })
                  setCurrentStep(Math.max(currentStep, 4))
                }}
                className="w-full px-6 py-4 border-2 border-gray-200 rounded-2xl focus:ring-4 focus:ring-orange-500/30 focus:border-orange-500 transition-all hover:border-gray-300 text-lg font-semibold"
              />
              <p className="text-xs text-gray-500 mt-2">
                Если не указано — маршрут будет спланирован на ближайшее удобное время
              </p>
            </div>

            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-2xl border-2 border-blue-200">
              <div className="flex items-start gap-3">
                <div className="text-3xl">💡</div>
                <div className="flex-1">
                  <h4 className="font-bold text-gray-900 mb-2">Умное планирование времени</h4>
                  <ul className="text-sm text-gray-700 space-y-2">
                    <li className="flex items-center gap-2">
                      <span className="text-green-600">✓</span>
                      Проверим расписание работы мест
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="text-green-600">✓</span>
                      Учтём ваш часовой пояс
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="text-green-600">✓</span>
                      Предложим оптимальное время, если указанное неудобно
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Coffee & Transit */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-fadeIn" style={{ animationDelay: '400ms' }}>
          {/* Coffee */}
          <div className="bg-gradient-to-br from-amber-50 to-orange-50 border-4 border-amber-300 rounded-3xl p-8 hover:shadow-2xl transition-all duration-300">
            <label className="flex items-center space-x-4 cursor-pointer group">
              <input
                type="checkbox"
                checked={coffeePrefs.enabled}
                onChange={(e) => setCoffeePrefs({ ...coffeePrefs, enabled: e.target.checked })}
                className="w-7 h-7 rounded-xl text-amber-600 focus:ring-amber-500 transition-all cursor-pointer"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Coffee className="w-6 h-6 text-amber-600" />
                  <span className="text-lg font-black text-gray-900">Кофе-брейки</span>
                </div>
                <p className="text-xs text-gray-600">Умный поиск кафе через 2GIS</p>
              </div>
            </label>
            
            {coffeePrefs.enabled && (
              <div className="mt-6 space-y-4 animate-fadeIn">
                <div>
                  <div className="flex justify-between text-sm font-bold text-gray-700 mb-2">
                    <span>Интервал перерывов</span>
                    <span className="text-amber-700">{coffeePrefs.interval_minutes} мин</span>
                  </div>
                  <input
                    type="range"
                    value={coffeePrefs.interval_minutes}
                    onChange={(e) => setCoffeePrefs({ ...coffeePrefs, interval_minutes: parseInt(e.target.value) })}
                    min="30"
                    max="180"
                    step="15"
                    className="w-full h-3 bg-amber-200 rounded-full appearance-none cursor-pointer accent-amber-600"
                  />
                </div>
                
                <button
                  type="button"
                  onClick={() => setShowCoffeeAdvanced(!showCoffeeAdvanced)}
                  className="text-sm text-amber-700 font-bold hover:text-amber-800 flex items-center gap-2 transition-colors"
                >
                  <span className="transform transition-transform" style={{ transform: showCoffeeAdvanced ? 'rotate(90deg)' : 'rotate(0deg)' }}>▶</span>
                  Дополнительные настройки
                </button>
                
                {showCoffeeAdvanced && (
                  <div className="space-y-4 animate-fadeIn bg-white/50 p-4 rounded-xl">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs font-bold text-gray-700 mb-1 block">Кухня</label>
                        <select
                          value={coffeePrefs.cuisine || ''}
                          onChange={(e) => setCoffeePrefs({ ...coffeePrefs, cuisine: e.target.value || undefined })}
                          className="w-full px-3 py-2 border-2 border-amber-300 rounded-xl text-sm focus:ring-2 focus:ring-amber-500"
                        >
                          <option value="">Любая</option>
                          <option value="italian">Итальянская</option>
                          <option value="french">Французская</option>
                          <option value="japanese">Японская</option>
                          <option value="asian">Азиатская</option>
                        </select>
                      </div>
                      
                      <div>
                        <label className="text-xs font-bold text-gray-700 mb-1 block">Диета</label>
                        <select
                          value={coffeePrefs.dietary || ''}
                          onChange={(e) => setCoffeePrefs({ ...coffeePrefs, dietary: e.target.value || undefined })}
                          className="w-full px-3 py-2 border-2 border-amber-300 rounded-xl text-sm focus:ring-2 focus:ring-amber-500"
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
                      <label className="flex items-center space-x-2 text-sm cursor-pointer group">
                        <input
                          type="checkbox"
                          checked={coffeePrefs.outdoor_seating}
                          onChange={(e) => setCoffeePrefs({ ...coffeePrefs, outdoor_seating: e.target.checked })}
                          className="rounded-lg text-amber-600"
                        />
                        <span className="group-hover:text-amber-700 transition-colors">🪑 Терраса</span>
                      </label>
                      
                      <label className="flex items-center space-x-2 text-sm cursor-pointer group">
                        <input
                          type="checkbox"
                          checked={coffeePrefs.wifi}
                          onChange={(e) => setCoffeePrefs({ ...coffeePrefs, wifi: e.target.checked })}
                          className="rounded-lg text-amber-600"
                        />
                        <span className="group-hover:text-amber-700 transition-colors">📶 Wi-Fi</span>
                      </label>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Transit */}
          <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-4 border-green-300 rounded-3xl p-8 hover:shadow-2xl transition-all duration-300">
            <label className="flex items-center space-x-4 cursor-pointer group">
              <input
                type="checkbox"
                checked={formData.allow_transit}
                onChange={(e) => setFormData({ ...formData, allow_transit: e.target.checked })}
                className="w-7 h-7 rounded-xl text-green-600 focus:ring-green-500 transition-all cursor-pointer"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Bus className="w-6 h-6 text-green-600" />
                  <span className="text-lg font-black text-gray-900">Общественный транспорт</span>
                </div>
                <p className="text-xs text-gray-600">Для больших расстояний (&gt;2 км)</p>
              </div>
            </label>
            
            {formData.allow_transit && (
              <div className="mt-6 bg-white/50 p-4 rounded-xl animate-fadeIn">
                <div className="flex items-start gap-3">
                  <div className="text-2xl">🚍</div>
                  <div className="text-sm text-gray-700">
                    <p className="font-semibold mb-2">Что мы сделаем:</p>
                    <ul className="space-y-1">
                      <li>• Найдём ближайшие остановки</li>
                      <li>• Предложим маршруты автобусов/трамваев</li>
                      <li>• Посчитаем экономию времени</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Validation error */}
        {validationError && (
          <div className="bg-gradient-to-r from-red-50 to-rose-50 border-4 border-red-300 text-red-700 px-8 py-6 rounded-3xl animate-scaleIn shadow-2xl">
            <div className="flex items-center gap-4">
              <span className="text-5xl">⚠️</span>
              <div>
                <p className="font-black text-xl mb-1">Проблема с формой</p>
                <p className="text-sm">{validationError}</p>
              </div>
            </div>
          </div>
        )}

        {/* Submit button */}
        <button
          type="submit"
          disabled={mutation.isPending || formProgress < 75}
          className="relative w-full bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white py-6 px-8 rounded-3xl font-black text-xl hover:shadow-2xl transition-all duration-500 transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none animate-slideInUp overflow-hidden group"
          style={{ animationDelay: '500ms' }}
        >
          <div className="absolute inset-0 bg-gradient-to-r from-purple-600 to-pink-600 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
          <div className="relative z-10 flex items-center justify-center gap-3">
            {mutation.isPending ? (
              <>
                <div className="w-8 h-8 border-4 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>Создаём ваш маршрут...</span>
              </>
            ) : formProgress < 75 ? (
              <>
                <span>Заполните форму ({formProgress}%)</span>
              </>
            ) : (
              <>
                <MapPin className="w-7 h-7" />
                <span>Построить маршрут</span>
                <span className="text-3xl">→</span>
              </>
            )}
          </div>
        </button>

        {/* Error */}
        {mutation.isError && (
          <div className="bg-gradient-to-r from-red-50 to-rose-50 border-4 border-red-300 text-red-700 px-8 py-6 rounded-3xl animate-scaleIn shadow-2xl">
            <div className="flex items-center gap-4">
              <span className="text-5xl">❌</span>
              <div>
                <p className="font-black text-xl mb-1">Ошибка при создании маршрута</p>
                <p className="text-sm">
                  {(mutation.error as any)?.response?.data?.detail || 'Проверьте введённые данные и попробуйте ещё раз.'}
                </p>
              </div>
            </div>
          </div>
        )}
      </form>
    </div>
  )
}