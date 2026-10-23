'use client'

import { useCallback, useRef, useState } from 'react'
import { api, type PracticeQuestion } from '@/lib/api'
import type { AnswerOutcome } from './outcome'

export const DEFAULT_SESSION_SIZE = 10
const CONCEPT_SESSION_SIZE = 6

export interface SessionRequest {
  size?: number
  conceptId?: string
}

export type SessionState =
  | { status: 'idle'; error?: string }
  | { status: 'loading'; request: SessionRequest }
  | { status: 'empty'; request: SessionRequest }
  | { status: 'active'; questions: PracticeQuestion[]; index: number; outcomes: Record<string, AnswerOutcome> }
  | { status: 'summary'; questions: PracticeQuestion[]; outcomes: Record<string, AnswerOutcome> }

export function usePracticeSession(courseId: string) {
  const [state, setState] = useState<SessionState>({ status: 'idle' })
  const latestRequest = useRef(0)

  const start = useCallback(
    async (request: SessionRequest = {}) => {
      const requestNumber = (latestRequest.current += 1)
      const settle = (next: SessionState) => requestNumber === latestRequest.current && setState(next)
      setState({ status: 'loading', request })
      try {
        const questions = request.conceptId
          ? await api.generateQuestions(courseId, { concept_id: request.conceptId, count: request.size ?? CONCEPT_SESSION_SIZE })
          : await api.startPracticeSession(courseId, request.size ?? DEFAULT_SESSION_SIZE)
        settle(questions.length > 0 ? { status: 'active', questions, index: 0, outcomes: {} } : { status: 'empty', request })
      } catch (error) {
        settle({ status: 'idle', error: error instanceof Error ? error.message : 'Could not start the session' })
      }
    },
    [courseId]
  )

  const record = useCallback((questionId: string, outcome: AnswerOutcome) => {
    setState((current) => (current.status === 'active' ? { ...current, outcomes: { ...current.outcomes, [questionId]: outcome } } : current))
  }, [])

  const next = useCallback(() => {
    setState((current) => {
      if (current.status !== 'active') return current
      if (current.index + 1 < current.questions.length) return { ...current, index: current.index + 1 }
      return { status: 'summary', questions: current.questions, outcomes: current.outcomes }
    })
  }, [])

  const end = useCallback(() => {
    setState((current) => {
      if (current.status === 'active' && Object.keys(current.outcomes).length > 0) {
        return { status: 'summary', questions: current.questions, outcomes: current.outcomes }
      }
      return { status: 'idle' }
    })
  }, [])

  const reset = useCallback(() => {
    latestRequest.current += 1
    setState({ status: 'idle' })
  }, [])

  return { state, start, record, next, end, reset }
}
