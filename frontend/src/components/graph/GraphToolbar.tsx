import { RefreshCw, SlidersHorizontal } from 'lucide-react'
import { pluralize } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

interface GraphToolbarProps {
  nodeCount: number
  linkCount: number
  refreshing: boolean
  controlsOpen: boolean
  onToggleControls: () => void
  onRefresh: () => void
}

export function GraphToolbar({ nodeCount, linkCount, refreshing, controlsOpen, onToggleControls, onRefresh }: GraphToolbarProps) {
  return (
    <div className="flex items-center justify-between gap-3">
      <p className="min-w-0 truncate text-body text-muted-foreground">
        {pluralize(nodeCount, 'note')} · {pluralize(linkCount, 'link')}
        <span className="hidden lg:inline"> · Click a note to open it, hover to see its neighbors</span>
      </p>
      <div className="flex shrink-0 items-center gap-1">
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Graph settings"
          aria-pressed={controlsOpen}
          onClick={onToggleControls}
          className={cn(controlsOpen && 'bg-accent')}
        >
          <SlidersHorizontal className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon-sm" aria-label="Refresh map" onClick={onRefresh} disabled={refreshing}>
          <RefreshCw className={cn('h-4 w-4', refreshing && 'animate-spin')} />
        </Button>
      </div>
    </div>
  )
}
