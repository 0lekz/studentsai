'use client'

import { useState } from 'react'
import { ArrowLeft, ArrowRight, CalendarCheck, Loader2, X } from 'lucide-react'
import type { Flashcard, FlashcardReviewResult } from '@/lib/api'
import { pluralize } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

const RATINGS = [
  { value: 1, label: 'Forgot' },
  { value: 2, label: 'Hard' },
  { value: 3, label: 'Okay' },
  { value: 4, label: 'Good' },
  { value: 5, label: 'Easy' },
] as const

interface StudySessionProps {
  cards: Flashcard[]
  initialIndex?: number
  onRate: (card: Flashcard, quality: number) => Promise<FlashcardReviewResult>
  onExit: () => void
}

export function StudySession({ cards, initialIndex = 0, onRate, onExit }: StudySessionProps) {
  const [index, setIndex] = useState(initialIndex)
  const [typedAnswer, setTypedAnswer] = useState('')
  const [revealed, setRevealed] = useState(false)
  const [rating, setRating] = useState<number | null>(null)
  const [result, setResult] = useState<FlashcardReviewResult | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const card = cards[index]
  const isFirst = index === 0
  const isLast = index === cards.length - 1

  const goTo = (next: number) => {
    setIndex(next)
    setTypedAnswer('')
    setRevealed(false)
    setRating(null)
    setResult(null)
    setError(null)
  }

  const rate = async (quality: number) => {
    setRating(quality)
    setSaving(true)
    setError(null)
    try {
      setResult(await onRate(card, quality))
    } catch (rateError) {
      setRating(null)
      setError(rateError instanceof Error ? rateError.message : 'Could not save the review')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section aria-label="Study session" className="mx-auto flex w-full max-w-prose flex-col">
      <div className="flex items-center gap-3">
        <p className="shrink-0 text-caption font-medium text-muted-foreground">
          Card {index + 1} of {cards.length}
        </p>
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted" aria-hidden>
          <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${((index + 1) / cards.length) * 100}%` }} />
        </div>
        <Button variant="ghost" size="sm" onClick={onExit} className="shrink-0 text-muted-foreground">
          <X className="h-4 w-4" />
          End
        </Button>
      </div>

      <div className="mt-6 rounded-card border border-border bg-surface p-6 shadow-sm sm:p-8">
        <p className="text-caption font-medium uppercase tracking-wide text-muted-foreground">Question</p>
        <h2 className="mt-2 text-title font-medium text-foreground sm:text-headline">{card.question}</h2>

        {!revealed ? (
          <div className="mt-6 space-y-3">
            <Textarea
              value={typedAnswer}
              onChange={(event) => setTypedAnswer(event.target.value)}
              placeholder="Type your answer first (optional)"
              aria-label="Your answer"
              className="min-h-[96px] text-body-lg"
            />
            <Button size="lg" className="w-full" onClick={() => setRevealed(true)}>
              Show answer
            </Button>
          </div>
        ) : (
          <div className="mt-6 border-t border-border pt-6">
            <p className="text-caption font-medium uppercase tracking-wide text-muted-foreground">Answer</p>
            <p className="mt-2 whitespace-pre-wrap text-body-lg text-foreground">{card.answer}</p>
            {typedAnswer.trim() && (
              <div className="mt-4 rounded-control bg-muted px-4 py-3">
                <p className="text-caption font-medium text-muted-foreground">Your answer</p>
                <p className="mt-1 whitespace-pre-wrap text-body text-foreground">{typedAnswer}</p>
              </div>
            )}

            <p className="mt-6 text-body font-medium text-foreground">How well did you know it?</p>
            <div className="mt-3 grid grid-cols-5 gap-2" role="group" aria-label="Rate your recall">
              {RATINGS.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  disabled={saving || result !== null}
                  aria-pressed={rating === value}
                  onClick={() => rate(value)}
                  className={cn(
                    'flex h-14 flex-col items-center justify-center rounded-control border text-caption font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed',
                    rating === value
                      ? 'border-transparent bg-primary text-primary-foreground'
                      : 'border-input bg-surface text-foreground hover:bg-accent disabled:opacity-50'
                  )}
                >
                  <span className="text-body-lg font-semibold">{value}</span>
                  {label}
                </button>
              ))}
            </div>

            {saving && (
              <p className="mt-4 flex items-center gap-2 text-body text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Saving review...
              </p>
            )}
            {error && (
              <Alert variant="error" className="mt-4">
                {error}
              </Alert>
            )}
            {result && (
              <Alert variant="success" className="mt-4 flex items-center gap-2">
                <CalendarCheck className="h-4 w-4 shrink-0" aria-hidden />
                Next review in {pluralize(result.interval_days, 'day')}
              </Alert>
            )}
          </div>
        )}
      </div>

      <div className="mt-4 flex items-center justify-between gap-3">
        <Button variant="ghost" onClick={() => goTo(index - 1)} disabled={isFirst}>
          <ArrowLeft className="h-4 w-4" />
          Previous
        </Button>
        {isLast ? (
          <Button variant={result ? 'default' : 'outline'} onClick={onExit}>
            Finish
          </Button>
        ) : (
          <Button variant={result ? 'default' : 'outline'} onClick={() => goTo(index + 1)}>
            Next
            <ArrowRight className="h-4 w-4" />
          </Button>
        )}
      </div>
    </section>
  )
}
