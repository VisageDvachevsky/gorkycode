import React from 'react'
import ReactDOM from 'react-dom/client'

import App from './App.tsx'
import ErrorBoundary from './components/system/ErrorBoundary'
import { bootstrapSentry } from './lib/sentry'
import './index.css'

const tracesSampleRateInput = Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE ?? '0.1')
const tracesSampleRate = Number.isFinite(tracesSampleRateInput) ? tracesSampleRateInput : 0.1

bootstrapSentry({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE,
  release: import.meta.env.VITE_APP_RELEASE,
  tracesSampleRate
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
)
