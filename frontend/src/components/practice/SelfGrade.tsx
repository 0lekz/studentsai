'use client'

import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { FeedbackLabel, useRevealOnMount } from './AnswerFeedback'

export const SELF_GRADES = [
  { quality: 1, label: 'Forgot' },
  { quality: 2, label: 'Hard' },
  { quality: 3, label: 'Okay' },
  { quality: 4, label: 'Good' },
  { quality: 5, label: 'Easy' },
] as const

interface SelfGradeProps {
  reference: string | null
  chosen: number | null
  saving: boolean
  onGrade: (quality: number) => void
}

export function SelfGrade({ reference, chosen, saving, onGrade }: SelfGradeProps) {
  const ref = useRevealOnMount<HTMLElement>()
  return (
    <section ref={ref} aria-label="Reference answer" className="space-y-5 rounded-card border border-border bg-surface p-5 shadow-sm">
      <div>
        <FeedbackLabel>Reference answer</FeedbackLabel>
        <p className="mt-2 whitespace-pre-line text-body-lg text-foreground">
          {reference ?? 'The reference answer is not available for this question. Grade yourself on how well you recalled it.'}
        </p>
      </div>
      <div>
        <p className="text-body font-medium text-foreground">How well did you know it?</p>
        <div role="group" aria-label="Grade your recall" className="mt-3 grid grid-cols-5 gap-2">
          {SELF_GRADES.map(({ quality, label }) => (
            <button
              key={quality}
              type="button"
              disabled={saving || chosen !== null}
              aria-pressed={chosen === quality}
              onClick={() => onGrade(quality)}
              className={cn(
                'flex h-16 flex-col items-center justify-center rounded-control border text-caption font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default',
                chosen === quality
                  ? 'border-transparent bg-primary text-primary-foreground'
                  : 'border-input bg-surface text-foreground hover:bg-accent disabled:opacity-50'
              )}
            >
              <span className="text-body-lg font-semibold">{quality}</span>
              {label}
            </button>
          ))}
        </div>
        {saving && (
          <p className="mt-3 flex items-center gap-2 text-body text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            Saving
          </p>
        )}
      </div>
    </section>
  )
}
