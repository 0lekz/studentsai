'use client'

import { useEffect, useState } from 'react'
import { ArrowRight, Eye, FileText, Loader2 } from 'lucide-react'
import { api, type AnswerBody, type AnswerResult, type Citation, type PracticeQuestion, type QuestionKind, type SrsState } from '@/lib/api'
import { formatPages } from '@/lib/format'
import { Alert } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { AnswerFeedback, FeedbackLabel, NextReview } from './AnswerFeedback'
import { ChoiceList } from './ChoiceList'
import type { AnswerOutcome } from './outcome'
import { SelfGrade } from './SelfGrade'

const KIND_LABELS: Record<QuestionKind, string> = {
  recall: 'Recall',
  short_answer: 'Short answer',
  mcq: 'Multiple choice',
}

type Phase =
  | { name: 'answering' }
  | { name: 'submitting' }
  | { name: 'graded'; result: AnswerResult }
  | { name: 'revealing' }
  | { name: 'self'; reference: string | null; quality: number | null; saving: boolean; srs: SrsState | null }

function correctChoiceIndex(question: PracticeQuestion, result: AnswerResult, chosen: number | null): number | null {
  if (result.verdict === 'correct') return chosen
  const reference = result.reference_answer.trim().toLowerCase()
  const index = question.choices?.findIndex((choice) => choice.trim().toLowerCase() === reference) ?? -1
  return index >= 0 ? index : null
}

interface QuestionStepProps {
  courseId: string
  question: PracticeQuestion
  isLast: boolean
  onOutcome: (outcome: AnswerOutcome) => void
  onNext: () => void
  onOpenSource: (citation: Citation) => void
}

