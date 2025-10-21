import { useState } from 'react'
import { motion } from 'framer-motion'

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
      onClose()
    }, 1500)
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        onClick={event => event.stopPropagation()}
        className="bg-white dark:bg-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl"
      >
        <h3 className="text-2xl font-bold text-slate-900 dark:text-white mb-4">Поделиться маршрутом</h3>
        <p className="text-slate-600 dark:text-slate-400 mb-4">Скопируйте ссылку:</p>
        <input
          type="text"
          value={window.location.href}
          readOnly
          className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border-2 border-slate-200 dark:border-slate-700 rounded-xl font-mono text-sm mb-4"
          onClick={event => (event.target as HTMLInputElement).select()}
        />
        <button
          onClick={handleCopy}
          className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3 rounded-xl font-semibold hover:shadow-lg transition-all"
        >
          {copied ? '✓ Скопировано!' : 'Копировать ссылку'}
        </button>
      </motion.div>
    </motion.div>
  )
}
