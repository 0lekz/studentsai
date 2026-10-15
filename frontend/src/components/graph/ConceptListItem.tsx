import { ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { MasteryMeter } from '@/components/concepts/MasteryMeter'

interface ConceptListItemProps {
  name: string
  mastery: number | null
  detail?: string
  selected?: boolean
  onSelect: () => void
}

export function ConceptListItem({ name, mastery, detail, selected, onSelect }: ConceptListItemProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-current={selected ? 'true' : undefined}
      className={cn(
        'flex w-full items-center gap-3 rounded-control px-3 py-2.5 text-left transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        selected && 'bg-brand-soft hover:bg-brand-soft'
      )}
    >
      <span className="min-w-0 flex-1">
        <span className="block truncate text-body font-medium text-foreground">{name}</span>
        {detail && <span className="block truncate text-caption text-muted-foreground">{detail}</span>}
      </span>
      <MasteryMeter mastery={mastery} />
      <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
    </button>
  )
}
