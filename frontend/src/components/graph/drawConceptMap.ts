import { select, type Selection } from 'd3-selection'
import { zoom, zoomIdentity, type D3ZoomEvent, type ZoomBehavior } from 'd3-zoom'
import { drag, type D3DragEvent } from 'd3-drag'
import { forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY, type SimulationNodeDatum } from 'd3-force'
import 'd3-transition'
import type { ConceptEdgeKind, ConceptMapEdge, ConceptMapNode } from '@/lib/api'
import { formatMastery, masteryFillVar, masteryLevel } from '@/components/concepts/mastery'

interface LayoutNode extends ConceptMapNode, SimulationNodeDatum {
  rank: number
  label: string
  labelWidth: number
  x: number
  y: number
}

interface LayoutEdge {
  source: LayoutNode
  target: LayoutNode
  kind: ConceptEdgeKind
  weight: number
}

export interface ConceptMapDrawing {
  highlight: (conceptId: string | null) => void
  fit: (animate?: boolean) => void
  destroy: () => void
}

interface DrawOptions {
  svg: SVGSVGElement
  nodes: ConceptMapNode[]
  edges: ConceptMapEdge[]
  width: number
  height: number
  alwaysShowLabels: boolean
  bottomInset: number
  onSelect: (conceptId: string) => void
}

const NODE_RADIUS = 12
const SELECTED_RADIUS = 15
const HIT_RADIUS = 22
const LABEL_OFFSET = 16
const LABEL_CHAR_PX = 6.8
const LABEL_MAX_CHARS = 26
const LAYOUT_TICKS = 300
const FIT_PADDING = 28
const FIT_PADDING_TOP = 64
const MAX_FIT_SCALE = 1.5
const PHONE_WIDTH = 640
const DIMMED_OPACITY = 0.25

const css = (token: string) => `hsl(var(--${token}))`

let instanceCount = 0

function truncate(name: string): string {
  return name.length > LABEL_MAX_CHARS ? `${name.slice(0, LABEL_MAX_CHARS - 1).trimEnd()}…` : name
}

function layout(nodes: ConceptMapNode[], edges: ConceptMapEdge[], width: number, height: number) {
  const vertical = width < PHONE_WIDTH
  const ordered = [...nodes].sort((a, b) => a.order - b.order)
  const span = Math.max(1, ordered.length - 1)
  const flowLength = Math.max(vertical ? height : width, ordered.length * (vertical ? 56 : 84))
  const crossCenter = vertical ? width / 2 : height / 2

  const layoutNodes: LayoutNode[] = ordered.map((node, index) => {
    const along = (index / span) * flowLength
    const across = crossCenter + (index % 2 === 0 ? -1 : 1) * 36
    const label = truncate(node.name)
    return {
      ...node,
      rank: index / span,
      label,
      labelWidth: label.length * LABEL_CHAR_PX,
      x: vertical ? across : along,
      y: vertical ? along : across,
    }
  })
  const byId = new Map(layoutNodes.map((node) => [node.id, node]))
  const layoutEdges: LayoutEdge[] = edges.flatMap((edge) => {
    const source = byId.get(edge.source)
    const target = byId.get(edge.target)
    return source && target ? [{ source, target, kind: edge.kind, weight: edge.weight }] : []
  })

  const flowPosition = (node: LayoutNode) => node.rank * flowLength
  const flowForce = vertical ? forceY<LayoutNode>(flowPosition).strength(0.3) : forceX<LayoutNode>(flowPosition).strength(0.3)
  const crossForce = vertical ? forceX<LayoutNode>(crossCenter).strength(0.05) : forceY<LayoutNode>(crossCenter).strength(0.05)

  forceSimulation(layoutNodes)
    .force(
      'link',
      forceLink<LayoutNode, LayoutEdge>(layoutEdges)
        .distance((edge) => (edge.kind === 'prerequisite' ? 100 : 150))
        .strength((edge) => (edge.kind === 'prerequisite' ? 0.4 : 0.04))
    )
    .force('charge', forceManyBody<LayoutNode>().strength(-240))
    .force('flow', flowForce)
    .force('cross', crossForce)
    .force('collide', forceCollide<LayoutNode>((node) => Math.max(NODE_RADIUS + 14, node.labelWidth / 2 + 8)).iterations(2))
    .stop()
    .tick(LAYOUT_TICKS)

  return { layoutNodes, layoutEdges }
}

const CURVATURE = 0.22

// Edges between concepts that are not next to each other in course order bend away from the line,
// so they never run underneath the concepts in between.
function controlPoint(edge: LayoutEdge, rankStep: number): { cx: number; cy: number } {
  const { x: x0, y: y0 } = edge.source
  const { x: x2, y: y2 } = edge.target
  const dx = x2 - x0
  const dy = y2 - y0
  const length = Math.hypot(dx, dy) || 1
  const skips = Math.abs(edge.target.rank - edge.source.rank) > rankStep * 1.5
  const bend = skips ? CURVATURE * length : 0
  return { cx: (x0 + x2) / 2 + (dy / length) * bend, cy: (y0 + y2) / 2 - (dx / length) * bend }
}

