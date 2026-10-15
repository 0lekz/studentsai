import { cn } from '@/lib/utils'

const LENGTHS = [5, 10, 20] as const

interface SessionLengthPickerProps {
  value: number
  onChange: (value: number) => void
}

export function SessionLengthPicker({ value, onChange }: SessionLengthPickerProps) {
  return (
    <div role="radiogroup" aria-label="Questions per session" className="inline-flex rounded-control border border-border bg-muted p-1">
      {LENGTHS.map((length) => (
        <button
          key={length}
          type="button"
          role="radio"
          aria-checked={value === length}
          onClick={() => onChange(length)}
          className={cn(
            'h-9 min-w-16 rounded-[calc(var(--radius-control)-0.25rem)] px-3 text-body font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            value === length ? 'bg-surface text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
          )}
        >
          {length}
        </button>
      ))}
    </div>
  )
}
