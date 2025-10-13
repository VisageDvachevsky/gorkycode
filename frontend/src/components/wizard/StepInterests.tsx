import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, Tag } from 'lucide-react'
import type { RouteRequest, Category } from '../../types'

interface Props {
  formData: Partial<RouteRequest>
  updateFormData: (updates: Partial<RouteRequest>) => void
  categories: Category[]
  categoriesLoading: boolean
}

export default function StepInterests({ formData, updateFormData, categories, categoriesLoading }: Props) {
  const toggleCategory = (value: string) => {
    const current = formData.categories || []
    const updated = current.includes(value)
      ? current.filter(c => c !== value)
      : [...current, value]
    updateFormData({ categories: updated })
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
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-4xl shadow-xl">
            ✨
          </div>
        </motion.div>
        <h2 className="text-4xl font-black text-slate-900 dark:text-white mb-3">
          Что вас интересует?
        </h2>
        <p className="text-lg text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
          Расскажите о своих предпочтениях, и AI создаст идеальный маршрут специально для вас
        </p>
      </div>

      {/* Free-form interests */}
      <div>
        <label className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
          <Sparkles className="w-4 h-4 text-blue-600" />
          Свободное описание
        </label>
        <textarea
          value={formData.interests || ''}
          onChange={(e) => updateFormData({ interests: e.target.value })}
          placeholder="Например: уличное искусство, исторические здания, атмосферные кофейни с видом на Волгу, советская архитектура..."
          className="w-full px-6 py-4 border-2 border-slate-200 dark:border-slate-700 dark:bg-slate-900 dark:text-white rounded-2xl focus:ring-4 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none text-lg placeholder:text-slate-400"
          rows={4}
        />
        {formData.interests && formData.interests.trim() && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-3 flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 px-4 py-2 rounded-lg"
          >
            <span className="text-lg">✓</span>
            <span className="font-medium">Отлично! AI учтёт ваши интересы</span>
          </motion.div>
        )}
      </div>

      {/* Divider */}
      <div className="flex items-center gap-4">
        <div className="flex-1 h-px bg-gradient-to-r from-transparent via-slate-300 dark:via-slate-700 to-transparent" />
        <span className="text-sm font-medium text-slate-500 dark:text-slate-400">или</span>
        <div className="flex-1 h-px bg-gradient-to-r from-transparent via-slate-300 dark:via-slate-700 to-transparent" />
      </div>

      {/* Categories */}
      <div>
        <label className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-4">
          <Tag className="w-4 h-4 text-indigo-600" />
          Выберите категории мест
          {formData.categories && formData.categories.length > 0 && (
            <span className="ml-2 px-2 py-0.5 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-full text-xs font-bold">
              {formData.categories.length}
            </span>
          )}
        </label>

        {categoriesLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {[...Array(8)].map((_, i) => (
              <div
                key={i}
                className="h-16 bg-slate-200 dark:bg-slate-700 rounded-xl animate-pulse"
              />
            ))}
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3"
          >
            {categories.map((cat, index) => {
              const isSelected = formData.categories?.includes(cat.value)
              return (
                <motion.button
                  key={cat.value}
                  type="button"
                  onClick={() => toggleCategory(cat.value)}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.03 }}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className={`relative px-4 py-3 rounded-xl font-semibold text-sm transition-all ${
                    isSelected
                      ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-lg shadow-blue-500/30'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 border-2 border-slate-200 dark:border-slate-700'
                  }`}
                >
                  <span className="block truncate">{cat.label}</span>
                  <span className="text-xs opacity-70 block mt-0.5">
                    {cat.count}
                  </span>
                  <AnimatePresence>
                    {isSelected && (
                      <motion.div
                        key={`badge-${cat.value}`}
                        className="absolute -top-1 -right-1 w-6 h-6 bg-emerald-500 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-lg"
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0, opacity: 0 }}
                        transition={{ type: 'spring', stiffness: 500, damping: 25 }}
                      >
                        ✓
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.button>
              )
            })}
          </motion.div>
        )}
      </div>

      {/* Helper text */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-800 rounded-xl p-4">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <span className="font-bold">💡 Совет:</span> Чем подробнее вы опишете интересы или выберете категории, тем точнее AI подберёт места
        </p>
      </div>
    </div>
  )
}