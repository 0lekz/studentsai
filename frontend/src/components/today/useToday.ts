'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, type TodaySummary } from '@/lib/api'

export function useToday() {
  const [today, setToday] = useState<TodaySummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    try {
      setToday(await api.getToday())
      setError(null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load today')
    }
  }, [])

  useEffect(() => {
    reload()
  }, [reload])

  return { today, error, reload }
}
