import axios from 'axios'
import type { RouteRequest, RouteResponse } from '../types'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const api = {
  async planRoute(request: RouteRequest): Promise<RouteResponse> {
    const { data } = await client.post<RouteResponse>('/route/plan', request)
    return data
  },
  async getCategories(): Promise<Category[]> {
  const { data } = await client.get<Category[]>('/categories/list')
  return data
}
}

export default client