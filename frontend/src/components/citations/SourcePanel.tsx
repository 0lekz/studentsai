'use client'

import { useState } from 'react'
import { AlertCircle } from 'lucide-react'
import type { Citation } from '@/lib/api'
import { formatPages } from '@/lib/format'
import { Sheet } from '@/components/ui/sheet'
import { Spinner } from '@/components/ui/spinner'
import { highlightExcerpt } from './highlightExcerpt'
import { useSourceChunk } from './useSourceChunk'

const BULLET = /^[ \t]*[-*][ \t]+/gm

function SectionText({ text: raw, excerpt }: { text: string; excerpt: string }) {
  const text = raw.replace(BULLET, '• ')
  const parts = excerpt ? highlightExcerpt(text, excerpt) : null
  if (!parts) return <p className="whitespace-pre-line text-body-lg text-foreground">{text}</p>
  const [before, match, after] = parts
  return (
    <p className="whitespace-pre-line text-body-lg text-muted-foreground">
      {before}
      <mark className="rounded-sm bg-brand-soft px-0.5 text-foreground">{match}</mark>
      {after}
    </p>
  )
}

function SourceBody({ citation }: { citation: Citation }) {
  const state = useSourceChunk(citation.document_id, citation.chunk_id)
  const heading = state.status === 'ready' ? state.chunk.heading_path.join(' › ') : undefined

  return (
    <div className="space-y-6">
      {citation.excerpt && (
        <section aria-labelledby="source-excerpt">
          <h3 id="source-excerpt" className="text-caption font-medium uppercase tracking-wide text-muted-foreground">
            Cited passage
          </h3>
          <blockquote className="mt-2 border-l-2 border-brand pl-4 text-body-lg text-foreground">{citation.excerpt}</blockquote>
        </section>
      )}

      <section aria-labelledby="source-section">
        <h3 id="source-section" className="text-caption font-medium uppercase tracking-wide text-muted-foreground">
          {heading ? `On the page: ${heading}` : 'On the page'}
        </h3>
        <div className="mt-2 rounded-control bg-muted px-4 py-3">
          {state.status === 'loading' && <Spinner className="py-6" label="Loading the page" />}
          {state.status === 'error' && (
            <p className="flex items-center gap-2 text-body text-muted-foreground">
              <AlertCircle className="h-4 w-4 shrink-0" aria-hidden />
              {state.message}
            </p>
          )}
          {state.status === 'ready' && <SectionText text={state.chunk.text} excerpt={citation.excerpt} />}
        </div>
      </section>
    </div>
  )
}

interface SourcePanelProps {
  citation: Citation | null
  onClose: () => void
}

export function SourcePanel({ citation, onClose }: SourcePanelProps) {
  const [lastCitation, setLastCitation] = useState(citation)
  if (citation && citation !== lastCitation) setLastCitation(citation)
  const shown = citation ?? lastCitation

  return (
    <Sheet
      open={citation !== null}
      onOpenChange={(open) => !open && onClose()}
      title={<span className="block truncate">{shown?.filename}</span>}
      description={shown ? formatPages(shown.page_start, shown.page_end, 'long') : undefined}
    >
      {shown && <SourceBody citation={shown} />}
    </Sheet>
  )
}
