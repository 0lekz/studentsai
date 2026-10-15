import { Flag, RotateCcw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { FeedbackLabel, NextReview } from './AnswerFeedback'
import type { SessionSummary as Summary } from './outcome'

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-card border border-border bg-surface px-3 py-4">
      <dt className="text-caption text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-headline font-semibold tabular-nums text-foreground">{value}</dd>
    </div>
  )
}

interface SessionSummaryProps {
  summary: Summary
  onPracticeMore: () => void
  onDone: () => void
}

export function SessionSummary({ summary, onPracticeMore, onDone }: SessionSummaryProps) {
  return (
    <>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <section aria-labelledby="summary-title" className="mx-auto w-full max-w-prose px-gutter py-10 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-card bg-brand-soft text-brand-soft-foreground">
            <Flag className="h-6 w-6" aria-hidden />
          </div>
          <h2 id="summary-title" className="mt-4 text-headline font-semibold text-foreground">
            {summary.answered === summary.total ? 'Session complete' : 'Session ended'}
          </h2>
          <p className="mt-1 text-body-lg text-muted-foreground">
            {summary.correct} of {summary.answered} correct
          </p>

          <dl className="mt-8 grid grid-cols-3 gap-3">
            <Stat label="Answered" value={summary.answered} />
            <Stat label="Correct" value={summary.correct} />
            <Stat label="Concepts" value={summary.conceptsTouched.length} />
          </dl>

          {summary.conceptsTouched.length > 0 && (
            <div className="mt-8 text-left">
              <FeedbackLabel>Concepts touched</FeedbackLabel>
              <ul className="mt-2 flex flex-wrap gap-2">
                {summary.conceptsTouched.map((name) => (
                  <li key={name}>
                    <Badge variant="brand">{name}</Badge>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {summary.nextDue && (
            <div className="mt-8 flex justify-center">
              <NextReview dueDate={summary.nextDue} />
            </div>
          )}
        </section>
      </div>
      <footer className="shrink-0 border-t border-border bg-surface px-gutter pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3">
        <div className="mx-auto flex w-full max-w-prose flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button variant="outline" size="lg" onClick={onPracticeMore}>
            <RotateCcw className="h-4 w-4" />
            Practice more
          </Button>
          <Button size="lg" autoFocus onClick={onDone}>
            Back to Today
          </Button>
        </div>
      </footer>
    </>
  )
}
