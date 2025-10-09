import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../api/client'
import type { RouteRequest, RouteResponse } from '../types'

interface Props {
  onRouteGenerated: (route: RouteResponse) => void
}

const DEFAULT_CENTER = { lat: 56.3287, lon: 44.002 }

export default function RouteForm({ onRouteGenerated }: Props) {
  const [formData, setFormData] = useState<RouteRequest>({
    interests: '',
    hours: 3,
    start_lat: DEFAULT_CENTER.lat,
    start_lon: DEFAULT_CENTER.lon,
    social_mode: 'solo',
    intensity: 'medium',
  })

  const mutation = useMutation({
    mutationFn: api.planRoute,
    onSuccess: (data) => {
      onRouteGenerated(data)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutation.mutate(formData)
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-2xl font-semibold mb-6">Создать маршрут</h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Что вас интересует?
          </label>
          <textarea
            value={formData.interests}
            onChange={(e) => setFormData({ ...formData, interests: e.target.value })}
            placeholder="стрит-арт, панорамы, кофе, история..."
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows={3}
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Сколько часов у вас есть?
          </label>
          <input
            type="number"
            value={formData.hours}
            onChange={(e) => setFormData({ ...formData, hours: parseFloat(e.target.value) })}
            min="0.5"
            max="12"
            step="0.5"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Широта старта
            </label>
            <input
              type="number"
              value={formData.start_lat}
              onChange={(e) => setFormData({ ...formData, start_lat: parseFloat(e.target.value) })}
              step="0.0001"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Долгота старта
            </label>
            <input
              type="number"
              value={formData.start_lon}
              onChange={(e) => setFormData({ ...formData, start_lon: parseFloat(e.target.value) })}
              step="0.0001"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            С кем идёте?
          </label>
          <select
            value={formData.social_mode}
            onChange={(e) => setFormData({ ...formData, social_mode: e.target.value as any })}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="solo">Один/одна</option>
            <option value="friends">С друзьями</option>
            <option value="family">С семьёй</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Интенсивность прогулки
          </label>
          <select
            value={formData.intensity}
            onChange={(e) => setFormData({ ...formData, intensity: e.target.value as any })}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="relaxed">Расслабленно</option>
            <option value="medium">Средне</option>
            <option value="intense">Интенсивно</option>
          </select>
        </div>

        <div>
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={formData.coffee_preference !== undefined}
              onChange={(e) => {
                if (e.target.checked) {
                  setFormData({ ...formData, coffee_preference: 90 })
                } else {
                  const { coffee_preference, ...rest } = formData
                  setFormData(rest)
                }
              }}
              className="rounded text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm font-medium text-gray-700">
              Добавить кофе-брейки
            </span>
          </label>
          
          {formData.coffee_preference !== undefined && (
            <input
              type="number"
              value={formData.coffee_preference}
              onChange={(e) => setFormData({ ...formData, coffee_preference: parseInt(e.target.value) })}
              min="30"
              max="180"
              step="15"
              className="mt-2 w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Интервал в минутах"
            />
          )}
        </div>

        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {mutation.isPending ? 'Создаём маршрут...' : 'Построить маршрут'}
        </button>

        {mutation.isError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            Ошибка при создании маршрута. Попробуйте ещё раз.
          </div>
        )}
      </form>
    </div>
  )
}