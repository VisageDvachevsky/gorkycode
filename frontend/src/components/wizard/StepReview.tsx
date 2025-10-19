import { motion } from 'framer-motion'
import { Check, Clock, MapPin, Users, Zap, Coffee, Bus, Tag } from 'lucide-react'
import type { RouteRequest, Category } from '../../types'
import { DEFAULT_ROUTE_HOURS, sanitizeRouteHours } from '../../constants/route'

interface Props {
  formData: Partial<RouteRequest>
  categories: Category[]
}

export default function StepReview({ formData, categories }: Props) {
  const selectedCategories = categories.filter(c => formData.categories?.includes(c.value))
  const durationHours = sanitizeRouteHours(formData.hours ?? DEFAULT_ROUTE_HOURS)

  const getSocialModeLabel = (mode: string) => {
    const modes = {
      solo: '🚶 Один',
      friends: '👥 С друзьями',
      family: '👨‍👩‍👧 С семьёй',
    }
    return modes[mode as keyof typeof modes] || mode
  }

  const getIntensityLabel = (intensity: string) => {
    const levels = {
      relaxed: '🌸 Спокойно',
      medium: '⚡ Средне',
      intense: '🔥 Активно',
    }
    return levels[intensity as keyof typeof levels] || intensity
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
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-4xl shadow-xl">
            🎯
          </div>
        </motion.div>
        <h2 className="text-4xl font-black text-slate-900 dark:text-white mb-3">
          Всё готово!
        </h2>
        <p className="text-lg text-slate-600 dark:text-slate-400">
          Проверьте настройки перед созданием маршрута
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Interests */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-6 bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 border-2 border-purple-200 dark:border-purple-800 rounded-xl"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-purple-600 rounded-xl flex items-center justify-center text-xl">
              ✨
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              Интересы
            </h3>
          </div>
          {formData.interests && formData.interests.trim() ? (
            <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
              {formData.interests}
            </p>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400 italic">
              Без описания
            </p>
          )}
          {selectedCategories.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {selectedCategories.map(cat => (
                <span
                  key={cat.value}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-lg text-xs font-semibold"
                >
                  <Tag className="w-3 h-3" />
                  {cat.label}
                </span>
              ))}
            </div>
          )}
        </motion.div>

        {/* Duration & Style */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="p-6 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-2 border-blue-200 dark:border-blue-800 rounded-xl"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center text-xl">
              ⏱️
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              Параметры
            </h3>
          </div>
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm">
              <Clock className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span className="text-slate-700 dark:text-slate-300">
                Длительность: <strong>{durationHours} часа</strong>
              </span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Users className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span className="text-slate-700 dark:text-slate-300">
                {getSocialModeLabel(formData.social_mode || 'solo')}
              </span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Zap className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span className="text-slate-700 dark:text-slate-300">
                {getIntensityLabel(formData.intensity || 'medium')}
              </span>
            </div>
          </div>
        </motion.div>

        {/* Location */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="p-6 bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border-2 border-green-200 dark:border-green-800 rounded-xl"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-green-600 rounded-xl flex items-center justify-center text-xl">
              📍
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              Точка старта
            </h3>
          </div>
          {formData.start_address ? (
            <div className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-300">
              <MapPin className="w-4 h-4 mt-0.5 text-green-600 dark:text-green-400 flex-shrink-0" />
              <p className="leading-relaxed">{formData.start_address}</p>
            </div>
          ) : formData.start_lat && formData.start_lon ? (
            <div className="text-sm text-slate-700 dark:text-slate-300">
              <p className="font-mono">
                {formData.start_lat.toFixed(4)}, {formData.start_lon.toFixed(4)}
              </p>
            </div>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400 italic">
              Не указана
            </p>
          )}
        </motion.div>

        {/* Preferences */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="p-6 bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 border-2 border-amber-200 dark:border-amber-800 rounded-xl"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-amber-600 rounded-xl flex items-center justify-center text-xl">
              🎛️
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              Настройки
            </h3>
          </div>
          <div className="space-y-2">
            {formData.coffee_preferences?.enabled ? (
              <div className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <Coffee className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                <span>
                  Кофе-брейки каждые <strong>{formData.coffee_preferences.interval_minutes} мин</strong>
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
                <Coffee className="w-4 h-4" />
                <span>Без кофе-брейков</span>
              </div>
            )}
            {formData.allow_transit ? (
              <div className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <Bus className="w-4 h-4 text-green-600 dark:text-green-400" />
                <span>С общественным транспортом</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
                <Bus className="w-4 h-4" />
                <span>Только пешком</span>
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Success Message */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.4 }}
        className="p-6 bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 border-2 border-emerald-300 dark:border-emerald-700 rounded-xl"
      >
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-emerald-600 rounded-full flex items-center justify-center flex-shrink-0">
            <Check className="w-6 h-6 text-white" />
          </div>
          <div>
            <h4 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
              Готовы создать маршрут!
            </h4>
            <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
              AI проанализирует ваши предпочтения и создаст персональный маршрут с подробными объяснениями для каждой точки. 
              Это займёт около 10-15 секунд.
            </p>
          </div>
        </div>
      </motion.div>

      {/* Features Preview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { icon: '🗺️', text: 'Реальные дороги' },
          { icon: '🤖', text: 'AI объяснения' },
          { icon: '📊', text: 'Оптимальный порядок' },
          { icon: '⏰', text: 'Точное время' },
        ].map((feature, index) => (
          <motion.div
            key={feature.text}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5 + index * 0.1 }}
            className="flex items-center gap-3 p-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
          >
            <span className="text-2xl">{feature.icon}</span>
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
              {feature.text}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  )
}