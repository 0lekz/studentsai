import { cn } from '@/lib/utils'
import { MASTERY_LEVELS, masteryFillClass } from './mastery'

function EdgeSwatch({ dashed }: { dashed?: boolean }) {
  return (
    <svg aria-hidden width="22" height="10" viewBox="0 0 22 10" className="shrink-0 text-muted-foreground">
      <line x1="1" y1="5" x2={dashed ? 21 : 15} y2="5" stroke="currentColor" strokeWidth="1.5" strokeDasharray={dashed ? '4 3' : undefined} />
      {!dashed && <path d="M14,1 L21,5 L14,9 z" fill="currentColor" />}
    </svg>
  )
}

export function MasteryLegend({ className, showEdges = false }: { className?: string; showEdges?: boolean }) {
  return (
    <div className={cn('space-y-2 text-caption text-muted-foreground', className)}>
      <ul aria-label="Mastery" className="flex flex-wrap gap-x-4 gap-y-2">
        {MASTERY_LEVELS.map(({ level, label, range }) => (
          <li key={level} className="flex items-center gap-1.5">
            <span aria-hidden className={cn('h-3 w-3 shrink-0 rounded-full', masteryFillClass[level])} />
            <span>
              <span className="text-foreground">{label}</span>
              {range && <span> {range}</span>}
            </span>
          </li>
        ))}
      </ul>
      {showEdges && (
        <ul aria-label="Links" className="flex flex-wrap gap-x-4 gap-y-2">
          <li className="flex items-center gap-1.5">
            <EdgeSwatch />
            Comes before
          </li>
          <li className="flex items-center gap-1.5">
            <EdgeSwatch dashed />
            Related
          </li>
        </ul>
      )}
    </div>
  )
}
