import { useState } from 'react'
import { motion } from 'framer-motion'
import { Link2, Copy } from 'lucide-react'

interface Props {
  title: string
  distance: number
  durationMinutes: number
  shareUrl: string
  weatherAdvice?: string
}

const formatDuration = (minutes: number) => {
  const hours = Math.floor(minutes / 60)
  const remainder = minutes % 60
  if (!hours) {
    return `${remainder} мин`
  }
  return `${hours} ч ${remainder} мин`
}

export default function RouteShareCard({ title, distance, durationMinutes, shareUrl, weatherAdvice }: Props) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch (error) {
      console.error('Не удалось скопировать ссылку', error)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="bg-white/90 backdrop-blur-lg border border-emerald-100 rounded-3xl shadow-xl p-6"
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 text-emerald-600 text-sm font-semibold">
            <Link2 className="w-4 h-4" />
            Итоги прогулки
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 mt-1">{title}</h2>
          <div className="mt-2 flex flex-wrap gap-3 text-sm text-slate-600">
            <span>⏱️ {formatDuration(durationMinutes)}</span>
            <span>•</span>
            <span>🚶 {distance.toFixed(1)} км</span>
          </div>
          {weatherAdvice && <p className="mt-3 text-sm text-slate-600">{weatherAdvice}</p>}
        </div>
        <div className="flex flex-col sm:items-end gap-2">
          <button
            onClick={handleCopy}
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-sky-500 text-white font-semibold shadow-lg hover:shadow-emerald-300/50 transition-transform hover:-translate-y-0.5"
          >
            <Copy className="w-4 h-4" />
            {copied ? 'Ссылка скопирована' : 'Скопировать ссылку'}
          </button>
          <span className="text-xs text-slate-400 break-all sm:text-right">{shareUrl}</span>
        </div>
      </div>
    </motion.div>
  )
}