export function QuestionStep({ courseId, question, isLast, onOutcome, onNext, onOpenSource }: QuestionStepProps) {
  const [typed, setTyped] = useState('')
  const [choice, setChoice] = useState<number | null>(null)
  const [phase, setPhase] = useState<Phase>({ name: 'answering' })
  const [error, setError] = useState<string | null>(null)

  const isChoice = question.kind === 'mcq' && (question.choices?.length ?? 0) > 0
  const busy = phase.name === 'submitting' || phase.name === 'revealing'
  const done = phase.name === 'graded' || (phase.name === 'self' && phase.srs !== null)
  const canType = phase.name === 'answering' || phase.name === 'submitting'

  const submit = async (body: AnswerBody) => {
    setPhase({ name: 'submitting' })
    setError(null)
    try {
      const result = await api.answerQuestion(question.id, body)
      setPhase({ name: 'graded', result })
      onOutcome({ mode: 'graded', result })
    } catch (submitError) {
      setPhase({ name: 'answering' })
      setChoice(null)
      setError(submitError instanceof Error ? submitError.message : 'Could not check your answer')
    }
  }

  const choose = (index: number) => {
    if (phase.name !== 'answering') return
    setChoice(index)
    submit({ choice_index: index })
  }

  const reveal = async () => {
    setPhase({ name: 'revealing' })
    setError(null)
    try {
      const reference = await api.getQuestionReference(courseId, question.id)
      setPhase({ name: 'self', reference, quality: null, saving: false, srs: null })
    } catch (revealError) {
      setPhase({ name: 'answering' })
      setError(revealError instanceof Error ? revealError.message : 'Could not load the answer')
    }
  }

  const selfGrade = async (quality: number) => {
    if (phase.name !== 'self') return
    const revealed = phase
    setPhase({ ...revealed, quality, saving: true })
    setError(null)
    try {
      const srs = await api.selfGradeQuestion(question.id, quality)
      setPhase({ ...revealed, quality, saving: false, srs })
      onOutcome({ mode: 'self', quality, srs })
    } catch (gradeError) {
      setPhase({ ...revealed, quality: null, saving: false })
      setError(gradeError instanceof Error ? gradeError.message : 'Could not save your grade')
    }
  }

  useEffect(() => {
    if (!isChoice || phase.name !== 'answering') return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLElement && event.target.closest('input, textarea, [contenteditable]')) return
      const index = Number(event.key) - 1
      if (Number.isInteger(index) && index >= 0 && index < (question.choices?.length ?? 0)) {
        event.preventDefault()
        choose(index)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  })

  const submitTyped = () => {
    if (typed.trim() && phase.name === 'answering') submit({ answer: typed.trim() })
  }

  return (
    <>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <article data-question-kind={question.kind} className="mx-auto w-full max-w-prose px-gutter py-6 sm:py-10">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{KIND_LABELS[question.kind]}</Badge>
            {question.concept && <Badge variant="brand">{question.concept.name}</Badge>}
          </div>
          <h2 className="mt-3 text-title font-semibold text-foreground sm:text-headline">{question.prompt}</h2>
          {question.source && (
            <p className="mt-2 flex items-center gap-1.5 text-caption text-muted-foreground">
              <FileText className="h-3.5 w-3.5 shrink-0" aria-hidden />
              <span className="truncate">
                From {question.source.filename}, {formatPages(question.source.page_start, question.source.page_end)}
              </span>
            </p>
          )}

          <div className="mt-6 space-y-5">
            {isChoice ? (
              <ChoiceList
                choices={question.choices ?? []}
                selected={choice}
                correct={phase.name === 'graded' ? correctChoiceIndex(question, phase.result, choice) : null}
                disabled={phase.name !== 'answering'}
                onChoose={choose}
              />
            ) : canType ? (
              <Textarea
                value={typed}
                onChange={(event) => setTyped(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
                    event.preventDefault()
                    submitTyped()
                  }
                }}
                placeholder={question.kind === 'recall' ? 'Explain it in your own words' : 'Type your answer'}
                aria-label="Your answer"
                rows={question.kind === 'recall' ? 5 : 2}
                disabled={phase.name === 'submitting'}
                autoFocus
                className="resize-none text-body-lg"
              />
            ) : (
              typed.trim() && (
                <div className="rounded-control bg-muted px-4 py-3">
                  <FeedbackLabel>Your answer</FeedbackLabel>
                  <p className="mt-1 whitespace-pre-line text-body-lg text-foreground">{typed}</p>
                </div>
              )
            )}

            {error && <Alert variant="error">{error}</Alert>}
            {phase.name === 'graded' && <AnswerFeedback result={phase.result} showReference={!isChoice} onOpenSource={onOpenSource} />}
            {phase.name === 'self' && <SelfGrade reference={phase.reference} chosen={phase.quality} saving={phase.saving} onGrade={selfGrade} />}
            {phase.name === 'self' && phase.srs && <NextReview dueDate={phase.srs.due_date} />}
          </div>
        </article>
      </div>

      <footer className="shrink-0 border-t border-border bg-surface px-gutter pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3">
        <div className="mx-auto flex w-full max-w-prose items-center justify-end gap-3">
          {done ? (
            <Button size="lg" autoFocus onClick={onNext} className="w-full sm:w-auto">
              {isLast ? 'See summary' : 'Next question'}
              <ArrowRight className="h-4 w-4" />
            </Button>
          ) : isChoice ? (
            <p className="flex h-11 w-full items-center justify-center text-body text-muted-foreground sm:justify-end">
              {phase.name === 'submitting' ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
                  Checking
                </>
              ) : (
                'Tap the answer you think is right'
              )}
            </p>
          ) : phase.name === 'self' ? (
            <p className="flex h-11 w-full items-center justify-center text-body text-muted-foreground sm:justify-end">Grade yourself to continue</p>
          ) : (
            <>
              {question.kind === 'recall' && (
                <Button variant="ghost" size="lg" onClick={reveal} disabled={busy} className="shrink-0 px-4">
                  {phase.name === 'revealing' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eye className="h-4 w-4" />}
                  Show answer
                </Button>
              )}
              <Button size="lg" onClick={submitTyped} disabled={!typed.trim() || busy} className="flex-1 sm:flex-none">
                {phase.name === 'submitting' && <Loader2 className="h-4 w-4 animate-spin" />}
                {phase.name === 'submitting' ? 'Checking' : 'Check answer'}
              </Button>
            </>
          )}
        </div>
      </footer>
    </>
  )
}
