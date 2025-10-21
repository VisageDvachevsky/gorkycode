/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_SENTRY_DSN?: string
  readonly VITE_APP_RELEASE?: string
  readonly VITE_SENTRY_TRACES_SAMPLE_RATE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
