import { motion } from 'framer-motion'
import { Clock, Users, Zap } from 'lucide-react'
import type { RouteRequest } from '../../types'
import {
  DEFAULT_ROUTE_HOURS,
  MAX_ROUTE_HOURS,
  MIN_ROUTE_HOURS,
  sanitizeRouteHours,
} from '../../constants/route'

interface Props {
  formData: Partial<RouteRequest>
  updateFormData: (updates: Partial<RouteRequest>) => void
}

const DURATION_PRESETS = [
  { hours: 1, label: '1 час', desc: 'Быстрая прогулка', icon: '⚡' },
  { hours: 2, label: '2 часа', desc: 'Классический маршрут', icon: '🚶' },
  { hours: 3, label: '3 часа', desc: 'Обстоятельно', icon: '🗺️' },
  { hours: 4, label: '4 часа', desc: 'Полудневная программа', icon: '☀️' },
  { hours: 6, label: '6 часов', desc: 'Насыщенный день', icon: '🌆' },
]

const SOCIAL_MODES = [
  { value: 'solo', label: 'Один', icon: '🚶', desc: 'Созерцательная прогулка' },
  { value: 'friends', label: 'С друзьями', icon: '👥', desc: 'Веселая компания' },
  { value: 'family', label: 'С семьёй', icon: '👨‍👩‍👧', desc: 'Семейный отдых' },
]

const INTENSITY_LEVELS = [
  { value: 'relaxed', label: 'Спокойно', icon: '🌸', desc: 'Неспешный темп' },
  { value: 'medium', label: 'Средне', icon: '⚡', desc: 'Комфортный ритм' },
  { value: 'intense', label: 'Активно', icon: '🔥', desc: 'Максимум мест' },
]

export default function StepDuration({ formData, updateFormData }: Props) {
  const hoursValue = sanitizeRouteHours(formData.hours ?? DEFAULT_ROUTE_HOURS)
  const progressPercent = Math.min(
    100,
    Math.max(0, ((hoursValue - MIN_ROUTE_HOURS) / (MAX_ROUTE_HOURS - MIN_ROUTE_HOURS)) * 100),
  )

  return (
    <div className="space-y-10">
      <div className="text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 200 }}
          className="inline-block mb-4"
        >
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-4xl shadow-xl">
            ⏱️
          </div>
        </motion.div>
        <h2 className="text-4xl font-black text-slate-900 dark:text-white mb-3">
          Сколько времени у вас?
        </h2>
        <p className="text-lg text-slate-600 dark:text-slate-400">
          Выберите длительность и характер прогулки
        </p>
      </div>

      {/* Duration Selection */}
      <div>
        <label className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-4">
          <Clock className="w-4 h-4 text-purple-600" />
          Длительность прогулки
        </label>
        
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-4">
          {DURATION_PRESETS.map((preset, index) => {
            const isSelected = formData.hours === preset.hours
            return (
              <motion.button
                key={preset.hours}
                type="button"
                onClick={() => updateFormData({ hours: preset.hours })}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className={`relative p-4 rounded-xl font-semibold transition-all ${
                  isSelected
                    ? 'bg-gradient-to-br from-purple-500 to-pink-600 text-white shadow-lg shadow-purple-500/30'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 border-2 border-slate-200 dark:border-slate-700'
                }`}
              >
                <div className="text-3xl mb-2">{preset.icon}</div>
                <div className="text-sm font-bold">{preset.label}</div>
                <div className="text-xs opacity-70 mt-1">{preset.desc}</div>
              </motion.button>
            )
          })}
        </div>

        {/* Custom Duration Slider */}
        <div className="mt-6 p-4 bg-slate-50 dark:bg-slate-900 rounded-xl">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Или выберите точно
            </span>
            <span className="text-2xl font-bold text-purple-600 dark:text-purple-400">
              {hoursValue}ч
            </span>
          </div>
          <input
            type="range"
            min={MIN_ROUTE_HOURS}
            max={MAX_ROUTE_HOURS}
            step="0.5"
            value={hoursValue}
            onChange={(e) => updateFormData({ hours: sanitizeRouteHours(parseFloat(e.target.value)) })}
            className="w-full h-3 bg-slate-200 dark:bg-slate-700 rounded-full appearance-none cursor-pointer accent-purple-600"
            style={{
              background: `linear-gradient(to right, rgb(168 85 247) 0%, rgb(168 85 247) ${progressPercent}%, rgb(226 232 240) ${progressPercent}%, rgb(226 232 240) 100%)`
            }}
          />
          <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mt-2">
            <span>30 мин</span>
            <span>8 часов</span>
          </div>
        </div>
      </div>

      {/* Social Mode */}
      <div>
        <label className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-4">
          <Users className="w-4 h-4 text-blue-600" />
          С кем идёте?
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {SOCIAL_MODES.map((mode, index) => {
            const isSelected = formData.social_mode === mode.value
            return (
              <motion.button
                key={mode.value}
                type="button"
                onClick={() => updateFormData({ social_mode: mode.value as any })}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                className={`p-5 rounded-xl font-semibold transition-all ${
                  isSelected
                    ? 'bg-gradient-to-br from-blue-500 to-cyan-600 text-white shadow-lg shadow-blue-500/30'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 border-2 border-slate-200 dark:border-slate-700'
                }`}
              >
                <div className="text-4xl mb-3">{mode.icon}</div>
                <div className="text-base font-bold mb-1">{mode.label}</div>
                <div className="text-xs opacity-70">{mode.desc}</div>
              </motion.button>
            )
          })}
        </div>
      </div>

      {/* Intensity Level */}
      <div>
        <label className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-4">
          <Zap className="w-4 h-4 text-orange-600" />
          Интенсивность прогулки
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {INTENSITY_LEVELS.map((level, index) => {
            const isSelected = formData.intensity === level.value
            return (
              <motion.button
                key={level.value}
                type="button"
                onClick={() => updateFormData({ intensity: level.value as any })}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                className={`p-5 rounded-xl font-semibold transition-all ${
                  isSelected
                    ? 'bg-gradient-to-br from-orange-500 to-red-600 text-white shadow-lg shadow-orange-500/30'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 border-2 border-slate-200 dark:border-slate-700'
                }`}
              >
                <div className="text-4xl mb-3">{level.icon}</div>
                <div className="text-base font-bold mb-1">{level.label}</div>
                <div className="text-xs opacity-70">{level.desc}</div>
              </motion.button>
            )
          })}
        </div>
      </div>

      {/* Info Card */}
      <div className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 border-2 border-purple-200 dark:border-purple-800 rounded-xl p-5">
        <p className="text-sm text-purple-900 dark:text-purple-100">
          <span className="font-bold">💡 Помните:</span> AI оптимизирует маршрут под ваши параметры, учитывая время на осмотр каждого места и переходы между ними
        </p>
      </div>
    </div>
  )
}