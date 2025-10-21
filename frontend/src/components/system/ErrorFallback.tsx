import { RefreshCcw } from 'lucide-react'
import React from 'react'

type ErrorFallbackProps = {
  onRetry?: () => void
}

const ErrorFallback: React.FC<ErrorFallbackProps> = ({ onRetry }) => {
  const handleRetry = () => {
    if (typeof onRetry === 'function') {
      onRetry()
    } else {
      window.location.reload()
    }
  }

  return (
    <div className="min-h-screen w-full bg-slate-50 flex flex-col items-center justify-center px-6 py-16 text-center text-slate-900">
      <div className="max-w-md">
        <div className="text-5xl mb-6">😔</div>
        <h1 className="text-2xl font-semibold mb-3">Что-то пошло не так</h1>
        <p className="text-base text-slate-600 mb-6">
          Мы уже получили отчёт об ошибке. Попробуйте обновить страницу или вернитесь чуть позже.
        </p>
        <button
          type="button"
          onClick={handleRetry}
          className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-white shadow-sm transition hover:bg-emerald-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
        >
          <RefreshCcw className="h-4 w-4" />
          Перезагрузить
        </button>
      </div>
    </div>
  )
}

export default ErrorFallback
