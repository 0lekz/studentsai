import { Construction } from 'lucide-react'
import { CONSTRUCTION_NOTICE, UNDER_CONSTRUCTION } from '@/lib/launch'
import { cn } from '@/lib/utils'

type Props = {
  variant?: 'card' | 'strip'
  className?: string
}

export function ConstructionNotice({ variant = 'card', className }: Props) {
  if (!UNDER_CONSTRUCTION) return null

  if (variant === 'strip') {
    return (
      <div
        role="status"
        className={cn(
          'flex shrink-0 items-center gap-2 border-b border-warning/30 bg-warning-soft px-4 py-2 text-sm text-warning-soft-foreground',
          className,
        )}
      >
        <Construction className="h-4 w-4 shrink-0" aria-hidden />
        <span>{CONSTRUCTION_NOTICE.short}</span>
      </div>
    )
  }

  return (
    <div
      role="status"
      className={cn(
        'flex gap-3 rounded-card border border-warning/40 bg-warning-soft p-4 text-warning-soft-foreground',
        className,
      )}
    >
      <Construction className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
      <div className="space-y-1">
        <p className="font-semibold">{CONSTRUCTION_NOTICE.title}</p>
        <p className="text-body leading-relaxed">{CONSTRUCTION_NOTICE.body}</p>
      </div>
    </div>
  )
}
