import { useState } from 'react'
import { motion } from 'framer-motion'
import { X, Copy, Check } from 'lucide-react'

interface Props {
  onClose: () => void
}

export default function ShareModal({ onClose }: Props) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => {
      setCopied(false)
    }, 2000)
  }

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-end sm:items-center justify-center z-[9999] p-0 sm:p-4"
      onClick={handleBackdropClick}
    >
      <motion.div
        initial={{ y: '100%', opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: '100%', opacity: 0 }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
        onClick={e => e.stopPropagation()}
        className="bg-white rounded-t-3xl sm:rounded-2xl p-6 pb-8 sm:pb-6 w-full sm:max-w-md shadow-2xl border-t-2 sm:border-2 border-emerald-100 relative"
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 hover:bg-slate-100 rounded-full transition-colors touch-manipulation"
          aria-label="Закрыть"
        >
          <X className="w-5 h-5 text-slate-600" />
        </button>

        <div className="mb-6">
          <h3 className="text-2xl font-bold text-slate-900 mb-2">Поделиться маршрутом</h3>
          <p className="text-sm text-slate-600">Скопируйте ссылку и отправьте друзьям</p>
        </div>

        <div className="space-y-4">
          <div className="relative">
            <input
              type="text"
              value={window.location.href}
              readOnly
              className="w-full px-4 py-3 pr-12 bg-emerald-50/50 border-2 border-emerald-100 rounded-xl font-mono text-xs sm:text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 select-all"
              onClick={e => (e.target as HTMLInputElement).select()}
            />
          </div>

          <button
            onClick={handleCopy}
            className="w-full bg-gradient-to-r from-emerald-500 to-sky-500 text-white py-4 rounded-xl font-semibold hover:shadow-lg transition-all flex items-center justify-center gap-2 touch-manipulation active:scale-95"
          >
            {copied ? (
              <>
                <Check className="w-5 h-5" />
                Скопировано!
              </>
            ) : (
              <>
                <Copy className="w-5 h-5" />
                Копировать ссылку
              </>
            )}
          </button>

          <button
            onClick={onClose}
            className="w-full py-3 text-slate-600 font-medium hover:bg-slate-50 rounded-xl transition-colors touch-manipulation"
          >
            Закрыть
          </button>
        </div>

        <div className="mt-4 pt-4 border-t border-slate-100">
          <p className="text-xs text-slate-500 text-center">
            Ссылка содержит полный маршрут и останется рабочей навсегда
          </p>
        </div>
      </motion.div>
    </motion.div>
  )
}