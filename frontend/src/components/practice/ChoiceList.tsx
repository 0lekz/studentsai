import { CircleCheck, CircleX } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChoiceListProps {
  choices: string[]
  selected: number | null
  correct: number | null
  disabled: boolean
  onChoose: (index: number) => void
}

const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F']

export function ChoiceList({ choices, selected, correct, disabled, onChoose }: ChoiceListProps) {
  const answered = correct !== null || (selected !== null && disabled)

  return (
    <div role="group" aria-label="Choices" className="space-y-3">
      {choices.map((choice, index) => {
        const isSelected = selected === index
        const isCorrect = correct === index
        const isWrongPick = answered && isSelected && correct !== index
        return (
          <button
            key={choice}
            type="button"
            disabled={disabled}
            aria-pressed={isSelected}
            onClick={() => onChoose(index)}
            className={cn(
              'flex min-h-14 w-full items-center gap-3 rounded-card border px-4 py-3 text-left text-body-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default',
              isCorrect
                ? 'border-success bg-success-soft text-success-soft-foreground'
                : isWrongPick
                  ? 'border-destructive bg-destructive-soft text-destructive-soft-foreground'
                  : isSelected
                    ? 'border-brand bg-brand-soft text-foreground'
                    : cn('border-border bg-surface text-foreground', !disabled && 'hover:border-brand hover:bg-brand-soft', answered && 'opacity-60')
            )}
          >
            <span
              aria-hidden
              className={cn(
                'flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-caption font-semibold',
                isCorrect || isWrongPick ? 'border-transparent' : 'border-border bg-muted text-muted-foreground'
              )}
            >
              {isCorrect ? <CircleCheck className="h-6 w-6" /> : isWrongPick ? <CircleX className="h-6 w-6" /> : LETTERS[index]}
            </span>
            <span className="min-w-0 flex-1">{choice}</span>
          </button>
        )
      })}
    </div>
  )
}
