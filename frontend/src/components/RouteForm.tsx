import { useState, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import { Clock, MapPin, Users, Zap, Calendar, Coffee, Bus, Sparkles } from 'lucide-react'
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
  const [showCoffeeAdvanced, setShowCoffeeAdvanced] = useState(false)
  
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

  return (
    <form onSubmit={handleSubmit} className="space-y-8 max-w-5xl mx-auto">
      {/* Form header */}
      <div className="text-center mb-12 animate-fade-in">
        <div className="inline-flex items-center gap-3 px-6 py-3 rounded-full backdrop-blur-xl bg-white/5 border border-white/10 mb-6">
          <Sparkles className="w-5 h-5 text-yellow-400 animate-pulse" />
          <span className="text-blue-300">Заполните форму, чтобы создать маршрут</span>
        </div>
        <h2 className="text-5xl sm:text-6xl font-black bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent mb-4">
          Создаём маршрут
        </h2>
        <p className="text-xl text-blue-300/70">Расскажите о себе, и AI подберёт идеальные места</p>
      </div>

      {/* Step 1: Interests */}
      <div className="group relative animate-slide-in-left">
        <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-600 to-purple-600 rounded-3xl opacity-20 group-hover:opacity-40 blur transition-all" />
        <div className="relative backdrop-blur-2xl bg-white/10 border border-white/20 rounded-3xl p-8 hover:border-white/40 transition-all">
          <div className="flex items-center gap-4 mb-6">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-2xl blur-lg opacity-50" />
              <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                <span className="text-3xl">✨</span>
              </div>
            </div>
            <div>
              <h3 className="text-3xl font-black text-white">Ваши интересы</h3>
              <p className="text-blue-300/70">Что вам нравится?</p>
            </div>
          </div>
          
          <textarea
            value={formData.interests}
            onChange={(e) => setFormData({ ...formData, interests: e.target.value })}
            placeholder="Например: уличное искусство, панорамные виды, советская архитектура, атмосферные кафе..."
            className="w-full px-6 py-4 bg-white/5 border-2 border-white/10 rounded-2xl focus:ring-4 focus:ring-blue-500/30 focus:border-blue-500/50 transition-all resize-none text-white placeholder-blue-300/30 hover:border-white/20 text-lg backdrop-blur-xl"
            rows={4}
          />
          
          {formData.interests.trim() && (
            <div className="mt-4 flex items-center gap-3 px-6 py-4 bg-gradient-to-r from-green-500/20 to-emerald-500/20 rounded-2xl border border-green-500/30 animate-fade-in">
              <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center">
                <span className="text-white font-bold">✓</span>
              </div>
              <span className="text-green-200 font-semibold">Отлично! Интересы учтены</span>
            </div>
          )}

          {/* Categories */}
          <div className="mt-8">
            <label className="block text-xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="text-3xl">🏷️</span>
              Или выберите категории
            </label>
            
            {categoriesLoading ? (
              <div className="flex items-center justify-center py-16">
                <div className="relative w-20 h-20">
                  <div className="absolute inset-0 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
                  <div className="absolute inset-2 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin-reverse" />
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                {categories.map((cat, index) => (
                  <button
                    key={cat.value}
                    type="button"
                    onClick={() => toggleCategory(cat.value)}
                    className={`group relative px-6 py-4 rounded-2xl text-sm font-bold transition-all transform hover:scale-105 animate-fade-in ${
                      selectedCategories.includes(cat.value)
                        ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-2xl shadow-blue-500/50'
                        : 'bg-white/5 text-blue-200 border border-white/10 hover:border-white/30 backdrop-blur-xl'
                    }`}
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    {selectedCategories.includes(cat.value) && (
                      <div className="absolute inset-0 bg-gradient-to-r from-purple-600 to-pink-600 rounded-2xl animate-pulse opacity-50" />
                    )}
                    <span className="relative block">{cat.label}</span>
                    <span className="relative block text-xs mt-1 opacity-70">({cat.count})</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Step 2: Details */}
      <div className="group relative animate-slide-in-right" style={{ animationDelay: '100ms' }}>
        <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-600 to-pink-600 rounded-3xl opacity-20 group-hover:opacity-40 blur transition-all" />
        <div className="relative backdrop-blur-2xl bg-white/10 border border-white/20 rounded-3xl p-8 hover:border-white/40 transition-all">
          <div className="flex items-center gap-4 mb-6">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-pink-500 rounded-2xl blur-lg opacity-50" />
              <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                <span className="text-3xl">⚙️</span>
              </div>
            </div>
            <div>
              <h3 className="text-3xl font-black text-white">Детали</h3>
              <p className="text-blue-300/70">Настройки прогулки</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Duration */}
            <div className="space-y-3">
              <label className="flex items-center gap-3 text-lg font-bold text-white">
                <Clock className="w-6 h-6 text-cyan-400" />
                Длительность
              </label>
              <div className="relative group/input">
                <input
                  type="number"
                  value={formData.hours}
                  onChange={(e) => setFormData({ ...formData, hours: parseFloat(e.target.value) || 3 })}
                  min="0.5"
                  max="12"
                  step="0.5"
                  className="w-full px-6 py-4 bg-white/5 border-2 border-white/10 rounded-2xl focus:ring-4 focus:ring-cyan-500/30 focus:border-cyan-500/50 transition-all text-white text-2xl font-black hover:border-white/20 backdrop-blur-xl group-hover/input:scale-105"
                  required
                />
                <div className="absolute right-6 top-1/2 -translate-y-1/2 text-cyan-400/70 font-semibold pointer-events-none">
                  часов
                </div>
              </div>
            </div>

            {/* Social mode */}
            <div className="space-y-3">
              <label className="flex items-center gap-3 text-lg font-bold text-white">
                <Users className="w-6 h-6 text-purple-400" />
                Компания
              </label>
              <select
                value={formData.social_mode}
                onChange={(e) => setFormData({ ...formData, social_mode: e.target.value as any })}
                className="w-full px-6 py-4 bg-white/5 border-2 border-white/10 rounded-2xl focus:ring-4 focus:ring-purple-500/30 focus:border-purple-500/50 transition-all text-white text-lg font-semibold hover:border-white/20 backdrop-blur-xl appearance-none cursor-pointer hover:scale-105"
              >
                <option value="solo">🚶 Один/одна</option>
                <option value="friends">👥 С друзьями</option>
                <option value="family">👨‍👩‍👧 С семьёй</option>
              </select>
            </div>

            {/* Start time */}
            <div className="space-y-3">
              <label className="flex items-center gap-3 text-lg font-bold text-white">
                <Calendar className="w-6 h-6 text-orange-400" />
                Время старта
              </label>
              <input
                type="time"
                value={formData.start_time || ''}
                onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                className="w-full px-6 py-4 bg-white/5 border-2 border-white/10 rounded-2xl focus:ring-4 focus:ring-orange-500/30 focus:border-orange-500/50 transition-all text-white text-lg font-semibold hover:border-white/20 backdrop-blur-xl hover:scale-105"
              />
            </div>
          </div>

          {/* Intensity */}
          <div className="mt-8 space-y-4">
            <label className="flex items-center gap-3 text-lg font-bold text-white">
              <Zap className="w-6 h-6 text-yellow-400" />
              Интенсивность
            </label>
            <div className="grid grid-cols-3 gap-4">
              {[
                { value: 'relaxed', emoji: '🌸', label: 'Спокойно', gradient: 'from-green-500 to-emerald-600' },
                { value: 'medium', emoji: '⚡', label: 'Средне', gradient: 'from-blue-500 to-indigo-600' },
                { value: 'intense', emoji: '🔥', label: 'Активно', gradient: 'from-orange-500 to-red-600' }
              ].map((level) => (
                <button
                  key={level.value}
                  type="button"
                  onClick={() => setFormData({ ...formData, intensity: level.value as any })}
                  className={`relative px-6 py-6 rounded-2xl font-bold transition-all transform hover:scale-110 ${
                    formData.intensity === level.value
                      ? `bg-gradient-to-br ${level.gradient} text-white shadow-2xl scale-105`
                      : 'bg-white/5 text-blue-200 border border-white/10 hover:border-white/30 backdrop-blur-xl'
                  }`}
                >
                  <div className="text-5xl mb-2 transform transition-transform">{level.emoji}</div>
                  <div className="text-lg">{level.label}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Step 3: Location */}
      <div className="group relative animate-slide-in-left" style={{ animationDelay: '200ms' }}>
        <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-600 to-blue-600 rounded-3xl opacity-20 group-hover:opacity-40 blur transition-all" />
        <div className="relative backdrop-blur-2xl bg-white/10 border border-white/20 rounded-3xl p-8 hover:border-white/40 transition-all">
          <div className="flex items-center gap-4 mb-6">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-2xl blur-lg opacity-50" />
              <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center">
                <MapPin className="w-8 h-8 text-white" />
              </div>
            </div>
            <div>
              <h3 className="text-3xl font-black text-white">Точка старта</h3>
              <p className="text-blue-300/70">Откуда начнём?</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-4 mb-6">
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
                className={`px-8 py-4 rounded-2xl font-bold transition-all transform hover:scale-105 ${
                  locationType === type.value
                    ? `bg-gradient-to-r ${type.color} text-white shadow-2xl scale-105`
                    : 'bg-white/5 text-blue-200 border border-white/10 hover:border-white/30 backdrop-blur-xl'
                }`}
              >
                <span className="text-2xl mr-3">{type.icon}</span>
                {type.label}
              </button>
            ))}
          </div>

          {locationType === 'address' && (
            <div className="animate-fade-in">
              <input
                type="text"
                value={formData.start_address || ''}
                onChange={(e) => setFormData({ ...formData, start_address: e.target.value })}
                placeholder="Например: площадь Минина и Пожарского"
                className="w-full px-6 py-4 bg-white/5 border-2 border-white/10 rounded-2xl focus:ring-4 focus:ring-blue-500/30 focus:border-blue-500/50 transition-all text-white text-lg hover:border-white/20 backdrop-blur-xl placeholder-blue-300/30"
              />
            </div>
          )}

          {locationType === 'coords' && (
            <div className="grid grid-cols-2 gap-4 animate-fade-in">
              <div>
                <label className="text-sm text-blue-300/70 mb-2 block font-semibold">Широта</label>
                <input
                  type="number"
                  value={formData.start_lat ?? ''}
                  onChange={(e) => setFormData({ ...formData, start_lat: e.target.value ? parseFloat(e.target.value) : undefined })}
                  step="0.0001"
                  placeholder="56.3287"
                  className="w-full px-6 py-4 bg-white/5 border-2 border-white/10 rounded-2xl focus:ring-4 focus:ring-blue-500/30 focus:border-blue-500/50 transition-all text-white hover:border-white/20 backdrop-blur-xl"
                />
              </div>
              <div>
                <label className="text-sm text-blue-300/70 mb-2 block font-semibold">Долгота</label>
                <input
                  type="number"
                  value={formData.start_lon ?? ''}
                  onChange={(e) => setFormData({ ...formData, start_lon: e.target.value ? parseFloat(e.target.value) : undefined })}
                  step="0.0001"
                  placeholder="44.002"
                  className="w-full px-6 py-4 bg-white/5 border-2 border-white/10 rounded-2xl focus:ring-4 focus:ring-blue-500/30 focus:border-blue-500/50 transition-all text-white hover:border-white/20 backdrop-blur-xl"
                />
              </div>
            </div>
          )}

          {locationType === 'map' && showMap && (
            <div className="h-96 rounded-2xl overflow-hidden border-4 border-white/20 shadow-2xl animate-fade-in hover:border-white/40 transition-all">
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
      </div>

      {/* Coffee & Transit */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-fade-in" style={{ animationDelay: '300ms' }}>
        {/* Coffee */}
        <div className="group relative">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-amber-600 to-orange-600 rounded-3xl opacity-20 group-hover:opacity-40 blur transition-all" />
          <div className="relative backdrop-blur-2xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-400/30 rounded-3xl p-8 hover:border-amber-400/50 transition-all">
            <label className="flex items-center gap-4 cursor-pointer group/label">
              <input
                type="checkbox"
                checked={coffeePrefs.enabled}
                onChange={(e) => setCoffeePrefs({ ...coffeePrefs, enabled: e.target.checked })}
                className="w-8 h-8 rounded-xl text-amber-600 focus:ring-amber-500 transition-all cursor-pointer"
              />
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-1">
                  <Coffee className="w-7 h-7 text-amber-400" />
                  <span className="text-2xl font-black text-white">Кофе-брейки</span>
                </div>
                <p className="text-sm text-amber-200/70">2GIS найдёт лучшие кафе</p>
              </div>
            </label>
            
            {coffeePrefs.enabled && (
              <div className="mt-6 space-y-4 animate-fade-in">
                <div>
                  <div className="flex justify-between text-sm font-bold text-white mb-3">
                    <span>Интервал</span>
                    <span className="text-amber-300">{coffeePrefs.interval_minutes} мин</span>
                  </div>
                  <input
                    type="range"
                    value={coffeePrefs.interval_minutes}
                    onChange={(e) => setCoffeePrefs({ ...coffeePrefs, interval_minutes: parseInt(e.target.value) })}
                    min="30"
                    max="180"
                    step="15"
                    className="w-full h-4 bg-amber-900/30 rounded-full appearance-none cursor-pointer accent-amber-500"
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Transit */}
        <div className="group relative">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-green-600 to-emerald-600 rounded-3xl opacity-20 group-hover:opacity-40 blur transition-all" />
          <div className="relative backdrop-blur-2xl bg-gradient-to-br from-green-500/20 to-emerald-500/20 border border-green-400/30 rounded-3xl p-8 hover:border-green-400/50 transition-all">
            <label className="flex items-center gap-4 cursor-pointer group/label">
              <input
                type="checkbox"
                checked={formData.allow_transit}
                onChange={(e) => setFormData({ ...formData, allow_transit: e.target.checked })}
                className="w-8 h-8 rounded-xl text-green-600 focus:ring-green-500 transition-all cursor-pointer"
              />
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-1">
                  <Bus className="w-7 h-7 text-green-400" />
                  <span className="text-2xl font-black text-white">Транспорт</span>
                </div>
                <p className="text-sm text-green-200/70">Для дальних переходов</p>
              </div>
            </label>
          </div>
        </div>
      </div>

      {/* Validation error */}
      {validationError && (
        <div className="relative group animate-shake">
          <div className="absolute -inset-1 bg-gradient-to-r from-red-600 to-pink-600 rounded-3xl opacity-50 group-hover:opacity-70 blur-lg transition-all" />
          <div className="relative backdrop-blur-2xl bg-gradient-to-br from-red-500/20 to-pink-500/20 border-2 border-red-400/50 rounded-3xl p-8">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-red-500 flex items-center justify-center flex-shrink-0">
                <span className="text-4xl">⚠️</span>
              </div>
              <div>
                <p className="font-black text-2xl text-white mb-1">Проблема</p>
                <p className="text-red-200">{validationError}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Submit button */}
      <button
        type="submit"
        disabled={mutation.isPending}
        className="group relative w-full py-8 px-12 overflow-hidden rounded-3xl transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none animate-fade-in"
        style={{ animationDelay: '400ms' }}
      >
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 transition-transform group-hover:scale-110" />
        <div className="absolute inset-0 bg-gradient-to-r from-cyan-600 via-blue-600 to-purple-600 opacity-0 group-hover:opacity-100 transition-opacity animate-gradient" />
        <div className="relative z-10 flex items-center justify-center gap-4">
          {mutation.isPending ? (
            <>
              <div className="w-10 h-10 border-4 border-white border-t-transparent rounded-full animate-spin" />
              <span className="text-3xl font-black text-white">Создаём маршрут...</span>
            </>
          ) : (
            <>
              <MapPin className="w-10 h-10 text-white" />
              <span className="text-3xl font-black text-white">Построить маршрут</span>
              <span className="text-5xl transform group-hover:translate-x-2 transition-transform">→</span>
            </>
          )}
        </div>
      </button>

      {/* Error */}
      {mutation.isError && (
        <div className="relative group animate-fade-in">
          <div className="absolute -inset-1 bg-gradient-to-r from-red-600 to-pink-600 rounded-3xl opacity-50 group-hover:opacity-70 blur-lg transition-all" />
          <div className="relative backdrop-blur-2xl bg-gradient-to-br from-red-500/20 to-pink-500/20 border-2 border-red-400/50 rounded-3xl p-8">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-red-500 flex items-center justify-center flex-shrink-0">
                <span className="text-4xl">❌</span>
              </div>
              <div>
                <p className="font-black text-2xl text-white mb-1">Ошибка</p>
                <p className="text-red-200">
                  {(mutation.error as any)?.response?.data?.detail || 'Проверьте данные и попробуйте ещё раз'}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </form>
  )
}