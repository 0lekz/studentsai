import { cn } from '@/lib/utils'

interface ProgressBarProps {
  value?: number
  label: string
  className?: string
}

// Omit `value` for an indeterminate bar.
export function ProgressBar({ value, label, className }: ProgressBarProps) {
  const indeterminate = value === undefined
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={indeterminate ? undefined : Math.round(value * 100)}
      className={cn('h-1.5 overflow-hidden rounded-full bg-muted', className)}
    >
      <div
        className={cn('h-full rounded-full bg-brand', indeterminate ? 'w-1/3 animate-indeterminate' : 'transition-[width] duration-300')}
        style={indeterminate ? undefined : { width: `${Math.max(0, Math.min(1, value)) * 100}%` }}
      />
    </div>
  )
}
