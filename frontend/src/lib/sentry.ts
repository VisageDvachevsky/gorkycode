const CDN_URL = 'https://browser.sentry-cdn.com/7.110.0/bundle.tracing.min.js';

declare global {
  interface Window {
    Sentry?: {
      init: (options: Record<string, unknown>) => void;
      captureException: (error: unknown, context?: Record<string, unknown>) => void;
      setUser?: (user?: Record<string, unknown>) => void;
      browserTracingIntegration?: () => unknown;
    };
  }
}

let bootstrapPromise: Promise<void> | null = null;

export interface SentryOptions {
  dsn?: string;
  environment?: string;
  release?: string;
  tracesSampleRate?: number;
}

function initialise(options: SentryOptions) {
  if (!window.Sentry) {
    return;
  }

  const integrations: unknown[] = [];
  if (typeof window.Sentry.browserTracingIntegration === 'function') {
    integrations.push(window.Sentry.browserTracingIntegration());
  }

  window.Sentry.init({
    dsn: options.dsn,
    environment: options.environment ?? 'production',
    release: options.release,
    tracesSampleRate: options.tracesSampleRate ?? 0.1,
    integrations,
  });
}

export function bootstrapSentry(options: SentryOptions): Promise<void> | undefined {
  if (typeof document === 'undefined' || !options.dsn) {
    return undefined;
  }

  if (bootstrapPromise) {
    return bootstrapPromise;
  }

  bootstrapPromise = new Promise((resolve) => {
    if (window.Sentry) {
      initialise(options);
      resolve();
      return;
    }

    const existing = document.querySelector<HTMLScriptElement>('script[data-sentry-loader="true"]');
    if (existing) {
      existing.addEventListener('load', () => {
        initialise(options);
        resolve();
      });
      existing.addEventListener('error', () => {
        console.warn('Sentry SDK failed to load');
        resolve();
      });
      return;
    }

    const script = document.createElement('script');
    script.src = CDN_URL;
    script.crossOrigin = 'anonymous';
    script.async = true;
    script.dataset.sentryLoader = 'true';
    script.addEventListener('load', () => {
      initialise(options);
      resolve();
    });
    script.addEventListener('error', () => {
      console.warn('Sentry SDK failed to load');
      resolve();
    });

    document.head.appendChild(script);
  });

  return bootstrapPromise;
}

export function captureException(error: unknown, context?: Record<string, unknown>): void {
  if (window.Sentry && typeof window.Sentry.captureException === 'function') {
    window.Sentry.captureException(error, { extra: context });
    return;
  }

  console.error('Captured error (Sentry offline)', error, context);
}

export function setUser(user: Record<string, unknown> | null): void {
  if (window.Sentry && typeof window.Sentry.setUser === 'function') {
    window.Sentry.setUser(user ?? null);
  }
}
