import { cn } from '@/lib/utils'
import { formatMastery, masteryFillClass, masteryLevel } from './mastery'

interface MasteryMeterProps {
  mastery: number | null
  className?: string
}

export function MasteryMeter({ mastery, className }: MasteryMeterProps) {
  const level = masteryLevel(mastery)
  return (
    <span className={cn('flex shrink-0 items-center gap-2', className)}>
      {mastery !== null && (
        <span aria-hidden className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
          <span className={cn('block h-full rounded-full', masteryFillClass[level])} style={{ width: `${Math.max(4, mastery * 100)}%` }} />
        </span>
      )}
      <span className={cn('text-caption tabular-nums', mastery === null ? 'text-muted-foreground' : 'w-9 text-right font-medium text-foreground')}>
        {mastery === null ? 'New' : formatMastery(mastery)}
      </span>
    </span>
  )
}
