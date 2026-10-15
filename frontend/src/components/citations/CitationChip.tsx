import { FileText } from 'lucide-react'
import type { QuestionSource } from '@/lib/api'
import { formatPages } from '@/lib/format'
import { cn } from '@/lib/utils'

interface CitationChipProps {
  source: QuestionSource
  number?: number
  onOpen: () => void
  className?: string
}

export function CitationChip({ source, number, onOpen, className }: CitationChipProps) {
  const pages = formatPages(source.page_start, source.page_end)
  return (
    <button
      type="button"
      onClick={onOpen}
      aria-label={`Open source${number ? ` ${number}` : ''}: ${source.filename}, ${pages}`}
      className={cn(
        'inline-flex h-9 max-w-full items-center gap-2 rounded-full border border-border bg-surface pl-1.5 pr-3 text-body text-foreground shadow-sm transition-colors hover:border-brand hover:bg-brand-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        className
      )}
    >
      {number ? (
        <span aria-hidden className="flex h-6 min-w-6 shrink-0 items-center justify-center rounded-full bg-brand-soft px-1.5 text-caption font-semibold text-brand-soft-foreground">
          {number}
        </span>
      ) : (
        <span aria-hidden className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-soft text-brand-soft-foreground">
          <FileText className="h-3.5 w-3.5" />
        </span>
      )}
      <span className="min-w-0 truncate font-medium">{source.filename}</span>
      <span className="shrink-0 text-muted-foreground">{pages}</span>
    </button>
  )
}
