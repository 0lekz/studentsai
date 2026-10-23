import { select, type Selection } from 'd3-selection'
import { zoom, type D3ZoomEvent } from 'd3-zoom'
import { drag, type D3DragEvent } from 'd3-drag'
import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, type ForceCollide, type ForceLink, type Simulation } from 'd3-force'
import type { GraphConnection, GraphNode } from '@/lib/api'
import {
  graphPalette,
  linkDistanceFor,
  linkWidthFor,
  nodeRadiusFor,
  type GraphSimulationLink,
  type GraphSimulationNode,
} from './graphModel'

export interface GraphSettings {
  linkDistance: number
  nodeSizeBase: number
  linkThicknessMul: number
  colorCoded: boolean
  showLabels: boolean
}

export interface GraphForces {
  center: number
  repel: number
  link: number
}

interface DrawGraphOptions {
  svg: SVGSVGElement
  nodes: GraphNode[]
  links: GraphConnection[]
  forces: GraphForces
  isDark: boolean
  getSettings: () => GraphSettings
  onNodeClick: (nodeId: string) => void
}

export interface DrawnGraph {
  nodes: Selection<SVGCircleElement, GraphSimulationNode, SVGGElement, unknown>
  links: Selection<SVGLineElement, GraphSimulationLink, SVGGElement, unknown>
  labels: Selection<SVGTextElement, GraphSimulationNode, SVGGElement, unknown>
  simulation: Simulation<GraphSimulationNode, GraphSimulationLink>
  linkForce: ForceLink<GraphSimulationNode, GraphSimulationLink>
  collisionForce: ForceCollide<GraphSimulationNode>
  nodeIds: Set<string>
  destroy: () => void
}

const MIN_HEIGHT = 320
const MARGIN = 20
const HOVER_DELAY_MS = 250

function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (char) => `&#${char.charCodeAt(0)};`)
}

