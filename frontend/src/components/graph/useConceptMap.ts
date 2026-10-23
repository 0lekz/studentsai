'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, type DocumentSummary, type Concept, type ConceptMap } from '@/lib/api'

export interface ConceptMapData {
  map: ConceptMap
  concepts: Concept[]
  documents: DocumentSummary[]
}

export function useConceptMap(courseId: string) {
  const [data, setData] = useState<ConceptMapData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const [map, concepts, documents] = await Promise.all([api.getConceptMap(courseId), api.getConcepts(courseId), api.getDocuments(courseId)])
      setData({ map, concepts, documents })
      setError(null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load the map')
    } finally {
      setLoading(false)
    }
  }, [courseId])

  useEffect(() => {
    reload()
  }, [reload])

  return { data, loading, error, reload }
}
