import { motion } from 'framer-motion'

interface TimelineEntry {
  id: number
  emoji: string
  label: string
  timeLabel: string
  relativeLabel: string
  active: boolean
  isBreak: boolean
}

interface Props {
  entries: TimelineEntry[]
  onHover: (id: number | null) => void
}

export default function ItineraryTimeline({ entries, onHover }: Props) {
  if (!entries.length) {
    return null
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <div className="flex items-stretch gap-4 overflow-x-auto pb-2">
        {entries.map(entry => (
          <div
            key={entry.id}
            onMouseEnter={() => onHover(entry.id)}
            onMouseLeave={() => onHover(null)}
            className={`min-w-[180px] rounded-2xl border px-4 py-3 transition-all ${
              entry.active
                ? 'border-emerald-400 bg-white shadow-lg scale-[1.02]'
                : 'border-emerald-100 bg-white/80 hover:border-emerald-200 hover:shadow-md'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-2xl">{entry.emoji}</span>
              <span className="text-xs font-semibold text-slate-500">{entry.relativeLabel}</span>
            </div>
            <div className="mt-3 text-sm font-semibold text-slate-800 line-clamp-2">{entry.label}</div>
            <div className="mt-2 text-xs text-slate-500">{entry.timeLabel}</div>
            {entry.isBreak && <div className="mt-2 text-xs font-semibold text-amber-600">Пауза на кофе</div>}
          </div>
        ))}
      </div>
    </motion.div>
  )
}
