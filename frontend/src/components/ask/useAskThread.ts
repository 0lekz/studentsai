'use client'

import { useCallback, useState } from 'react'
import { api, type AskResult } from '@/lib/api'

export type Exchange =
  | { id: string; question: string; status: 'pending' }
  | { id: string; question: string; status: 'answered'; result: AskResult }
  | { id: string; question: string; status: 'failed'; error: string }

export function useAskThread(courseId: string) {
  const [exchanges, setExchanges] = useState<Exchange[]>([])

  const settle = useCallback((id: string, update: Exchange) => {
    setExchanges((current) => current.map((exchange) => (exchange.id === id ? update : exchange)))
  }, [])

  const run = useCallback(
    async (id: string, question: string) => {
      try {
        settle(id, { id, question, status: 'answered', result: await api.askCourse(courseId, question) })
      } catch (error) {
        settle(id, { id, question, status: 'failed', error: error instanceof Error ? error.message : 'Could not get an answer' })
      }
    },
    [courseId, settle]
  )

  const ask = useCallback(
    (question: string) => {
      const id = crypto.randomUUID()
      setExchanges((current) => [...current, { id, question, status: 'pending' }])
      run(id, question)
    },
    [run]
  )

  const retry = useCallback(
    (exchange: Exchange) => {
      settle(exchange.id, { id: exchange.id, question: exchange.question, status: 'pending' })
      run(exchange.id, exchange.question)
    },
    [run, settle]
  )

  const pending = exchanges.some((exchange) => exchange.status === 'pending')
  return { exchanges, ask, retry, pending }
}
