import { motion } from 'framer-motion'
import { Sparkles, MapPin, Clock, Coffee, Brain } from 'lucide-react'

interface HeroProps {
  onStartJourney: () => void
}

export default function Hero({ onStartJourney }: HeroProps) {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-amber-50 via-emerald-50 to-sky-100">
      <div className="max-w-6xl mx-auto text-center py-8 sm:py-12">
        <motion.div
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ 
            type: 'spring', 
            stiffness: 200, 
            damping: 20,
            delay: 0.2 
          }}
          className="inline-block mb-6 sm:mb-8"
        >
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-400 via-sky-400 to-amber-300 rounded-full blur-2xl sm:blur-3xl opacity-40 animate-pulse-glow" />
            <div className="relative w-20 h-20 sm:w-28 sm:h-28 md:w-32 md:h-32 mx-auto bg-gradient-to-br from-emerald-500 to-sky-500 rounded-2xl sm:rounded-3xl shadow-2xl flex items-center justify-center transform hover:scale-110 transition-transform">
              <MapPin className="w-10 h-10 sm:w-14 sm:h-14 md:w-16 md:h-16 text-white" />
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="mb-6 sm:mb-8"
        >
          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl xl:text-8xl font-black mb-4 sm:mb-6 leading-tight px-2">
            <span className="inline-block bg-gradient-to-r from-emerald-600 via-sky-600 to-amber-500 bg-clip-text text-transparent">
              AI-Tourist
            </span>
          </h1>
          
          <p className="text-lg sm:text-xl md:text-2xl lg:text-3xl text-slate-600 max-w-3xl mx-auto leading-relaxed font-medium px-4">
            Персональные прогулки по Нижнему Новгороду
          </p>

          <p className="text-sm sm:text-base md:text-lg text-slate-500 max-w-2xl mx-auto mt-3 sm:mt-4 px-4">
            AI создаст уникальный маршрут специально для вас за 30 секунд
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 max-w-4xl mx-auto mb-8 sm:mb-12 px-2"
        >
          {[
            { icon: Brain, label: 'AI-объяснения', color: 'from-purple-500 to-pink-500' },
            { icon: MapPin, label: 'Реальные дороги', color: 'from-blue-500 to-cyan-500' },
            { icon: Coffee, label: 'Кофе-брейки', color: 'from-amber-500 to-orange-500' },
            { icon: Clock, label: 'Точное время', color: 'from-emerald-500 to-teal-500' },
          ].map((feature, index) => {
            const Icon = feature.icon
            return (
              <motion.div
                key={feature.label}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.7 + index * 0.1 }}
                className="group"
              >
                <div className="relative bg-white rounded-xl sm:rounded-2xl p-4 sm:p-6 shadow-lg border-2 border-emerald-100 hover:border-emerald-200 transition-all hover:shadow-2xl hover:-translate-y-1 touch-manipulation">
                  <div className={`w-10 h-10 sm:w-12 sm:h-12 md:w-14 md:h-14 mx-auto mb-2 sm:mb-4 bg-gradient-to-br ${feature.color} rounded-lg sm:rounded-xl flex items-center justify-center shadow-lg transform group-hover:scale-110 transition-transform`}>
                    <Icon className="w-5 h-5 sm:w-6 sm:h-6 md:w-7 md:h-7 text-white" />
                  </div>
                  <p className="text-xs sm:text-sm font-bold text-slate-900 leading-tight">
                    {feature.label}
                  </p>
                </div>
              </motion.div>
            )
          })}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1.0, type: 'spring', stiffness: 200 }}
          className="px-4"
        >
          <button
            onClick={onStartJourney}
            className="group relative px-6 sm:px-8 md:px-10 py-4 sm:py-5 text-base sm:text-lg md:text-xl font-bold text-white rounded-xl sm:rounded-2xl overflow-hidden shadow-2xl hover:shadow-emerald-400/50 transition-all hover:scale-105 active:scale-95 touch-manipulation w-full sm:w-auto"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-500 via-sky-500 to-amber-400" />
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-400 via-sky-400 to-amber-300 opacity-0 group-hover:opacity-100 transition-opacity" />
            <span className="relative flex items-center justify-center gap-2 sm:gap-3">
              <Sparkles className="w-5 h-5 sm:w-6 sm:h-6" />
              Создать маршрут
              <motion.span
                animate={{ x: [0, 5, 0] }}
                transition={{ repeat: Infinity, duration: 1.5 }}
              >
                →
              </motion.span>
            </span>
          </button>
          
          <p className="mt-4 sm:mt-6 text-xs sm:text-sm text-slate-600 flex items-center justify-center gap-2 flex-wrap px-2">
            <span>✓ Бесплатно</span>
            <span>•</span>
            <span>✓ Без регистрации</span>
            <span>•</span>
            <span>✓ За 30 секунд</span>
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
          className="mt-12 sm:mt-16 pt-8 sm:pt-12 border-t-2 border-emerald-100 px-4"
        >
          <div className="grid grid-cols-3 gap-4 sm:gap-6 md:gap-8 max-w-2xl mx-auto">
            {[
              { value: '50+', label: 'Мест в базе' },
              { value: '2GIS', label: 'Реальные данные' },
              { value: 'AI', label: 'Powered' },
            ].map((stat, index) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.3 + index * 0.1 }}
              >
                <div className="text-2xl sm:text-3xl font-black bg-gradient-to-r from-emerald-600 to-sky-600 bg-clip-text text-transparent">
                  {stat.value}
                </div>
                <div className="text-xs sm:text-sm text-slate-600 mt-1">
                  {stat.label}
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  )
}