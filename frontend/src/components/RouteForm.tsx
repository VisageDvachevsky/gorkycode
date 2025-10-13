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
    onError: (error: any) => {
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail
        if (Array.isArray(detail)) {
          const errorMessages = detail.map((err: any) => {
            if (typeof err === 'object' && err.msg) {
              return err.msg
            }
            return String(err)
          }).join('; ')
          setValidationError(`Ошибка валидации: ${errorMessages}`)
        } else if (typeof detail === 'string') {
          setValidationError(detail)
        } else {
          setValidationError('Произошла ошибка при планировании маршрута')
        }
      } else {
        setValidationError(error.message || 'Произошла ошибка при планировании маршрута')
      }
    }
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
      start_time: formData.start_time?.trim() || undefined,
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
    <form onSubmit={handleSubmit} className="space-y-8">
      {/* Header */}
      <div className="text-center space-y-4 animate-fade-in">
        <div className="inline-block">
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 rounded-full blur-2xl opacity-50 animate-pulse-glow" />
            <div className="relative text-8xl animate-bounce-slow">
              ✨
            </div>
          </div>
        </div>
        <h2 className="text-5xl sm:text-6xl font-black bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
          Создай свой маршрут
        </h2>
        <p className="text-xl text-blue-300/80">AI создаст идеальную прогулку специально для тебя</p>
      </div>

      {/* Step 1: Interests */}
      <div className="group relative animate-fade-in-up" style={{ animationDelay: '100ms' }}>
        <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-600 to-pink-600 rounded-3xl opacity-20 group-hover:opacity-40 blur transition-all" />
        <div className="relative backdrop-blur-2xl bg-white/10 border border-white/20 rounded-3xl p-8 hover:border-white/40 transition-all">
          <div className="flex items-center gap-4 mb-6">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-pink-500 rounded-2xl blur-lg opacity-50" />
              <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
            </div>
            <div>
              <h3 className="text-3xl font-black text-white">Твои интересы</h3>
              <p className="text-purple-300/70">Расскажи, что тебе интересно</p>
            </div>
          </div>
          
          <textarea
            value={formData.interests}
            onChange={(e) => setFormData({ ...formData, interests: e.target.value })}
            placeholder="Например: архитектура, история, уютные кафе, панорамные виды..."
            rows={4}
            className="w-full px-6 py-4 bg-slate-900/50 border-2 border-purple-500/30 rounded-2xl focus:ring-4 focus:ring-purple-500/30 focus:border-purple-500/50 transition-all text-white text-lg hover:border-purple-500/50 backdrop-blur-xl placeholder-purple-300/50 resize-none"
          />
        </div>
      </div>

      {/* Categories */}
      {!categoriesLoading && categories.length > 0 && (
        <div className="group relative animate-fade-in-up" style={{ animationDelay: '150ms' }}>
          <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-600 to-cyan-600 rounded-3xl opacity-20 group-hover:opacity-40 blur transition-all" />
          <div className="relative backdrop-blur-2xl bg-white/10 border border-white/20 rounded-3xl p-8 hover:border-white/40 transition-all">
            <div className="flex items-center gap-4 mb-6">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-2xl blur-lg opacity-50" />
                <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                  <span className="text-3xl">🏛️</span>
                </div>
              </div>
              <div>
                <h3 className="text-3xl font-black text-white">Категории мест</h3>
                <p className="text-blue-300/70">Выбери что хочешь увидеть</p>
              </div>
            </div>
            
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {categories.map((cat) => (
                <button
                  key={cat.name}
                  type="button"
                  onClick={() => toggleCategory(cat.name)}
                  className={`px-4 py-3 rounded-xl font-semibold transition-all transform hover:scale-105 ${
                    selectedCategories.includes(cat.name)
                      ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-lg scale-105'
                      : 'bg-slate-900/50 text-blue-200 border border-blue-500/30 hover:border-blue-500/50 backdrop-blur-xl'
                  }`}
                >
                  <span className="text-xl mr-2">{cat.emoji}</span>
                  {cat.name}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Duration */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="group relative animate-slide-in-left" style={{ animationDelay: '200ms' }}>
          <div className="absolute -inset-0.5 bg-gradient-to-r from-orange-600 to-red-600 rounded-3xl opacity-20 group-hover:opacity-40 blur transition-all" />
          <div className="relative backdrop-blur-2xl bg-white/10 border border-white/20 rounded-3xl p-8 hover:border-white/40 transition-all">
            <div className="flex items-center gap-4 mb-6">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-orange-500 to-red-500 rounded-2xl blur-lg opacity-50" />
                <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center">
                  <Clock className="w-8 h-8 text-white" />
                </div>
              </div>
              <div>
                <h3 className="text-3xl font-black text-white">Длительность</h3>
                <p className="text-orange-300/70">Сколько у тебя времени?</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <input
                type="range"
                min="1"
                max="8"
                step="0.5"
                value={formData.hours}
                onChange={(e) => setFormData({ ...formData, hours: parseFloat(e.target.value) })}
                className="flex-1 h-3 bg-slate-900/50 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-6 [&::-webkit-slider-thumb]:h-6 [&::-webkit-slider-thumb]:bg-gradient-to-r [&::-webkit-slider-thumb]:from-orange-500 [&::-webkit-slider-thumb]:to-red-500 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:shadow-lg"
              />
              <div className="w-24 px-4 py-2 bg-gradient-to-r from-orange-500 to-red-500 rounded-xl text-white font-black text-2xl text-center">
                {formData.hours}ч
              </div>
            </div>
          </div>
        </div>

        {/* Social Mode */}
        <div className="group relative animate-slide-in-right" style={{ animationDelay: '200ms' }}>
          <div className="absolute -inset-0.5 bg-gradient-to-r from-pink-600 to-rose-600 rounded-3xl opacity-20 group-hover:opacity-40 blur transition-all" />
          <div className="relative backdrop-blur-2xl bg-white/10 border border-white/20 rounded-3xl p-8 hover:border-white/40 transition-all">
            <div className="flex items-center gap-4 mb-6">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-pink-500 to-rose-500 rounded-2xl blur-lg opacity-50" />
                <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-pink-500 to-rose-500 flex items-center justify-center">
                  <Users className="w-8 h-8 text-white" />
                </div>
              </div>
              <div>
                <h3 className="text-3xl font-black text-white">Компания</h3>
                <p className="text-pink-300/70">С кем идём?</p>
              </div>
            </div>
            
            <div className="grid grid-cols-3 gap-3">
              {[
                { value: 'solo', emoji: '🚶', label: 'Один', gradient: 'from-purple-500 to-pink-600' },
                { value: 'couple', emoji: '💑', label: 'Вдвоём', gradient: 'from-pink-500 to-red-600' },
                { value: 'group', emoji: '👥', label: 'Группа', gradient: 'from-orange-500 to-pink-600' }
              ].map((mode) => (
                <button
                  key={mode.value}
                  type="button"
                  onClick={() => setFormData({ ...formData, social_mode: mode.value as any })}
                  className={`px-4 py-4 rounded-2xl font-bold transition-all transform hover:scale-105 ${
                    formData.social_mode === mode.value
                      ? `bg-gradient-to-br ${mode.gradient} text-white shadow-2xl scale-105`
                      : 'bg-slate-900/50 text-pink-200 border border-pink-500/30 hover:border-pink-500/50 backdrop-blur-xl'
                  }`}
                >
                  <div className="text-4xl mb-2">{mode.emoji}</div>
                  <div className="text-sm">{mode.label}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Intensity */}
      <div className="group relative animate-fade-in-up" style={{ animationDelay: '250ms' }}>
        <div className="absolute -inset-0.5 bg-gradient-to-r from-yellow-600 to-orange-600 rounded-3xl opacity-20 group-hover:opacity-40 blur transition-all" />
        <div className="relative backdrop-blur-2xl bg-white/10 border border-white/20 rounded-3xl p-8 hover:border-white/40 transition-all">
          <div className="flex items-center gap-4 mb-6">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-yellow-500 to-orange-500 rounded-2xl blur-lg opacity-50" />
              <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-yellow-500 to-orange-500 flex items-center justify-center">
                <Zap className="w-8 h-8 text-white" />
              </div>
            </div>
            <div>
              <h3 className="text-3xl font-black text-white">Интенсивность</h3>
              <p className="text-yellow-300/70">Как быстро будем двигаться?</p>
            </div>
          </div>
          
          <div className="grid grid-cols-3 gap-4">
            {[
              { value: 'slow', emoji: '🐢', label: 'Неспешно', desc: 'Больше остановок', gradient: 'from-green-500 to-emerald-600' },
              { value: 'medium', emoji: '🚶', label: 'Средне', desc: 'Баланс', gradient: 'from-blue-500 to-cyan-600' },
              { value: 'fast', emoji: '🏃', label: 'Активно', desc: 'Много за раз', gradient: 'from-orange-500 to-red-600' }
            ].map((level) => (
              <button
                key={level.value}
                type="button"
                onClick={() => setFormData({ ...formData, intensity: level.value as any })}
                className={`px-6 py-6 rounded-2xl font-bold transition-all transform hover:scale-105 text-center ${
                  formData.intensity === level.value
                    ? `bg-gradient-to-br ${level.gradient} text-white shadow-2xl scale-105`
                    : 'bg-slate-900/50 text-blue-200 border border-blue-500/30 hover:border-blue-500/50 backdrop-blur-xl'
                }`}
              >
                <div className="text-5xl mb-2">{level.emoji}</div>
                <div className="text-lg font-black">{level.label}</div>
                <div className="text-xs opacity-70 mt-1">{level.desc}</div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Location */}
      <div className="group relative animate-slide-in-left" style={{ animationDelay: '300ms' }}>
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
              <p className="text-cyan-300/70">Откуда начнём?</p>
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
                    : 'bg-slate-900/50 text-cyan-200 border border-cyan-500/30 hover:border-cyan-500/50 backdrop-blur-xl'
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
                className="w-full px-6 py-4 bg-slate-900/50 border-2 border-cyan-500/30 rounded-2xl focus:ring-4 focus:ring-cyan-500/30 focus:border-cyan-500/50 transition-all text-white text-lg hover:border-cyan-500/50 backdrop-blur-xl placeholder-cyan-300/50"
              />
            </div>
          )}

          {locationType === 'coords' && (
            <div className="grid grid-cols-2 gap-4 animate-fade-in">
              <div>
                <label className="text-sm text-cyan-300/70 mb-2 block font-semibold">Широта</label>
                <input
                  type="number"
                  value={formData.start_lat ?? ''}
                  onChange={(e) => setFormData({ ...formData, start_lat: e.target.value ? parseFloat(e.target.value) : undefined })}
                  step="0.0001"
                  placeholder="56.3287"
                  className="w-full px-6 py-4 bg-slate-900/50 border-2 border-cyan-500/30 rounded-2xl focus:ring-4 focus:ring-cyan-500/30 focus:border-cyan-500/50 transition-all text-white hover:border-cyan-500/50 backdrop-blur-xl placeholder-cyan-300/50"
                />
              </div>
              <div>
                <label className="text-sm text-cyan-300/70 mb-2 block font-semibold">Долгота</label>
                <input
                  type="number"
                  value={formData.start_lon ?? ''}
                  onChange={(e) => setFormData({ ...formData, start_lon: e.target.value ? parseFloat(e.target.value) : undefined })}
                  step="0.0001"
                  placeholder="44.002"
                  className="w-full px-6 py-4 bg-slate-900/50 border-2 border-cyan-500/30 rounded-2xl focus:ring-4 focus:ring-cyan-500/30 focus:border-cyan-500/50 transition-all text-white hover:border-cyan-500/50 backdrop-blur-xl placeholder-cyan-300/50"
                />
              </div>
            </div>
          )}

          {locationType === 'map' && showMap && (
            <div className="h-96 rounded-2xl overflow-hidden border-4 border-cyan-500/30 shadow-2xl animate-fade-in hover:border-cyan-500/50 transition-all">
              <MapContainer
                center={[formData.start_lat ?? DEFAULT_CENTER.lat, formData.start_lon ?? DEFAULT_CENTER.lon]}
                zoom={13}
                className="h-full w-full"
              >
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                />
                <LocationPicker onLocationSelect={(lat, lon) => setFormData({ ...formData, start_lat: lat, start_lon: lon })} />
              </MapContainer>
            </div>
          )}
        </div>
      </div>

      {/* Optional: Start Time */}
      <div className="group relative animate-fade-in-up" style={{ animationDelay: '350ms' }}>
        <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-3xl opacity-20 group-hover:opacity-40 blur transition-all" />
        <div className="relative backdrop-blur-2xl bg-white/10 border border-white/20 rounded-3xl p-8 hover:border-white/40 transition-all">
          <div className="flex items-center gap-4 mb-4">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-2xl blur-lg opacity-50" />
              <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
                <Calendar className="w-8 h-8 text-white" />
              </div>
            </div>
            <div>
              <h3 className="text-3xl font-black text-white">Время старта (опционально)</h3>
              <p className="text-indigo-300/70">Когда начинаем прогулку?</p>
            </div>
          </div>
          
          <input
            type="time"
            value={formData.start_time || ''}
            onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
            className="w-full px-6 py-4 bg-slate-900/50 border-2 border-indigo-500/30 rounded-2xl focus:ring-4 focus:ring-indigo-500/30 focus:border-indigo-500/50 transition-all text-white text-lg hover:border-indigo-500/50 backdrop-blur-xl"
          />
        </div>
      </div>

      {/* Coffee Preferences */}
      <div className="group relative animate-slide-in-right" style={{ animationDelay: '400ms' }}>
        <div className="absolute -inset-0.5 bg-gradient-to-r from-amber-600 to-orange-600 rounded-3xl opacity-20 group-hover:opacity-40 blur transition-all" />
        <div className="relative backdrop-blur-2xl bg-white/10 border border-white/20 rounded-3xl p-8 hover:border-white/40 transition-all">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-amber-500 to-orange-500 rounded-2xl blur-lg opacity-50" />
                <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
                  <Coffee className="w-8 h-8 text-white" />
                </div>
              </div>
              <div>
                <h3 className="text-3xl font-black text-white">Кофе-паузы</h3>
                <p className="text-amber-300/70">Добавим кофейни?</p>
              </div>
            </div>
            
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={coffeePrefs.enabled}
                onChange={(e) => setCoffeePrefs({ ...coffeePrefs, enabled: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-14 h-7 bg-slate-900/50 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-amber-500/30 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[4px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-gradient-to-r peer-checked:from-amber-500 peer-checked:to-orange-500"></div>
            </label>
          </div>
          
          {coffeePrefs.enabled && (
            <div className="space-y-4 animate-fade-in">
              <div>
                <label className="text-white font-semibold mb-2 block">Интервал кофе-пауз (минут)</label>
                <input
                  type="number"
                  min="30"
                  max="180"
                  step="15"
                  value={coffeePrefs.interval_minutes}
                  onChange={(e) => setCoffeePrefs({ ...coffeePrefs, interval_minutes: parseInt(e.target.value) })}
                  className="w-full px-6 py-3 bg-slate-900/50 border-2 border-amber-500/30 rounded-xl focus:ring-4 focus:ring-amber-500/30 focus:border-amber-500/50 transition-all text-white hover:border-amber-500/50 backdrop-blur-xl"
                />
              </div>
              
              <button
                type="button"
                onClick={() => setShowCoffeeAdvanced(!showCoffeeAdvanced)}
                className="text-amber-300 hover:text-amber-200 font-semibold transition-colors"
              >
                {showCoffeeAdvanced ? '▼ Скрыть доп. настройки' : '► Показать доп. настройки'}
              </button>
              
              {showCoffeeAdvanced && (
                <div className="space-y-3 animate-fade-in">
                  <label className="flex items-center gap-3 cursor-pointer group/label">
                    <input
                      type="checkbox"
                      checked={coffeePrefs.outdoor_seating}
                      onChange={(e) => setCoffeePrefs({ ...coffeePrefs, outdoor_seating: e.target.checked })}
                      className="w-5 h-5 rounded border-2 border-amber-500/50 bg-slate-900/50 checked:bg-gradient-to-r checked:from-amber-500 checked:to-orange-500 focus:ring-4 focus:ring-amber-500/30 transition-all"
                    />
                    <span className="text-white font-medium group-hover/label:text-amber-300 transition-colors">Летняя веранда</span>
                  </label>
                  
                  <label className="flex items-center gap-3 cursor-pointer group/label">
                    <input
                      type="checkbox"
                      checked={coffeePrefs.wifi}
                      onChange={(e) => setCoffeePrefs({ ...coffeePrefs, wifi: e.target.checked })}
                      className="w-5 h-5 rounded border-2 border-amber-500/50 bg-slate-900/50 checked:bg-gradient-to-r checked:from-amber-500 checked:to-orange-500 focus:ring-4 focus:ring-amber-500/30 transition-all"
                    />
                    <span className="text-white font-medium group-hover/label:text-amber-300 transition-colors">Wi-Fi</span>
                  </label>
                  
                  <div>
                    <label className="text-white font-medium mb-2 block">Радиус поиска (км)</label>
                    <input
                      type="number"
                      min="0.1"
                      max="3"
                      step="0.1"
                      value={coffeePrefs.search_radius_km}
                      onChange={(e) => setCoffeePrefs({ ...coffeePrefs, search_radius_km: parseFloat(e.target.value) })}
                      className="w-full px-4 py-2 bg-slate-900/50 border-2 border-amber-500/30 rounded-xl focus:ring-4 focus:ring-amber-500/30 focus:border-amber-500/50 transition-all text-white hover:border-amber-500/50 backdrop-blur-xl"
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Transit */}
      <div className="group relative animate-fade-in" style={{ animationDelay: '450ms' }}>
        <div className="absolute -inset-0.5 bg-gradient-to-r from-green-600 to-emerald-600 rounded-3xl opacity-20 group-hover:opacity-40 blur transition-all" />
        <div className="relative backdrop-blur-2xl bg-white/10 border border-white/20 rounded-3xl p-8 hover:border-white/40 transition-all">
          <label className="flex items-center justify-between cursor-pointer">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-green-500 to-emerald-500 rounded-2xl blur-lg opacity-50" />
                <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center">
                  <Bus className="w-8 h-8 text-white" />
                </div>
              </div>
              <div>
                <h3 className="text-3xl font-black text-white">Общественный транспорт</h3>
                <p className="text-green-300/70">Для дальних переходов</p>
              </div>
            </div>
            
            <input
              type="checkbox"
              checked={formData.allow_transit}
              onChange={(e) => setFormData({ ...formData, allow_transit: e.target.checked })}
              className="w-7 h-7 rounded border-2 border-green-500/50 bg-slate-900/50 checked:bg-gradient-to-r checked:from-green-500 checked:to-emerald-500 focus:ring-4 focus:ring-green-500/30 transition-all"
            />
          </label>
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
        style={{ animationDelay: '500ms' }}
      >
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 transition-transform group-hover:scale-110" />
        <div className="absolute inset-0 bg-gradient-to-r from-cyan-600 via-blue-600 to-purple-600 opacity-0 group-hover:opacity-100 transition-opacity animate-gradient" />
        <div className="relative z-10 flex items-center justify-center gap-4">
          {mutation.isPending ? (
            <>
              <div className="w-8 h-8 border-4 border-white border-t-transparent rounded-full animate-spin" />
              <span className="text-2xl font-black text-white">Создаём магию...</span>
            </>
          ) : (
            <>
              <span className="text-4xl">✨</span>
              <span className="text-2xl font-black text-white">Создать маршрут</span>
              <span className="text-4xl">🗺️</span>
            </>
          )}
        </div>
      </button>
    </form>
  )
}