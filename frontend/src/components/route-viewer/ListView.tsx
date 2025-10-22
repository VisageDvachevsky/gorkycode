import type { RefObject } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown, ChevronUp, Navigation, Clock } from 'lucide-react'
import type { RouteResponse, POIInRoute } from '../../types'

interface Props {
  route: RouteResponse
  expandedPoi: number | null
  setExpandedPoi: (id: number | null) => void
  formatTime: (timestamp: string) => string
  timelineRef: RefObject<HTMLDivElement>
  onPoiHover: (id: number | null) => void
}

interface PoiCardProps {
  poi: POIInRoute
  isExpanded: boolean
  onToggle: () => void
  formatTime: (timestamp: string) => string
  isLast: boolean
  onHover: (id: number | null) => void
}

const PoiCard = ({ poi, isExpanded, onToggle, formatTime, isLast, onHover }: PoiCardProps) => (
  <div
    className={`bg-white dark:bg-slate-800 border-2 rounded-2xl overflow-hidden transition-all ${
      poi.is_coffee_break
        ? 'border-amber-300 dark:border-amber-700'
        : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
    } ${isExpanded ? 'shadow-2xl scale-[1.02]' : 'shadow-lg hover:shadow-xl'}`}
    onMouseEnter={() => onHover(poi.poi_id)}
    onMouseLeave={() => onHover(null)}
  >
    <button onClick={onToggle} className="w-full p-6 text-left">
      <div className="flex items-start gap-4">
        <div
          className={`flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-lg shadow-lg ${
            poi.is_coffee_break
              ? 'bg-gradient-to-br from-amber-500 to-orange-600'
              : 'bg-gradient-to-br from-blue-600 to-indigo-600'
          }`}
        >
          {poi.is_coffee_break ? '☕' : poi.order}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4 mb-2">
            <div>
              <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-1">{poi.name}</h3>
              <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {formatTime(poi.arrival_time)} - {formatTime(poi.leave_time)}
                </span>
                <span>•</span>
                <span>{poi.est_visit_minutes} минут</span>
                {poi.opening_hours && (
                  <>
                    <span>•</span>
                    <span
                      className={`flex items-center gap-1 ${
                        poi.is_open ? 'text-emerald-600 dark:text-emerald-300' : 'text-amber-600 dark:text-amber-300'
                      }`}
                    >
                      {poi.is_open ? 'Открыто' : 'График'}
                      <span className="font-medium text-xs">{poi.opening_hours}</span>
                    </span>
                  </>
                )}
                {poi.is_coffee_break && (
                  <>
                    <span>•</span>
                    <span className="px-2 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-full text-xs font-semibold">
                      Кофе-брейк
                    </span>
                  </>
                )}
              </div>
              {poi.availability_note && (
                <p className="mt-1 text-xs text-amber-600 dark:text-amber-300">
                  {poi.availability_note}
                </p>
              )}
            </div>
            {isExpanded ? (
              <ChevronUp className="w-5 h-5 text-slate-400 flex-shrink-0" />
            ) : (
              <ChevronDown className="w-5 h-5 text-slate-400 flex-shrink-0" />
            )}
          </div>

          <p className="text-slate-700 dark:text-slate-300 leading-relaxed">{poi.why}</p>
        </div>
      </div>
    </button>

    <AnimatePresence>
      {isExpanded && poi.tip && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="border-t-2 border-slate-100 dark:border-slate-700 px-6 pb-6"
        >
          <div className="pt-4 bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500 rounded-r-lg p-4">
            <p className="text-sm text-blue-900 dark:text-blue-100">
              <strong className="font-bold">💡 Совет:</strong> {poi.tip}
            </p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>

    {!isLast && (
      <div className="px-6 pb-4 flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
        <Navigation className="w-4 h-4" />
        <span>
          Переход к следующей точке
          {poi.distance_from_previous_km && !poi.is_coffee_break
            ? ` • ${poi.distance_from_previous_km.toFixed(1)} км`
            : ''}
        </span>
        <div className="flex-1 h-px bg-gradient-to-r from-slate-300 dark:from-slate-700 to-transparent" />
      </div>
    )}
  </div>
)

export default function ListView({ route, expandedPoi, setExpandedPoi, formatTime, timelineRef, onPoiHover }: Props) {
  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-blue-900/20 dark:via-indigo-900/20 dark:to-purple-900/20 border-2 border-blue-200 dark:border-blue-800 rounded-2xl p-6"
      >
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-3">{route.summary}</h2>
        {route.atmospheric_description && (
          <p className="text-lg text-slate-700 dark:text-slate-300 italic leading-relaxed">✨ {route.atmospheric_description}</p>
        )}
      </motion.div>

      <div ref={timelineRef} className="space-y-4">
        {route.route.map((poi, index) => (
          <motion.div
            key={poi.poi_id}
            id={`poi-${poi.poi_id}`}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            className={`relative ${expandedPoi === poi.poi_id ? 'ring-4 ring-blue-300 dark:ring-blue-700' : ''}`}
          >
            <PoiCard
              poi={poi}
              isExpanded={expandedPoi === poi.poi_id}
              onToggle={() => setExpandedPoi(expandedPoi === poi.poi_id ? null : poi.poi_id)}
              formatTime={formatTime}
              isLast={index === route.route.length - 1}
              onHover={onPoiHover}
            />
          </motion.div>
        ))}
      </div>

      {route.notes && route.notes.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-amber-50 dark:bg-amber-900/20 border-2 border-amber-200 dark:border-amber-800 rounded-2xl p-6"
        >
          <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">📝 Полезные заметки</h3>
          <ul className="space-y-2">
            {route.notes.map((note, index) => (
              <li key={index} className="flex items-start gap-3 text-sm text-slate-700 dark:text-slate-300">
                <span className="text-amber-600 dark:text-amber-400 mt-0.5">•</span>
                <span>{note}</span>
              </li>
            ))}
          </ul>
        </motion.div>
      )}
    </div>
  )
}
