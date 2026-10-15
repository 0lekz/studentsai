'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, APIError, type GraphData } from '@/lib/api'

export function useGraphData(courseId?: string) {
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const reload = useCallback(async () => {
    try {
      setLoading(true)
      setError('')
      setGraphData(await api.getNotesGraph(courseId))
    } catch (loadError) {
      console.error('Failed to load graph data:', loadError)
      setError(
        loadError instanceof APIError
          ? `Failed to load graph (status ${loadError.status}): ${loadError.message}`
          : 'Failed to load graph data'
      )
    } finally {
      setLoading(false)
    }
  }, [courseId])

  useEffect(() => {
    reload()
  }, [reload])

  return { graphData, loading, error, reload }
}
