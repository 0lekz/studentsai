'use client'

import { useEffect, useRef } from 'react'
import { CalendarClock, CircleCheck, CircleDot, CircleX, type LucideIcon } from 'lucide-react'
import type { AnswerResult, Citation, Verdict } from '@/lib/api'
import { formatRelativeDue } from '@/lib/format'
import { cn } from '@/lib/utils'
import { CitationChip } from '@/components/citations/CitationChip'

const VERDICTS: Record<Verdict, { label: string; icon: LucideIcon; tone: string }> = {
  correct: { label: 'Correct', icon: CircleCheck, tone: 'bg-success-soft text-success-soft-foreground' },
  partial: { label: 'Partly right', icon: CircleDot, tone: 'bg-warning-soft text-warning-soft-foreground' },
  incorrect: { label: 'Not quite', icon: CircleX, tone: 'bg-destructive-soft text-destructive-soft-foreground' },
}

export function FeedbackLabel({ children }: { children: React.ReactNode }) {
  return <h3 className="text-caption font-medium uppercase tracking-wide text-muted-foreground">{children}</h3>
}

export function NextReview({ dueDate }: { dueDate: string }) {
  return (
    <p className="flex items-center gap-1.5 text-body text-muted-foreground">
      <CalendarClock className="h-4 w-4 shrink-0" aria-hidden />
      Next review {formatRelativeDue(dueDate)}
    </p>
  )
}

interface AnswerFeedbackProps {
  result: AnswerResult
  showReference: boolean
  onOpenSource: (citation: Citation) => void
}

export function useRevealOnMount<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  useEffect(() => {
    ref.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [])
  return ref
}

export function AnswerFeedback({ result, showReference, onOpenSource }: AnswerFeedbackProps) {
  const ref = useRevealOnMount<HTMLElement>()
  const { source } = result
  const verdict = VERDICTS[result.verdict]
  const Icon = verdict.icon

  return (
    <section ref={ref} aria-label="Feedback" aria-live="polite" className="overflow-hidden rounded-card border border-border bg-surface shadow-sm">
      <div className={cn('flex items-center justify-between gap-3 px-5 py-3', verdict.tone)}>
        <p className="flex items-center gap-2 text-body-lg font-semibold">
          <Icon className="h-5 w-5 shrink-0" aria-hidden />
          {verdict.label}
        </p>
        <p className="text-body font-medium tabular-nums">
          {result.score}
          <span className="opacity-70"> / 100</span>
        </p>
      </div>

      <div className="space-y-5 px-5 py-5">
        <p className="text-body-lg text-foreground">{result.feedback}</p>

        {result.missing_points.length > 0 && (
          <div>
            <FeedbackLabel>What was missing</FeedbackLabel>
            <ul className="mt-2 space-y-1.5">
              {result.missing_points.map((point) => (
                <li key={point} className="flex gap-2 text-body text-foreground">
                  <span aria-hidden className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-warning" />
                  {point}
                </li>
              ))}
            </ul>
          </div>
        )}

        {showReference && (
          <div>
            <FeedbackLabel>Reference answer</FeedbackLabel>
            <p className="mt-2 whitespace-pre-line text-body-lg text-foreground">{result.reference_answer}</p>
          </div>
        )}

        <div className="flex flex-col gap-3 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-between">
          {source && <CitationChip source={source} onOpen={() => onOpenSource(source)} className="self-start" />}
          <NextReview dueDate={result.srs.due_date} />
        </div>
      </div>
    </section>
  )
}
