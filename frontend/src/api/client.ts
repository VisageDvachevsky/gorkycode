import axios from 'axios'
import type { RouteRequest, RouteResponse, Category } from '../types'

const getApiUrl = (): string => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  
  if (import.meta.env.DEV) {
    return 'http://localhost:8000'
  }
  
  return ''
}

const API_URL = getApiUrl()

const client = axios.create({
  baseURL: API_URL ? `${API_URL}/api/v1` : '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

client.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      message: error.message,
    })
    return Promise.reject(error)
  }
)

export const api = {
  async planRoute(request: RouteRequest): Promise<RouteResponse> {
    const { data } = await client.post<RouteResponse>('/route/plan', request)
    return data
  },

  async getSharedRoute(token: string): Promise<RouteResponse> {
    const { data } = await client.get<RouteResponse>(`/route/share/${encodeURIComponent(token)}`)
    return data
  },

  async getCategories(): Promise<Category[]> {
    const { data } = await client.get<Category[]>('/categories/list')
    return data
  }
}

export default client