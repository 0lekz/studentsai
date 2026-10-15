'use client'

import Link from 'next/link'
import { useCallback, useState } from 'react'
import { FileText, Loader2, Network, Sparkles } from 'lucide-react'
import type { Citation } from '@/lib/api'
import { pluralize } from '@/lib/format'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { Spinner } from '@/components/ui/spinner'
import { SourcePanel } from '@/components/citations/SourcePanel'
import { MasteryLegend } from '@/components/concepts/MasteryLegend'
import { useConceptExtraction } from '@/components/concepts/useConceptExtraction'
import { ConceptListItem } from './ConceptListItem'
import { ConceptMapCanvas } from './ConceptMapCanvas'
import { ConceptPanel } from './ConceptPanel'
import { StudyNextList } from './StudyNextList'
import { useConceptMap, type ConceptMapData } from './useConceptMap'

function NoConcepts({ courseId, data, onExtracted }: { courseId: string; data: ConceptMapData; onExtracted: () => void }) {
  const { state, run } = useConceptExtraction(courseId, onExtracted)
  const hasReadyFiles = data.documents.some((document) => document.status === 'ready')

  if (!hasReadyFiles) {
    return (
      <EmptyState icon={Network} title="No map yet" description="Add this course’s slides, then pull out its concepts. The map shows how they build on each other and how well you know each one.">
        <Button asChild size="lg">
          <Link href={`/courses/${courseId}/materials`}>
            <FileText className="h-4 w-4" />
            Open materials
          </Link>
        </Button>
      </EmptyState>
    )
  }

  return (
    <EmptyState
      icon={Network}
      title="Map this course"
      description={`Pull the key concepts out of ${pluralize(data.documents.length, 'file')}. The map shows how they build on each other and how well you know each one.`}
    >
      <Button size="lg" onClick={run} disabled={state.status === 'running'}>
        {state.status === 'running' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
        {state.status === 'running' ? 'Extracting concepts' : 'Extract concepts'}
      </Button>
      {state.status === 'error' && <Alert variant="error">{state.message}</Alert>}
    </EmptyState>
  )
}

export function ConceptMapView({ courseId }: { courseId: string }) {
  const { data, loading, error, reload } = useConceptMap(courseId)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [source, setSource] = useState<Citation | null>(null)
  const select = useCallback((conceptId: string) => setSelectedId(conceptId), [])

  if (!data && loading) return <Spinner className="flex-1" label="Loading map" />

  if (!data) {
    return (
      <div className="mx-auto w-full max-w-prose px-gutter py-section">
        <Alert variant="error">{error}</Alert>
        <Button variant="outline" className="mt-4" onClick={reload}>
          Try again
        </Button>
      </div>
    )
  }

  if (data.map.nodes.length === 0) {
    return (
      <div className="min-h-0 flex-1 overflow-y-auto">
        <NoConcepts courseId={courseId} data={data} onExtracted={reload} />
      </div>
    )
  }

  const selectedNode = data.map.nodes.find((node) => node.id === selectedId) ?? null
  const ordered = [...data.map.nodes].sort((a, b) => a.order - b.order)

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto lg:flex-row lg:overflow-hidden">
      <div className="relative h-[58dvh] min-h-80 shrink-0 border-b border-border lg:h-auto lg:min-h-0 lg:flex-1 lg:border-b-0">
        <ConceptMapCanvas map={data.map} selectedId={selectedId} refreshing={loading} onSelect={select} onRefresh={reload} />
      </div>

      <div className="shrink-0 border-b border-border bg-surface px-gutter py-3 lg:hidden">
        <MasteryLegend showEdges />
      </div>

      <aside aria-label="Concepts" className="shrink-0 space-y-section bg-surface px-gutter py-section lg:w-80 lg:overflow-y-auto lg:border-l lg:border-border lg:px-5 lg:py-6">
        {error && <Alert variant="error">{error}</Alert>}
        <StudyNextList courseId={courseId} map={data.map} selectedId={selectedId} onSelect={select} />
        <section aria-labelledby="all-concepts-title">
          <h2 id="all-concepts-title" className="text-body font-semibold text-foreground">
            All concepts <span className="font-normal text-muted-foreground">{data.map.nodes.length}</span>
          </h2>
          <p className="mt-0.5 text-caption text-muted-foreground">In the order the course introduces them.</p>
          <ol className="-mx-3 mt-2">
            {ordered.map((node) => (
              <li key={node.id}>
                <ConceptListItem name={node.name} mastery={node.mastery} selected={node.id === selectedId} onSelect={() => select(node.id)} />
              </li>
            ))}
          </ol>
        </section>
      </aside>

      <ConceptPanel
        courseId={courseId}
        map={data.map}
        node={selectedNode}
        concept={data.concepts.find((concept) => concept.id === selectedId)}
        documents={data.documents}
        onClose={() => setSelectedId(null)}
        onSelect={select}
        onOpenSource={setSource}
        onChanged={reload}
      />
      <SourcePanel citation={source} onClose={() => setSource(null)} />
    </div>
  )
}
