'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { Network, RefreshCw, Sparkles } from 'lucide-react'
import { api, type DocumentSummary } from '@/lib/api'
import { pluralize } from '@/lib/format'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { ProgressBar } from '@/components/ui/progress-bar'
import { useConceptExtraction } from '@/components/concepts/useConceptExtraction'

interface ConceptExtractionCardProps {
  courseId: string
  documents: DocumentSummary[]
}

export function ConceptExtractionCard({ courseId, documents }: ConceptExtractionCardProps) {
  const [conceptCount, setConceptCount] = useState<number | null>(null)
  const { state, run } = useConceptExtraction(courseId)
  const readyCount = documents.filter((document) => document.status === 'ready').length
  const processing = documents.some((document) => document.status === 'pending')

  useEffect(() => {
    let cancelled = false
    api
      .getConcepts(courseId)
      .then((concepts) => !cancelled && setConceptCount(concepts.length))
      .catch(() => !cancelled && setConceptCount(null))
    return () => {
      cancelled = true
    }
  }, [courseId])

  const count = state.status === 'done' ? state.concepts.length : conceptCount
  const running = state.status === 'running'

  const title = running ? 'Extracting concepts' : count ? `${pluralize(count, 'concept')} mapped` : 'Turn these files into concepts'
  const description = running
    ? `Reading ${pluralize(readyCount, 'file')} and pulling out the key ideas. This can take a minute for long decks.`
    : state.status === 'done'
      ? `Found ${pluralize(state.concepts.length, 'concept')} across ${pluralize(readyCount, 'file')}. Practice now focuses on the ones you know least.`
      : count
        ? 'Added more files? Extract again to bring their concepts into the map.'
        : 'Pull the key ideas out of your files to build the concept map and focus practice on weak spots.'

  return (
    <section aria-labelledby="extraction-title" aria-busy={running} className="mb-6 rounded-card border border-border bg-surface p-5 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="flex min-w-0 flex-1 items-start gap-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-card bg-brand-soft text-brand-soft-foreground">
            <Sparkles className="h-5 w-5" aria-hidden />
          </div>
          <div className="min-w-0">
            <h2 id="extraction-title" className="text-body-lg font-semibold text-foreground">
              {title}
            </h2>
            <p className="mt-0.5 text-body text-muted-foreground">{description}</p>
          </div>
        </div>
        <div className="flex shrink-0 gap-2 pl-14 sm:justify-end sm:pl-0">
          {count && !running ? (
            <>
              <Button variant="ghost" onClick={run} disabled={readyCount === 0}>
                <RefreshCw className="h-4 w-4" />
                Extract again
              </Button>
              <Button asChild variant="outline">
                <Link href={`/courses/${courseId}/map`}>
                  <Network className="h-4 w-4" />
                  Open map
                </Link>
              </Button>
            </>
          ) : (
            <Button variant="outline" onClick={run} disabled={running || readyCount === 0} className="w-full sm:w-auto">
              <Sparkles className="h-4 w-4" />
              {running ? 'Extracting' : 'Extract concepts'}
            </Button>
          )}
        </div>
      </div>
      {running && <ProgressBar label="Extracting concepts" className="mt-4" />}
      {state.status === 'error' && (
        <Alert variant="error" className="mt-4">
          {state.message}
        </Alert>
      )}
      {readyCount === 0 && processing && !running && <p className="mt-3 text-caption text-muted-foreground">Available once your files finish processing.</p>}
    </section>
  )
}
