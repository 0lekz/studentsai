'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { Network } from 'lucide-react'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { Spinner } from '@/components/ui/spinner'
import { applyHighlight } from './applyHighlight'
import { drawGraph, type DrawnGraph, type GraphForces, type GraphSettings } from './drawGraph'
import { GraphControls } from './GraphControls'
import { GraphToolbar } from './GraphToolbar'
import { computeViewGraph, linkDistanceFor, linkWidthFor, nodeRadiusFor } from './graphModel'
import { useGraphData } from './useGraphData'
import { useIsDarkTheme } from './useIsDarkTheme'

const FORCES: GraphForces = { center: 0.65, repel: 12.4, link: 0.91 }
const DEFAULT_SETTINGS: GraphSettings = {
  linkDistance: 30,
  nodeSizeBase: 0.51,
  linkThicknessMul: 0.1,
  colorCoded: false,
  showLabels: false,
}
const NO_HIGHLIGHT: string[] = []
const SETTLE_DELAY_MS = 200

function prefersTouch(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(hover: none)').matches
}

interface NotesGraphProps {
  courseId?: string
  onNodeClick?: (nodeId: string) => void
  highlightNodeIds?: string[]
  emptyAction?: React.ReactNode
}

export function NotesGraph({ courseId, onNodeClick, highlightNodeIds = NO_HIGHLIGHT, emptyAction }: NotesGraphProps) {
  const { graphData, loading, error, reload } = useGraphData(courseId)
  const isDark = useIsDarkTheme()
  const [hideIsolated, setHideIsolated] = useState(true)
  const [settings, setSettings] = useState(() => ({ ...DEFAULT_SETTINGS, showLabels: prefersTouch() }))
  const [controlsOpen, setControlsOpen] = useState(false)
  const svgRef = useRef<SVGSVGElement>(null)
  const drawnRef = useRef<DrawnGraph | null>(null)
  const settingsRef = useRef(settings)
  const onNodeClickRef = useRef(onNodeClick)

  useEffect(() => {
    settingsRef.current = settings
  }, [settings])

  useEffect(() => {
    onNodeClickRef.current = onNodeClick
  }, [onNodeClick])

  const { viewNodes, viewLinks } = useMemo(() => computeViewGraph(graphData, hideIsolated), [graphData, hideIsolated])

  useEffect(() => {
    const svg = svgRef.current
    if (!svg) return
    const drawn = drawGraph({
      svg,
      nodes: viewNodes,
      links: viewLinks,
      forces: FORCES,
      isDark,
      getSettings: () => settingsRef.current,
      onNodeClick: (nodeId) => onNodeClickRef.current?.(nodeId),
    })
    drawnRef.current = drawn
    return () => {
      drawn?.destroy()
      drawnRef.current = null
    }
  }, [viewNodes, viewLinks, isDark, settings.showLabels])

  useEffect(() => {
    if (!drawnRef.current) return
    applyHighlight(drawnRef.current, {
      highlightIds: highlightNodeIds,
      colorCoded: settings.colorCoded,
      showLabels: settings.showLabels,
      hideIsolated,
      isDark,
    })
  }, [highlightNodeIds, settings.colorCoded, settings.showLabels, hideIsolated, isDark, viewNodes])

  useEffect(() => {
    drawnRef.current?.links.attr('stroke-width', (link) => linkWidthFor(link.similarity, settings.linkThicknessMul))
  }, [settings.linkThicknessMul])

  useEffect(() => {
    const drawn = drawnRef.current
    if (!drawn) return
    drawn.linkForce.distance(linkDistanceFor(settings.linkDistance))
    drawn.simulation.alphaTarget(0.2).restart()
    const settle = setTimeout(() => drawn.simulation.alphaTarget(0), SETTLE_DELAY_MS)
    return () => clearTimeout(settle)
  }, [settings.linkDistance])

  useEffect(() => {
    const drawn = drawnRef.current
    if (!drawn) return
    const radius = nodeRadiusFor(settings.nodeSizeBase)
    drawn.nodes.attr('r', radius)
    drawn.collisionForce.radius(radius + 6)
    drawn.simulation.alphaTarget(0.15).restart()
    const settle = setTimeout(() => drawn.simulation.alphaTarget(0), SETTLE_DELAY_MS)
    return () => clearTimeout(settle)
  }, [settings.nodeSizeBase])

  if (loading && !graphData) return <Spinner className="flex-1" label="Loading map" />

  if (error && !graphData) {
    return (
      <div className="mx-auto w-full max-w-prose px-gutter py-section">
        <Alert variant="error">{error}</Alert>
        <Button variant="outline" className="mt-4" onClick={reload}>
          Try again
        </Button>
      </div>
    )
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <EmptyState icon={Network} title="No map yet" description="Write a couple of notes in this course and the map shows how they connect.">
        {emptyAction}
      </EmptyState>
    )
  }

  const allIsolated = viewNodes.length === 0

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="shrink-0 space-y-3 border-b border-border px-gutter py-3">
        <GraphToolbar
          nodeCount={graphData.nodes.length}
          linkCount={graphData.connections.length}
          refreshing={loading}
          controlsOpen={controlsOpen}
          onToggleControls={() => setControlsOpen((open) => !open)}
          onRefresh={reload}
        />
        {controlsOpen && (
          <GraphControls
            settings={settings}
            hideIsolated={hideIsolated}
            onHideIsolatedChange={setHideIsolated}
            onSettingsChange={(patch) => setSettings((current) => ({ ...current, ...patch }))}
          />
        )}
      </div>
      <div className="relative min-h-0 flex-1 overflow-hidden">
        <svg ref={svgRef} className="absolute inset-0 block" role="img" aria-label="Map of how this course's notes connect" />
        {allIsolated && (
          <div className="absolute inset-0 flex items-center justify-center p-gutter">
            <div className="max-w-sm rounded-card border border-border bg-surface p-6 text-center shadow-sm">
              <p className="text-body text-foreground">None of these notes are linked yet.</p>
              <p className="mt-1 text-body text-muted-foreground">Link notes with [[wiki links]], or show every note on its own.</p>
              <Button variant="outline" className="mt-4" onClick={() => setHideIsolated(false)}>
                Show unlinked notes
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
