'use client'

import { useEffect, useRef, useState } from 'react'
import { Maximize2, RefreshCw } from 'lucide-react'
import type { ConceptMap } from '@/lib/api'
import { pluralize } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { MasteryLegend } from '@/components/concepts/MasteryLegend'
import { LABEL_NODE_LIMIT, strongCount } from './conceptMapModel'
import { drawConceptMap, type ConceptMapDrawing } from './drawConceptMap'

interface ConceptMapCanvasProps {
  map: ConceptMap
  selectedId: string | null
  refreshing: boolean
  onSelect: (conceptId: string) => void
  onRefresh: () => void
}

export function ConceptMapCanvas({ map, selectedId, refreshing, onSelect, onRefresh }: ConceptMapCanvasProps) {
  const container = useRef<HTMLDivElement>(null)
  const svg = useRef<SVGSVGElement>(null)
  const drawing = useRef<ConceptMapDrawing | null>(null)
  const legend = useRef<HTMLDivElement>(null)
  const onSelectRef = useRef(onSelect)
  const selectedRef = useRef(selectedId)
  const [size, setSize] = useState<{ width: number; height: number } | null>(null)

  useEffect(() => {
    onSelectRef.current = onSelect
  }, [onSelect])

  useEffect(() => {
    const element = container.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => {
      const width = Math.round(entry.contentRect.width)
      const height = Math.round(entry.contentRect.height)
      setSize((current) => (current?.width === width && current.height === height ? current : { width, height }))
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!svg.current || !size || size.width === 0 || size.height === 0) return
    const drawn = drawConceptMap({
      svg: svg.current,
      nodes: map.nodes,
      edges: map.edges,
      width: size.width,
      height: size.height,
      alwaysShowLabels: map.nodes.length < LABEL_NODE_LIMIT,
      bottomInset: legend.current?.offsetHeight ? legend.current.offsetHeight + 24 : 0,
      onSelect: (conceptId) => onSelectRef.current(conceptId),
    })
    drawn.highlight(selectedRef.current)
    drawing.current = drawn
    return () => {
      drawn.destroy()
      drawing.current = null
    }
  }, [map, size])

  useEffect(() => {
    selectedRef.current = selectedId
    drawing.current?.highlight(selectedId)
  }, [selectedId])

  return (
    <div ref={container} className="absolute inset-0 overflow-hidden bg-background">
      <svg ref={svg} className="absolute inset-0 block touch-none" role="group" aria-label="Concept map. Each concept's fill shows how well you know it; arrows point from a concept to the ones that build on it." />

      <div className="pointer-events-none absolute inset-x-0 top-0 flex items-center justify-between gap-3 p-3">
        <p className="pointer-events-auto rounded-full border border-border bg-surface/90 px-3 py-1 text-caption text-muted-foreground shadow-sm backdrop-blur">
          {pluralize(map.nodes.length, 'concept')} · {strongCount(map)} strong
        </p>
        <div className="pointer-events-auto flex items-center gap-1 rounded-control border border-border bg-surface/90 p-0.5 shadow-sm backdrop-blur">
          <Button variant="ghost" size="icon-sm" aria-label="Fit map to screen" onClick={() => drawing.current?.fit(true)}>
            <Maximize2 className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon-sm" aria-label="Refresh map" onClick={onRefresh} disabled={refreshing}>
            <RefreshCw className={cn('h-4 w-4', refreshing && 'animate-spin')} />
          </Button>
        </div>
      </div>

      <div ref={legend} className="pointer-events-none absolute bottom-3 left-3 hidden max-w-[calc(100%-1.5rem)] rounded-card border border-border bg-surface/90 px-3 py-2.5 shadow-sm backdrop-blur lg:block">
        <MasteryLegend showEdges />
      </div>
    </div>
  )
}
