import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Coffee, Bus, ChevronDown, ChevronUp } from 'lucide-react'
import type { RouteRequest, CoffeePreferences } from '../../types'

interface Props {
  formData: Partial<RouteRequest>
  updateFormData: (updates: Partial<RouteRequest>) => void
}

export default function StepPreferences({ formData, updateFormData }: Props) {
  const [showCoffeeAdvanced, setShowCoffeeAdvanced] = useState(false)

  const coffeePrefs = formData.coffee_preferences || {
    enabled: false,
    interval_minutes: 90,
    outdoor_seating: false,
    wifi: false,
    search_radius_km: 0.5,
  }

  const updateCoffeePrefs = (updates: Partial<CoffeePreferences>) => {
    updateFormData({
      coffee_preferences: { ...coffeePrefs, ...updates }
    })
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
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-4xl shadow-xl">
            🎛️
          </div>
        </motion.div>
        <h2 className="text-4xl font-black text-slate-900 dark:text-white mb-3">
          Дополнительные настройки
        </h2>
        <p className="text-lg text-slate-600 dark:text-slate-400">
          Настройте кофе-брейки и транспорт
        </p>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`p-6 rounded-2xl border-2 transition-all ${
          coffeePrefs.enabled
            ? 'bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 border-amber-300 dark:border-amber-700'
            : 'bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-700'
        }`}
      >
        <label className="flex items-start gap-4 cursor-pointer group">
          <div className="relative">
            <input
              type="checkbox"
              checked={coffeePrefs.enabled}
              onChange={(e) => updateCoffeePrefs({ enabled: e.target.checked })}
              className="w-6 h-6 rounded-lg border-2 border-slate-300 dark:border-slate-600 checked:bg-amber-600 checked:border-amber-600 cursor-pointer transition-all"
            />
            {coffeePrefs.enabled && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="absolute inset-0 flex items-center justify-center text-white text-sm"
              >
                ✓
              </motion.div>
            )}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Coffee className={`w-5 h-5 ${coffeePrefs.enabled ? 'text-amber-600' : 'text-slate-600 dark:text-slate-400'}`} />
              <span className="font-bold text-slate-900 dark:text-white">
                Умные кофе-брейки
              </span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              AI автоматически добавит уютные кафе по пути используя 2GIS Places API
            </p>
          </div>
        </label>

        <AnimatePresence>
          {coffeePrefs.enabled && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="mt-6 space-y-6 overflow-hidden"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <label className="text-sm font-bold text-slate-700 dark:text-slate-300">
                    Интервал кофе-брейков
                  </label>
                  <span className="text-lg font-bold text-amber-600 dark:text-amber-400">
                    {coffeePrefs.interval_minutes} мин
                  </span>
                </div>
                <input
                  type="range"
                  min="30"
                  max="180"
                  step="15"
                  value={coffeePrefs.interval_minutes}
                  onChange={(e) => updateCoffeePrefs({ interval_minutes: parseInt(e.target.value) })}
                  className="w-full h-3 bg-amber-200 dark:bg-amber-900/30 rounded-full appearance-none cursor-pointer accent-amber-600"
                  style={{
                    background: `linear-gradient(to right, rgb(217 119 6) 0%, rgb(217 119 6) ${((coffeePrefs.interval_minutes - 30) / 150) * 100}%, rgb(254 215 170) ${((coffeePrefs.interval_minutes - 30) / 150) * 100}%, rgb(254 215 170) 100%)`
                  }}
                />
                <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mt-2">
                  <span>30 мин</span>
                  <span>3 часа</span>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setShowCoffeeAdvanced(!showCoffeeAdvanced)}
                className="flex items-center gap-2 text-sm font-semibold text-amber-700 dark:text-amber-300 hover:text-amber-800 dark:hover:text-amber-200 transition-colors"
              >
                {showCoffeeAdvanced ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
                Расширенные настройки
              </button>

              <AnimatePresence>
                {showCoffeeAdvanced && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="space-y-4 overflow-hidden"
                  >
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                          Кухня
                        </label>
                        <select
                          value={coffeePrefs.cuisine || ''}
                          onChange={(e) => updateCoffeePrefs({ cuisine: e.target.value || undefined })}
                          className="w-full px-3 py-2 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 transition-all"
                        >
                          <option value="">Любая</option>
                          <option value="italian">Итальянская</option>
                          <option value="french">Французская</option>
                          <option value="japanese">Японская</option>
                          <option value="asian">Азиатская</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                          Диета
                        </label>
                        <select
                          value={coffeePrefs.dietary || ''}
                          onChange={(e) => updateCoffeePrefs({ dietary: e.target.value || undefined })}
                          className="w-full px-3 py-2 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 transition-all"
                        >
                          <option value="">Без ограничений</option>
                          <option value="vegetarian">Вегетарианская</option>
                          <option value="vegan">Веганская</option>
                          <option value="halal">Халяль</option>
                          <option value="kosher">Кошерная</option>
                        </select>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-3">
                      <label className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-lg cursor-pointer hover:border-amber-500 transition-all">
                        <input
                          type="checkbox"
                          checked={coffeePrefs.outdoor_seating}
                          onChange={(e) => updateCoffeePrefs({ outdoor_seating: e.target.checked })}
                          className="w-4 h-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
                        />
                        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                          🪑 Терраса
                        </span>
                      </label>
                      <label className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-lg cursor-pointer hover:border-amber-500 transition-all">
                        <input
                          type="checkbox"
                          checked={coffeePrefs.wifi}
                          onChange={(e) => updateCoffeePrefs({ wifi: e.target.checked })}
                          className="w-4 h-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
                        />
                        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                          📶 Wi-Fi
                        </span>
                      </label>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className={`p-6 rounded-2xl border-2 transition-all ${
          formData.allow_transit
            ? 'bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border-green-300 dark:border-green-700'
            : 'bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-700'
        }`}
      >
        <label className="flex items-start gap-4 cursor-pointer group">
          <div className="relative">
            <input
              type="checkbox"
              checked={formData.allow_transit ?? true}
              onChange={(e) => updateFormData({ allow_transit: e.target.checked })}
              className="w-6 h-6 rounded-lg border-2 border-slate-300 dark:border-slate-600 checked:bg-green-600 checked:border-green-600 cursor-pointer transition-all"
            />
            {formData.allow_transit && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="absolute inset-0 flex items-center justify-center text-white text-sm"
              >
                ✓
              </motion.div>
            )}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Bus className={`w-5 h-5 ${formData.allow_transit ? 'text-green-600' : 'text-slate-600 dark:text-slate-400'}`} />
              <span className="font-bold text-slate-900 dark:text-white">
                Использовать общественный транспорт (BETA)
              </span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              При больших расстояниях (&gt;2 км) AI предложит автобус или трамвай
            </p>
          </div>
        </label>
      </motion.div>

      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-2 border-blue-200 dark:border-blue-800 rounded-xl p-5">
        <p className="text-sm text-blue-900 dark:text-blue-100">
          <span className="font-bold">💡 Все настройки опциональны:</span> AI создаст отличный маршрут даже с базовыми параметрами
        </p>
      </div>
    </div>
  )
}
