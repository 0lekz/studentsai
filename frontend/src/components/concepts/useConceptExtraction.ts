'use client'

import { useCallback, useState } from 'react'
import { api, APIError, type Concept } from '@/lib/api'

export type ExtractionState =
  | { status: 'idle' }
  | { status: 'running' }
  | { status: 'done'; concepts: Concept[] }
  | { status: 'error'; message: string }

function messageFor(error: unknown): string {
  if (error instanceof APIError && error.status === 409) return 'Wait until your files finish processing, then try again.'
  return error instanceof Error ? error.message : 'Could not extract concepts'
}

export function useConceptExtraction(courseId: string, onExtracted?: (concepts: Concept[]) => void) {
  const [state, setState] = useState<ExtractionState>({ status: 'idle' })

  const run = useCallback(async () => {
    setState({ status: 'running' })
    try {
      const concepts = await api.extractConcepts(courseId)
      setState({ status: 'done', concepts })
      onExtracted?.(concepts)
    } catch (error) {
      setState({ status: 'error', message: messageFor(error) })
    }
  }, [courseId, onExtracted])

  return { state, run }
}