export function drawGraph({ svg: svgElement, nodes: viewNodes, links: viewLinks, forces, isDark, getSettings, onNodeClick }: DrawGraphOptions): DrawnGraph | null {
  const svg = select(svgElement)
  svg.selectAll('*').remove()
  if (viewNodes.length === 0) return null

  const palette = graphPalette(isDark)
  const settings = getSettings()
  const linkStroke = (link: GraphSimulationLink) =>
    getSettings().colorCoded && link.connection_type === 'manual' ? palette.manualLink : palette.link

  const simulationNodes: GraphSimulationNode[] = viewNodes.map((node) => ({ ...node, fx: null, fy: null }))
  const nodeById = new Map(simulationNodes.map((node) => [node.id, node]))
  const simulationLinks: GraphSimulationLink[] = viewLinks
    .filter((link) => nodeById.has(link.source_id) && nodeById.has(link.target_id))
    .map((link) => ({
      source: nodeById.get(link.source_id)!,
      target: nodeById.get(link.target_id)!,
      similarity: link.similarity || 0.5,
      connection_type: link.connection_type || 'similarity',
    }))

  const parent = svgElement.parentElement ?? document.body
  const width = Math.max(260, parent.clientWidth)
  const height = Math.max(MIN_HEIGHT, parent.clientHeight)
  svg.attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`).attr('preserveAspectRatio', 'xMidYMid meet')

  const rootLayer = svg.append('g').attr('class', 'zoom-layer')
  const chartLayer = rootLayer.append('g').attr('transform', `translate(${MARGIN},${MARGIN})`)
  const nodeRadius = () => nodeRadiusFor(getSettings().nodeSizeBase)

  const chargeForce = forceManyBody<GraphSimulationNode>().strength(-forces.repel * 20)
  const linkForce = forceLink<GraphSimulationNode, GraphSimulationLink>(simulationLinks)
    .id((node) => node.id)
    .distance(linkDistanceFor(settings.linkDistance))
    .strength(forces.link)
  const collisionForce = forceCollide<GraphSimulationNode>().radius(() => nodeRadius() + 6).iterations(2)
  const simulation = forceSimulation<GraphSimulationNode>(simulationNodes)
    .force('link', linkForce)
    .force('charge', chargeForce)
    .force('center', forceCenter((width - 2 * MARGIN) / 2, (height - 2 * MARGIN) / 2).strength(forces.center))
    .force('collision', collisionForce)
    .alpha(1)
    .alphaDecay(0.06)
    .velocityDecay(0.5)

  const links = chartLayer
    .append('g')
    .selectAll<SVGLineElement, GraphSimulationLink>('line')
    .data(simulationLinks)
    .enter()
    .append('line')
    .attr('stroke', linkStroke)
    .attr('stroke-width', (link) => linkWidthFor(link.similarity, settings.linkThicknessMul))
    .attr('stroke-opacity', 1)
    .attr('vector-effect', 'non-scaling-stroke')
    .attr('shape-rendering', 'geometricPrecision')
    .attr('stroke-linecap', 'round')
    .attr('stroke-linejoin', 'round')

  let isDragging = false
  const tooltipSelector = 'div.graph-tooltip'

  const nodes = chartLayer
    .append('g')
    .selectAll<SVGCircleElement, GraphSimulationNode>('circle')
    .data(simulationNodes)
    .enter()
    .append('circle')
    .attr('r', nodeRadius)
    .attr('fill', palette.nodeFill)
    .attr('stroke', palette.nodeStroke)
    .attr('stroke-width', 2)
    .style('cursor', 'pointer')

  const labels = chartLayer
    .append('g')
    .selectAll<SVGTextElement, GraphSimulationNode>('text')
    .data(simulationNodes)
    .enter()
    .append('text')
    .text((node) => {
      const title = node.title || 'Untitled'
      return title.length > 20 ? `${title.substring(0, 20)}...` : title
    })
    .attr('font-size', '12px')
    .attr('font-family', 'var(--font-sans)')
    .attr('fill', palette.label)
    .attr('stroke', palette.labelHalo)
    .attr('stroke-width', isDark ? 0 : 2)
    .style('paint-order', 'stroke')
    .attr('text-anchor', 'middle')
    .attr('dy', '0.35em')
    .style('pointer-events', 'none')
    .style('opacity', settings.showLabels ? 1 : 0)

  nodes.call(
    drag<SVGCircleElement, GraphSimulationNode>()
      .on('start', (event: D3DragEvent<SVGCircleElement, GraphSimulationNode, GraphSimulationNode>, node) => {
        if (!event.active) simulation.alphaTarget(0.3).restart()
        chargeForce.strength(-300)
        isDragging = true
        select('body').selectAll(tooltipSelector).style('visibility', 'hidden')
        node.fx = node.x
        node.fy = node.y
      })
      .on('drag', (event: D3DragEvent<SVGCircleElement, GraphSimulationNode, GraphSimulationNode>, node) => {
        node.fx = event.x
        node.fy = event.y
      })
      .on('end', (event: D3DragEvent<SVGCircleElement, GraphSimulationNode, GraphSimulationNode>, node) => {
        if (!event.active) simulation.alphaTarget(0)
        chargeForce.strength(-260)
        isDragging = false
        node.fx = null
        node.fy = null
        if (getSettings().showLabels) labels.style('opacity', 1)
      })
  )

  nodes.on('click', (_event: MouseEvent, node) => onNodeClick(node.id))

  select('body').selectAll(tooltipSelector).remove()
  const tooltip = select('body')
    .append('div')
    .attr('class', 'graph-tooltip')
    .style('position', 'absolute')
    .style('visibility', 'hidden')
    .style('background', 'rgba(0, 0, 0, 0.8)')
    .style('color', 'white')
    .style('padding', '8px')
    .style('border-radius', '6px')
    .style('font-size', '12px')
    .style('max-width', '220px')
    .style('pointer-events', 'none')
    .style('z-index', '1000')

  let hoverTimeout: ReturnType<typeof setTimeout> | null = null
  const hideTooltip = () => {
    if (hoverTimeout) {
      clearTimeout(hoverTimeout)
      hoverTimeout = null
    }
    tooltip.style('visibility', 'hidden')
  }

  const neighbors = new Map<string, Set<string>>()
  for (const link of simulationLinks) {
    const source = String(link.source.id)
    const target = String(link.target.id)
    if (!neighbors.has(source)) neighbors.set(source, new Set())
    if (!neighbors.has(target)) neighbors.set(target, new Set())
    neighbors.get(source)!.add(target)
    neighbors.get(target)!.add(source)
  }
  const isNeighborhood = (centerId: string, node: GraphSimulationNode) =>
    node.id === centerId || Boolean(neighbors.get(String(centerId))?.has(String(node.id)))

  const dimRest = (id: string) => {
    nodes.style('opacity', (node) => (isNeighborhood(id, node) ? 1 : 0.45))
    if (getSettings().showLabels) {
      labels.style('opacity', 1)
    } else {
      labels.style('opacity', (node) => (isNeighborhood(id, node) ? 1 : 0))
    }
    links
      .attr('stroke', (link) => (link.source.id === id || link.target.id === id ? palette.link : palette.linkDimmed))
      .attr('stroke-opacity', 1)
      .attr('stroke-width', (link) =>
        link.source.id === id || link.target.id === id ? 2 + Math.max(0.2, link.similarity) * 3.5 : 1 + Math.max(0.2, link.similarity) * 2
      )
  }

  const clearDim = () => {
    const current = getSettings()
    nodes.style('opacity', 1)
    labels.style('opacity', current.showLabels ? 1 : 0)
    links
      .attr('stroke', linkStroke)
      .attr('stroke-opacity', 1)
      .attr('stroke-width', (link) => linkWidthFor(link.similarity, current.linkThicknessMul))
  }

  nodes
    .on('mouseover', (_event: MouseEvent, node) => {
      if (isDragging) return
      if (hoverTimeout) clearTimeout(hoverTimeout)
      hoverTimeout = setTimeout(() => {
        if (isDragging) return
        dimRest(String(node.id))
        tooltip
          .style('visibility', 'visible')
          .html(
            `<strong>${escapeHtml(node.title || 'Untitled')}</strong><br/>${escapeHtml(node.content_preview || 'No preview available')}<br/><em>${node.word_count || 0} words</em>`
          )
        labels.style('opacity', (other) => (isNeighborhood(node.id, other) ? 1 : 0))
      }, HOVER_DELAY_MS)
    })
    .on('mousemove', (event: MouseEvent) => {
      if (tooltip.style('visibility') === 'visible') {
        tooltip.style('top', `${event.pageY - 10}px`).style('left', `${event.pageX + 10}px`)
      }
    })
    .on('mouseout', () => {
      hideTooltip()
      clearDim()
    })

  simulation.on('tick', () => {
    links
      .attr('x1', (link) => link.source.x || 0)
      .attr('y1', (link) => link.source.y || 0)
      .attr('x2', (link) => link.target.x || 0)
      .attr('y2', (link) => link.target.y || 0)
    nodes.attr('cx', (node) => node.x || 0).attr('cy', (node) => node.y || 0)
    labels.attr('x', (node) => node.x || 0).attr('y', (node) => (node.y || 0) + nodeRadius() + 13)
  })
  simulation.on('end', () => {
    simulation.alphaTarget(0)
  })

  const hideTooltipOnClick = () => tooltip.style('visibility', 'hidden')
  document.addEventListener('click', hideTooltipOnClick)

  const zoomBehavior = zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.5, 4])
    .on('zoom', (event: D3ZoomEvent<SVGSVGElement, unknown>) => {
      rootLayer.attr('transform', event.transform.toString())
    })
  svg.call(zoomBehavior)

  return {
    nodes,
    links,
    labels,
    simulation,
    linkForce,
    collisionForce,
    nodeIds: new Set(simulationNodes.map((node) => String(node.id))),
    destroy: () => {
      hideTooltip()
      tooltip.remove()
      simulation.stop()
      svg.on('.zoom', null)
      document.removeEventListener('click', hideTooltipOnClick)
    },
  }
}