function curveMidpoint(edge: LayoutEdge, rankStep: number): { x: number; y: number } {
  const { cx, cy } = controlPoint(edge, rankStep)
  return { x: (edge.source.x + 2 * cx + edge.target.x) / 4, y: (edge.source.y + 2 * cy + edge.target.y) / 4 }
}

function edgePath(edge: LayoutEdge, rankStep: number): string {
  const { x: x0, y: y0 } = edge.source
  const { x: x2, y: y2 } = edge.target
  const { cx, cy } = controlPoint(edge, rankStep)
  const startGap = NODE_RADIUS + 2
  const endGap = NODE_RADIUS + (edge.kind === 'prerequisite' ? 4 : 2)
  const startLength = Math.hypot(cx - x0, cy - y0) || 1
  const endLength = Math.hypot(x2 - cx, y2 - cy) || 1
  const sx = x0 + ((cx - x0) / startLength) * startGap
  const sy = y0 + ((cy - y0) / startLength) * startGap
  const ex = x2 - ((x2 - cx) / endLength) * endGap
  const ey = y2 - ((y2 - cy) / endLength) * endGap
  return `M${sx},${sy} Q${cx},${cy} ${ex},${ey}`
}

export function drawConceptMap({ svg: svgElement, nodes, edges, width, height, alwaysShowLabels, bottomInset, onSelect }: DrawOptions): ConceptMapDrawing {
  const svg = select(svgElement)
  svg.selectAll('*').remove()
  svg.attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`)

  const { layoutNodes, layoutEdges } = layout(nodes, edges, width, height)
  const markerId = `concept-arrow-${(instanceCount += 1)}`

  svg
    .append('defs')
    .append('marker')
    .attr('id', markerId)
    .attr('viewBox', '0 0 10 10')
    .attr('refX', 9)
    .attr('refY', 5)
    .attr('markerWidth', 7)
    .attr('markerHeight', 7)
    .attr('orient', 'auto-start-reverse')
    .append('path')
    .attr('d', 'M0,0 L10,5 L0,10 z')
    .style('fill', css('muted-foreground'))

  const root = svg.append('g')

  const rankStep = 1 / Math.max(1, layoutNodes.length - 1)
  const edgeLines: Selection<SVGPathElement, LayoutEdge, SVGGElement, unknown> = root
    .append('g')
    .selectAll<SVGPathElement, LayoutEdge>('path')
    .data(layoutEdges)
    .join('path')
    .style('fill', 'none')
    .attr('stroke-linecap', 'round')
    .attr('vector-effect', 'non-scaling-stroke')
    .attr('marker-end', (edge) => (edge.kind === 'prerequisite' ? `url(#${markerId})` : null))
    .attr('stroke-dasharray', (edge) => (edge.kind === 'related' ? '4 4' : null))
    .style('stroke', css('muted-foreground'))
    .style('stroke-width', (edge) => (edge.kind === 'prerequisite' ? 1.5 : 1))
    .style('stroke-opacity', (edge) => (edge.kind === 'prerequisite' ? 0.7 : 0.35))

  const placeEdges = () => edgeLines.attr('d', (edge) => edgePath(edge, rankStep))
  placeEdges()

  const nodeGroups = root
    .append('g')
    .selectAll<SVGGElement, LayoutNode>('g')
    .data(layoutNodes, (node) => node.id)
    .join('g')
    .attr('transform', (node) => `translate(${node.x},${node.y})`)
    .attr('tabindex', 0)
    .attr('role', 'button')
    .attr('data-concept-id', (node) => node.id)
    .attr('aria-label', (node) => `${node.name}, mastery ${formatMastery(node.mastery)}`)
    .style('cursor', 'pointer')
    .style('outline', 'none')

  nodeGroups.append('title').text((node) => `${node.name} · ${formatMastery(node.mastery)}`)
  nodeGroups.append('circle').attr('r', HIT_RADIUS).style('fill', 'transparent')

  const dots = nodeGroups
    .append('circle')
    .attr('class', 'concept-dot')
    .attr('r', NODE_RADIUS)
    .style('fill', (node) => masteryFillVar[masteryLevel(node.mastery)])
    .style('stroke', (node) => (masteryLevel(node.mastery) === 'none' ? css('muted-foreground') : css('background')))
    .style('stroke-width', 2)
    .style('stroke-dasharray', (node) => (masteryLevel(node.mastery) === 'none' ? '3 2' : null))

  const focusRings = nodeGroups
    .append('circle')
    .attr('r', SELECTED_RADIUS + 4)
    .style('fill', 'none')
    .style('stroke', css('ring'))
    .style('stroke-width', 2)
    .style('opacity', 0)

  const labels = nodeGroups.append('g').attr('class', 'concept-label').style('pointer-events', 'none').style('opacity', alwaysShowLabels ? 1 : 0)
  labels.append('rect').attr('rx', 4).style('fill', css('background')).style('opacity', 0.9)
  labels
    .append('text')
    .text((node) => node.label)
    .attr('y', NODE_RADIUS + LABEL_OFFSET)
    .attr('text-anchor', 'middle')
    .style('font-family', 'var(--font-sans)')
    .style('font-size', '12px')
    .style('font-weight', 500)
    .style('fill', css('foreground'))
  labels.select<SVGTextElement>('text').each(function sizeBackground() {
    const box = this.getBBox()
    select(this.previousElementSibling as SVGRectElement)
      .attr('x', box.x - 4)
      .attr('y', box.y - 1)
      .attr('width', box.width + 8)
      .attr('height', box.height + 2)
  })

  const neighbors = new Map<string, Set<string>>(layoutNodes.map((node) => [node.id, new Set([node.id])]))
  for (const edge of layoutEdges) {
    neighbors.get(edge.source.id)!.add(edge.target.id)
    neighbors.get(edge.target.id)!.add(edge.source.id)
  }

  let highlighted: string | null = null
  const applyHighlight = (hoveredId: string | null = null) => {
    const near = highlighted ? neighbors.get(highlighted) : null
    nodeGroups.style('opacity', (node) => (near && !near.has(node.id) ? DIMMED_OPACITY : 1))
    dots.attr('r', (node) => (node.id === highlighted ? SELECTED_RADIUS : NODE_RADIUS))
    labels.style('opacity', (node) => (alwaysShowLabels || near?.has(node.id) || node.id === hoveredId ? 1 : 0))
    edgeLines.style('opacity', (edge) => (highlighted && edge.source.id !== highlighted && edge.target.id !== highlighted ? DIMMED_OPACITY : 1))
  }

  nodeGroups
    .on('click', (_event: MouseEvent, node) => onSelect(node.id))
    .on('keydown', (event: KeyboardEvent, node) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        onSelect(node.id)
      }
    })
    .on('focus', (_event: FocusEvent, node) => focusRings.style('opacity', (other) => (other.id === node.id ? 1 : 0)))
    .on('blur', () => focusRings.style('opacity', 0))
    .on('mouseenter', (_event: MouseEvent, node) => applyHighlight(node.id))
    .on('mouseleave', () => applyHighlight())

  nodeGroups.call(
    drag<SVGGElement, LayoutNode>()
      .on('drag', function move(event: D3DragEvent<SVGGElement, LayoutNode, LayoutNode>, node) {
        node.x = event.x
        node.y = event.y
        select(this).attr('transform', `translate(${node.x},${node.y})`)
        placeEdges()
      })
  )

  const zoomBehavior: ZoomBehavior<SVGSVGElement, unknown> = zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.3, 3])
    .on('zoom', (event: D3ZoomEvent<SVGSVGElement, unknown>) => root.attr('transform', event.transform.toString()))
  svg.call(zoomBehavior).on('dblclick.zoom', null)

  const fit = (animate = false) => {
    if (layoutNodes.length === 0) return
    const curvePeaks = layoutEdges.map((edge) => curveMidpoint(edge, rankStep))
    const minX = Math.min(...layoutNodes.map((node) => node.x - Math.max(HIT_RADIUS, node.labelWidth / 2)), ...curvePeaks.map((point) => point.x))
    const maxX = Math.max(...layoutNodes.map((node) => node.x + Math.max(HIT_RADIUS, node.labelWidth / 2)), ...curvePeaks.map((point) => point.x))
    const minY = Math.min(...layoutNodes.map((node) => node.y - HIT_RADIUS), ...curvePeaks.map((point) => point.y))
    const maxY = Math.max(...layoutNodes.map((node) => node.y + NODE_RADIUS + LABEL_OFFSET + 6), ...curvePeaks.map((point) => point.y))
    const availableWidth = width - 2 * FIT_PADDING
    const availableHeight = height - FIT_PADDING_TOP - Math.max(FIT_PADDING, bottomInset)
    const scale = Math.max(0.3, Math.min(MAX_FIT_SCALE, availableWidth / (maxX - minX), availableHeight / (maxY - minY)))
    const transform = zoomIdentity
      .translate(width / 2, FIT_PADDING_TOP + availableHeight / 2)
      .scale(scale)
      .translate(-(minX + maxX) / 2, -(minY + maxY) / 2)
    if (animate) svg.transition().duration(300).call(zoomBehavior.transform, transform)
    else svg.call(zoomBehavior.transform, transform)
  }
  fit()

  return {
    highlight: (conceptId) => {
      highlighted = conceptId
      applyHighlight()
    },
    fit,
    destroy: () => {
      svg.on('.zoom', null)
      svg.selectAll('*').remove()
    },
  }
}
