'use client'

import { useEffect, useState } from 'react'
import { api, type DocumentSummary, type Concept } from '@/lib/api'

export interface CourseReadiness {
  documents: DocumentSummary[] | null
  concepts: Concept[] | null
  error: string | null
}

export function useCourseReadiness(courseId: string): CourseReadiness {
  const [state, setState] = useState<CourseReadiness>({ documents: null, concepts: null, error: null })

  useEffect(() => {
    let cancelled = false
    api
      .getDocuments(courseId)
      .then((documents) => !cancelled && setState((current) => ({ ...current, documents })))
      .catch((error) => !cancelled && setState((current) => ({ ...current, error: error instanceof Error ? error.message : 'Could not load the course' })))
    api
      .getConcepts(courseId)
      .then((concepts) => !cancelled && setState((current) => ({ ...current, concepts })))
      .catch(() => !cancelled && setState((current) => ({ ...current, concepts: [] })))
    return () => {
      cancelled = true
    }
  }, [courseId])

  return state
}
