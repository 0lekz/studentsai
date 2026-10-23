import type { DrawnGraph } from './drawGraph'
import { graphPalette } from './graphModel'

interface HighlightOptions {
  highlightIds: string[]
  colorCoded: boolean
  showLabels: boolean
  hideIsolated: boolean
  isDark: boolean
}

export function applyHighlight(drawn: DrawnGraph, { highlightIds, colorCoded, showLabels, hideIsolated, isDark }: HighlightOptions) {
  const palette = graphPalette(isDark)
  const ids = new Set(highlightIds.map(String))
  const strokeFor = (connectionType: string) => (colorCoded && connectionType === 'manual' ? palette.manualLink : palette.link)
  const anyVisible = Array.from(ids).some((id) => drawn.nodeIds.has(id))

  if (!anyVisible) {
    drawn.nodes.style('opacity', 1)
    drawn.labels.style('opacity', showLabels ? 1 : 0)
    drawn.links.attr('stroke', (link) => strokeFor(link.connection_type)).attr('stroke-opacity', 1)
    return
  }

  const connected = new Set<string>()
  for (const link of drawn.links.data()) {
    connected.add(String(link.source.id))
    connected.add(String(link.target.id))
  }
  drawn.nodes.style('opacity', (node) => {
    const id = String(node.id)
    if (hideIsolated && !connected.has(id)) return 0
    return ids.has(id) ? 1 : 0.25
  })
  drawn.labels.style('opacity', (node) => (ids.has(String(node.id)) || showLabels ? 1 : 0))
  drawn.links
    .attr('stroke-opacity', (link) => (ids.has(String(link.source.id)) || ids.has(String(link.target.id)) ? 1 : 0.3))
    .attr('stroke', (link) => strokeFor(link.connection_type))
}
