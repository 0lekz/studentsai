import type { AnswerResult, PracticeQuestion, SrsState } from '@/lib/api'

export type AnswerOutcome =
  | { mode: 'graded'; result: AnswerResult }
  | { mode: 'self'; quality: number; srs: SrsState }

export interface SessionSummary {
  total: number
  answered: number
  correct: number
  conceptsTouched: string[]
  nextDue: string | null
}

const SELF_GRADE_CORRECT = 4

export function isCorrect(outcome: AnswerOutcome): boolean {
  return outcome.mode === 'graded' ? outcome.result.verdict === 'correct' : outcome.quality >= SELF_GRADE_CORRECT
}

function dueDateOf(outcome: AnswerOutcome): string {
  return outcome.mode === 'graded' ? outcome.result.srs.due_date : outcome.srs.due_date
}

export function summarize(questions: PracticeQuestion[], outcomes: Record<string, AnswerOutcome>): SessionSummary {
  const answered = questions.filter((question) => outcomes[question.id])
  const concepts = new Set(answered.flatMap((question) => (question.concept ? [question.concept.name] : [])))
  const dueDates = answered.map((question) => dueDateOf(outcomes[question.id])).sort()
  return {
    total: questions.length,
    answered: answered.length,
    correct: answered.filter((question) => isCorrect(outcomes[question.id])).length,
    conceptsTouched: Array.from(concepts),
    nextDue: dueDates[0] ?? null,
  }
}
