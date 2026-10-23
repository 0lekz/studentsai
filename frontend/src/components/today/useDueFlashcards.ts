'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, type Flashcard } from '@/lib/api'

const DUE_LIMIT = 50

export function useDueFlashcards() {
  const [due, setDue] = useState<Flashcard[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    try {
      setDue(await api.getDueFlashcards(DUE_LIMIT))
      setError(null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load due reviews')
    }
  }, [])

  useEffect(() => {
    reload()
  }, [reload])

  return { due, error, reload }
}
