import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Loader2, Sparkles } from 'lucide-react'
import { api } from '../api/client'
import type { RouteRequest, RouteResponse } from '../types'
import StepInterests from './wizard/StepInterests'
import StepDuration from './wizard/StepDuration'
import StepLocation from './wizard/StepLocation'
import StepPreferences from './wizard/StepPreferences'
import StepReview from './wizard/StepReview'
import {
  DEFAULT_ROUTE_HOURS,
  MAX_ROUTE_HOURS,
  MIN_ROUTE_HOURS,
  sanitizeRouteHours,
} from '../constants/route'

interface Props {
  onRouteGenerated: (route: RouteResponse) => void
  onBack: () => void
}

const STEPS = [
  { id: 'interests', title: 'Интересы', icon: '✨' },
  { id: 'duration', title: 'Время', icon: '⏱️' },
  { id: 'location', title: 'Старт', icon: '📍' },
  { id: 'preferences', title: 'Настройки', icon: '🎛️' },
  { id: 'review', title: 'Готово', icon: '🎯' },
] as const

type StepId = typeof STEPS[number]['id']

export default function RouteWizard({ onRouteGenerated, onBack }: Props) {
  const [currentStep, setCurrentStep] = useState<number>(0)
  const [formData, setFormData] = useState<Partial<RouteRequest>>({
    social_mode: 'solo',
    intensity: 'medium',
    allow_transit: true,
    hours: DEFAULT_ROUTE_HOURS,
    client_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  })

  const { data: categories = [], isLoading: categoriesLoading } = useQuery({
    queryKey: ['categories'],
    queryFn: api.getCategories,
  })

  const mutation = useMutation({
    mutationFn: api.planRoute,
    onSuccess: (data) => {
      onRouteGenerated(data)
    },
  })

  const updateFormData = (updates: Partial<RouteRequest>) => {
    setFormData(prev => {
      const next = { ...prev, ...updates }

      if ('hours' in updates) {
        next.hours = sanitizeRouteHours(updates.hours)
      }

      return next
    })
  }

  const canProceed = () => {
    switch (STEPS[currentStep].id) {
      case 'interests':
        return (formData.interests?.trim() || formData.categories?.length)
      case 'duration':
        return (
          typeof formData.hours === 'number' &&
          formData.hours >= MIN_ROUTE_HOURS &&
          formData.hours <= MAX_ROUTE_HOURS
        )
      case 'location':
        return formData.start_address || (formData.start_lat && formData.start_lon)
      case 'preferences':
        return true
      case 'review':
        return true
      default:
        return false
    }
  }

  const handleNext = () => {
    if (currentStep < STEPS.length - 1 && canProceed()) {
      setCurrentStep(prev => prev + 1)
    }
  }

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1)
    }
  }

  const handleSubmit = () => {
    if (!canProceed()) return
    const safeHours = sanitizeRouteHours(formData.hours)
    mutation.mutate({ ...formData, hours: safeHours } as RouteRequest)
  }

  const progress = ((currentStep + 1) / STEPS.length) * 100

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-lg border-b border-slate-200 dark:border-slate-700 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={onBack}
              className="flex items-center gap-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors group"
            >
              <ChevronLeft className="w-5 h-5 group-hover:-translate-x-1 transition-transform" />
              <span className="font-medium">Назад</span>
            </button>

            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              <span className="font-bold text-slate-900 dark:text-white">AI-Tourist</span>
            </div>

            <div className="text-sm font-medium text-slate-600 dark:text-slate-400">
              Шаг {currentStep + 1} / {STEPS.length}
            </div>
          </div>

          <div className="mt-4">
            <div className="flex justify-between mb-2">
              {STEPS.map((step, index) => (
                <div
                  key={step.id}
                  className={`flex flex-col items-center gap-1 transition-opacity ${
                    index === currentStep
                      ? 'opacity-100 scale-110'
                      : index < currentStep
                      ? 'opacity-70'
                      : 'opacity-30'
                  }`}
                >
                  <motion.div
                    className={`w-10 h-10 rounded-full flex items-center justify-center text-lg ${
                      index <= currentStep
                        ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-lg'
                        : 'bg-slate-200 dark:bg-slate-700'
                    }`}
                    animate={{ scale: index === currentStep ? 1.1 : 1 }}
                    transition={{ type: 'spring', stiffness: 300 }}
                  >
                    {step.icon}
                  </motion.div>
                  <span className="text-xs font-medium hidden sm:block">
                    {step.title}
                  </span>
                </div>
              ))}
            </div>
            <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-blue-500 via-indigo-600 to-purple-600"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5, ease: 'easeInOut' }}
              />
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 py-8 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
              className="bg-white dark:bg-slate-800 rounded-3xl shadow-2xl p-6 sm:p-8 md:p-12"
            >
              {STEPS[currentStep].id === 'interests' && (
                <StepInterests
                  formData={formData}
                  updateFormData={updateFormData}
                  categories={categories}
                  categoriesLoading={categoriesLoading}
                />
              )}
              {STEPS[currentStep].id === 'duration' && (
                <StepDuration
                  formData={formData}
                  updateFormData={updateFormData}
                />
              )}
              {STEPS[currentStep].id === 'location' && (
                <StepLocation
                  formData={formData}
                  updateFormData={updateFormData}
                />
              )}
              {STEPS[currentStep].id === 'preferences' && (
                <StepPreferences
                  formData={formData}
                  updateFormData={updateFormData}
                />
              )}
              {STEPS[currentStep].id === 'review' && (
                <StepReview
                  formData={formData}
                  categories={categories}
                />
              )}
            </motion.div>
          </AnimatePresence>

          <div className="mt-8 flex justify-between items-center gap-4">
            <button
              onClick={handlePrev}
              disabled={currentStep === 0}
              className="flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 disabled:opacity-30 disabled:cursor-not-allowed transition-all hover:shadow-lg disabled:hover:shadow-none"
            >
              <ChevronLeft className="w-5 h-5" />
              Назад
            </button>

            <div className="flex-1" />

            {currentStep < STEPS.length - 1 ? (
              <button
                onClick={handleNext}
                disabled={!canProceed()}
                className="flex items-center gap-2 px-8 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:shadow-xl disabled:hover:shadow-none hover:scale-105"
              >
                Далее
                <ChevronRight className="w-5 h-5" />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={!canProceed() || mutation.isPending}
                className="flex items-center gap-3 px-8 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:shadow-xl disabled:hover:shadow-none hover:scale-105"
              >
                {mutation.isPending ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Создаём маршрут...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    Создать маршрут
                  </>
                )}
              </button>
            )}
          </div>

          {mutation.isError && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-xl"
            >
              <p className="text-red-800 dark:text-red-200 font-semibold">
                Ошибка при создании маршрута
              </p>
              <p className="text-red-600 dark:text-red-400 text-sm mt-1">
                {(mutation.error as any)?.response?.data?.detail || 
                  'Проверьте данные и попробуйте снова'}
              </p>
            </motion.div>
          )}
        </div>
      </main>
    </div>
  )
}
