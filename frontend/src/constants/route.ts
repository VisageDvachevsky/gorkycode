export const MIN_ROUTE_HOURS = 0.5
export const MAX_ROUTE_HOURS = 8
export const DEFAULT_ROUTE_HOURS = 3

export const sanitizeRouteHours = (value: number | null | undefined): number => {
  if (value == null || Number.isNaN(value)) {
    return DEFAULT_ROUTE_HOURS
  }

  return Math.min(MAX_ROUTE_HOURS, Math.max(MIN_ROUTE_HOURS, value))
}