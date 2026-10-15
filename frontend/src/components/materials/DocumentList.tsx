'use client'

import { FileText, Loader2, MoreHorizontal, Presentation, Trash2 } from 'lucide-react'
import type { DocumentSummary } from '@/lib/api'
import { formatFileSize, formatShortDate, pluralize } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface DocumentListProps {
  documents: DocumentSummary[]
  uploadingNames: string[]
  onDelete: (document: DocumentSummary) => void
}

function documentMeta(document: DocumentSummary): string {
  const parts = [
    document.kind === 'slides' ? 'Slides' : 'PDF',
    document.page_count ? pluralize(document.page_count, document.kind === 'slides' ? 'slide' : 'page') : null,
    formatFileSize(document.size_bytes),
    formatShortDate(document.created_at),
  ]
  return parts.filter(Boolean).join(' · ')
}

function StatusBadge({ document }: { document: DocumentSummary }) {
  if (document.status === 'failed') return <Badge variant="destructive" title={document.error ?? undefined}>Failed</Badge>
  if (document.status === 'pending') return <Badge variant="warning">Processing</Badge>
  return null
}

export function DocumentList({ documents, uploadingNames, onDelete }: DocumentListProps) {
  return (
    <ul className="divide-y divide-border overflow-hidden rounded-card border border-border bg-surface">
      {uploadingNames.map((name) => (
        <li key={`uploading-${name}`} className="flex items-center gap-3 px-4 py-3">
          <Loader2 className="h-5 w-5 shrink-0 animate-spin text-muted-foreground" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="truncate text-body font-medium text-foreground">{name}</p>
            <p className="text-caption text-muted-foreground">Uploading and extracting...</p>
          </div>
        </li>
      ))}
      {documents.map((document) => {
        const Icon = document.kind === 'slides' ? Presentation : FileText
        return (
          <li key={document.id} className="flex items-center gap-3 px-4 py-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-control bg-muted text-muted-foreground">
              <Icon className="h-5 w-5" aria-hidden />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <p className="truncate text-body font-medium text-foreground">{document.filename}</p>
                <StatusBadge document={document} />
              </div>
              <p className="truncate text-caption text-muted-foreground">
                {document.status === 'failed' && document.error ? document.error : documentMeta(document)}
              </p>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon-sm" aria-label={`Options for ${document.filename}`} className="text-muted-foreground">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => onDelete(document)} className="text-destructive focus:text-destructive">
                  <Trash2 className="h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </li>
        )
      })}
    </ul>
  )
}
