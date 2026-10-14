'use client'

import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { select, type Selection, type ValueFn } from 'd3-selection'
import { zoom, type D3ZoomEvent } from 'd3-zoom'
import { drag, type D3DragEvent } from 'd3-drag'
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide, type SimulationNodeDatum, type SimulationLinkDatum, type ForceLink, type Simulation, type ForceCollide } from 'd3-force'
import { api, APIError, type GraphData, type GraphNode, type GraphConnection } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Network, RefreshCw } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'

interface NotesGraphProps {
  onNodeClick?: (nodeId: string) => void
  highlightNodeIds?: string[]
  mode?: 'full' | 'mini'
  anchorNodeId?: string
}

// Extend GraphNode with D3.js simulation properties
interface GraphSimulationNode extends GraphNode, SimulationNodeDatum {
  x?: number
  y?: number
  fx?: number | null
  fy?: number | null
}

// D3.js link interface
interface GraphSimulationLink extends SimulationLinkDatum<GraphSimulationNode> {
  source: GraphSimulationNode
  target: GraphSimulationNode
  similarity: number
  connection_type: string
}

export function NotesGraph({ onNodeClick, highlightNodeIds = [], mode = 'full', anchorNodeId }: NotesGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const nodesSelRef = useRef<Selection<SVGCircleElement, unknown, null, undefined> | null>(null)
  const linksSelRef = useRef<Selection<SVGLineElement, unknown, null, undefined> | null>(null)
  const labelsSelRef = useRef<Selection<SVGTextElement, unknown, null, undefined> | null>(null)
  const currentNodeIdsRef = useRef<Set<string>>(new Set())
  const onNodeClickRef = useRef(onNodeClick)
  const simulationRef = useRef<Simulation<GraphSimulationNode, GraphSimulationLink> | null>(null)
  const linkForceRef = useRef<ForceLink<GraphSimulationNode, GraphSimulationLink> | null>(null)
  const collisionForceRef = useRef<ForceCollide<GraphSimulationNode> | null>(null)
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [interactionMode] = useState<'repel' | 'attract'>('repel')
  const interactionModeRef = useRef<'repel' | 'attract'>(interactionMode)
  const isDraggingRef = useRef<boolean>(false)

  // UX controls (inspired by Obsidian)
  // Local/Depth controls temporarily hidden per UX feedback
  const [localMode, setLocalMode] = useState<boolean>(false)
  const [depth, setDepth] = useState<number>(1)
  const [hideIsolated, setHideIsolated] = useState<boolean>(true)
  const [focusSet, setFocusSet] = useState<Set<string>>(new Set())
  const [collapsedSet] = useState<Set<string>>(new Set())

  // Adjustable forces (defaults provided by user)
  const [centerForce] = useState<number>(0.65)
  const [repelForce] = useState<number>(12.4)
  const [linkForce] = useState<number>(0.91)
  const [linkDistance, setLinkDistance] = useState<number>(30)
  const [nodeSizeBase, setNodeSizeBase] = useState<number>(0.51)
  const [linkThicknessMul, setLinkThicknessMul] = useState<number>(0.1)
  const [colorCoded, setColorCoded] = useState<boolean>(false)
  const [showLabels, setShowLabels] = useState<boolean>(mode === 'mini' ? true : false)
  const [, setThemeKey] = useState<number>(0)

  // highlight ids are used directly where needed

  useEffect(() => {
    interactionModeRef.current = interactionMode
  }, [interactionMode])

  useEffect(() => {
    onNodeClickRef.current = onNodeClick
  }, [onNodeClick])

  // Re-render graph when theme (html.dark) toggles
  useEffect(() => {
    if (typeof document === 'undefined') return
    const html = document.documentElement
    const observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.type === 'attributes' && m.attributeName === 'class') {
          setThemeKey((k) => k + 1)
          break
        }
      }
    })
    observer.observe(html, { attributes: true, attributeFilter: ['class'] })
    return () => observer.disconnect()
  }, [])

  const loadGraphData = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await api.getNotesGraph()
      setGraphData(data)
      // initialize local focus with first node only in full mode to avoid mini picking random
      if (mode !== 'mini' && data?.nodes?.length) {
        setFocusSet((prev) => (prev.size === 0 ? new Set([String(data.nodes[0].id)]) : prev))
      }
    } catch (err) {
      console.error('Failed to load graph data:', err)
      if (err instanceof APIError) {
        setError(`Failed to load graph (status ${err.status}): ${err.message}`)
      } else {
        setError('Failed to load graph data')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadGraphData()
  }, [])

  // When in mini mode, always focus on anchor node and its immediate neighbors
  useEffect(() => {
    if (mode !== 'mini' || !anchorNodeId) return
    setLocalMode(true)
    setHideIsolated(true)
    setDepth(1)
    setFocusSet(new Set([String(anchorNodeId)]))
    // Force labels on in mini mode
    setShowLabels(true)
  }, [mode, anchorNodeId])

  // Compute local view subgraph (BFS from focusSet up to depth), apply collapsed/hide-isolated
  const { viewNodes, viewLinks } = useMemo(() => {
    if (!graphData) return { viewNodes: [] as GraphNode[], viewLinks: [] as GraphConnection[] }
    const idToNode = new Map(graphData.nodes.map(n => [String(n.id), n]))
    // Mini mode: return connected component of anchorNodeId
    if (mode === 'mini' && anchorNodeId) {
      const start = String(anchorNodeId)
      const adj = new Map<string, Set<string>>()
      for (const l of graphData.connections) {
        const a = String(l.source_id), b = String(l.target_id)
        if (!adj.has(a)) adj.set(a, new Set())
        if (!adj.has(b)) adj.set(b, new Set())
        adj.get(a)!.add(b)
        adj.get(b)!.add(a)
      }
      const visited = new Set<string>()
      const queue: string[] = []
      if (idToNode.has(start)) {
        visited.add(start)
        queue.push(start)
      }
      while (queue.length) {
        const cur = queue.shift() as string
        const nbrs = adj.get(cur)
        if (!nbrs) continue
        for (const nb of nbrs) {
          if (!visited.has(nb)) { visited.add(nb); queue.push(nb) }
        }
      }
      const nodes = Array.from(visited).map(id => idToNode.get(id)!).filter(Boolean)
      const nodeSet = new Set(nodes.map(n => String(n.id)))
      const links = graphData.connections.filter(c => nodeSet.has(String(c.source_id)) && nodeSet.has(String(c.target_id)))
      return { viewNodes: nodes, viewLinks: links }
    }
    if (!localMode || focusSet.size === 0) {
      // full graph, optionally hide isolated
      const linkPairs = graphData.connections
      const linkedIds = new Set<string>()
      if (hideIsolated) {
        for (const l of linkPairs) {
          linkedIds.add(String(l.source_id)); linkedIds.add(String(l.target_id))
        }
      }
      const nodes = hideIsolated ? graphData.nodes.filter(n => linkedIds.has(String(n.id))) : graphData.nodes
      return { viewNodes: nodes, viewLinks: linkPairs }
    }
    // BFS to specified depth
    const adj = new Map<string, Set<string>>()
    for (const l of graphData.connections) {
      const a = String(l.source_id), b = String(l.target_id)
      if (!adj.has(a)) adj.set(a, new Set())
      if (!adj.has(b)) adj.set(b, new Set())
      adj.get(a)!.add(b)
      adj.get(b)!.add(a)
    }
    const included = new Set<string>(Array.from(focusSet))
    let frontier = Array.from(focusSet)
    for (let d = 0; d < depth; d++) {
      const next: string[] = []
      for (const id of frontier) {
        const nbrs = adj.get(id); if (!nbrs) continue
        for (const nb of nbrs) {
          // skip collapsed nodes' external expansion
          if (collapsedSet.has(id) && !focusSet.has(nb)) continue
          if (!included.has(nb)) { included.add(nb); next.push(nb) }
        }
      }
      frontier = next
    }
    const nodes = Array.from(included).map(id => idToNode.get(id)!).filter(Boolean)
    const nodeSet = new Set(nodes.map(n => String(n.id)))
    const links = graphData.connections.filter(c => nodeSet.has(String(c.source_id)) && nodeSet.has(String(c.target_id)))
    // optionally hide isolated in the local set
    if (hideIsolated) {
      const linkedIds = new Set<string>()
      for (const l of links) { linkedIds.add(String(l.source_id)); linkedIds.add(String(l.target_id)) }
      return { viewNodes: nodes.filter(n => linkedIds.has(String(n.id))), viewLinks: links }
    }
    return { viewNodes: nodes, viewLinks: links }
  }, [graphData, localMode, focusSet, depth, hideIsolated, collapsedSet])

  const renderGraph = useCallback((): (() => void) | void => {
    if (!graphData || !svgRef.current) return

    // Validate graph data
    if (!viewNodes || !Array.isArray(viewNodes) || viewNodes.length === 0) {
      console.warn('No valid nodes found in graph data')
      return
    }

    if (!viewLinks || !Array.isArray(viewLinks)) {
      console.warn('No valid connections found in graph data')
      return
    }

    // Convert nodes to simulation nodes
    const simulationNodes: GraphSimulationNode[] = viewNodes.map(node => ({
      ...node,
      x: undefined,
      y: undefined,
      fx: null,
      fy: null
    }))
    currentNodeIdsRef.current = new Set(simulationNodes.map(n => String(n.id)))

    // Create a map for quick node lookup
    const nodeMap = new Map(simulationNodes.map(node => [node.id, node]))

    // Filter and transform connections to D3.js format
    const validConnections: GraphSimulationLink[] = viewLinks
      .filter(connection => {
        const sourceExists = nodeMap.has(connection.source_id)
        const targetExists = nodeMap.has(connection.target_id)
        return sourceExists && targetExists
      })
      .map(connection => ({
        source: nodeMap.get(connection.source_id)!,
        target: nodeMap.get(connection.target_id)!,
        similarity: connection.similarity || 0.5,
        connection_type: connection.connection_type || 'similarity'
      }))

    console.log('Graph data:', {
      nodes: simulationNodes.length,
      connections: validConnections.length,
      totalConnections: (graphData.connections?.length || 0)
    })

    const svg = select(svgRef.current)
    svg.selectAll('*').remove()

    // Responsive sizing based on container width
    const parent = (svgRef.current.parentElement as HTMLElement) || document.body
    const width = mode === 'mini' ? Math.max(260, parent.clientWidth) : Math.max(600, parent.clientWidth)
    const dynamicHeight = typeof window !== 'undefined' ? Math.floor(window.innerHeight * 0.75) : 600
    const height = mode === 'mini' ? 220 : Math.max(600, dynamicHeight)
    const margin = { top: 20, right: 20, bottom: 20, left: 20 }

    svg
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')

    // Theme-aware styling
    const isDark = typeof document !== 'undefined' && document.documentElement.classList.contains('dark')
    const linkBase = isDark ? '#ffffff' : '#334155'

    const rootG = svg.append('g').attr('class', 'zoom-layer')
    const g = rootG.append('g')
      .attr('class', 'chart-layer')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    // Node radius helper
    const nodeRadius = () => Math.max(4, 8 * nodeSizeBase)

    // Forces
    const chargeForce = forceManyBody().strength(-repelForce * 20)

    // Create simulation with tuned forces to reduce jitter/overlap
    const linkF = forceLink<GraphSimulationNode, GraphSimulationLink>(validConnections)
        .id((d: GraphSimulationNode) => d.id)
        .distance(Math.max(20, linkDistance * 5))
        .strength(linkForce)
    const collideF = forceCollide<GraphSimulationNode>().radius(() => nodeRadius() + 6).iterations(2)

    const simulation = forceSimulation<GraphSimulationNode>(simulationNodes)
      .force('link', linkF)
      .force('charge', chargeForce)
      .force('center', forceCenter((width - margin.left - margin.right) / 2, (height - margin.top - margin.bottom) / 2).strength(centerForce))
      .force('collision', collideF)
      .alpha(1)
      .alphaDecay(0.06)
      .velocityDecay(0.5)

    // Save forces and simulation for incremental updates
    simulationRef.current = simulation
    linkForceRef.current = linkF
    collisionForceRef.current = collideF

    // Create links (main stroke)
    const links = g.append('g')
      .selectAll('line')
      .data(validConnections)
      .enter()
      .append('line')
      .attr('stroke', (d: GraphSimulationLink) => {
        if (!colorCoded) return linkBase
        return d.connection_type === 'manual' ? (isDark ? '#f59e0b' : '#f97316') : linkBase
      })
      .attr('stroke-width', (d: GraphSimulationLink) => 1 + Math.max(0.2, d.similarity) * (3 * linkThicknessMul))
      .attr('stroke-opacity', 1)
      .attr('vector-effect', 'non-scaling-stroke')
      .attr('shape-rendering', 'geometricPrecision')
      .attr('stroke-linecap', 'round')
      .attr('stroke-linejoin', 'round')

    // Create nodes
    const nodes = g.append('g')
      .selectAll('circle')
      .data(simulationNodes)
      .enter()
      .append('circle')
      .attr('r', () => nodeRadius())
      .attr('fill', isDark ? '#fb923c' : '#f97316')
      .attr('stroke', isDark ? '#f97316' : '#ea580c')
      .attr('stroke-width', mode === 'mini' ? 1.5 : 2)
      .style('cursor', 'pointer')
      .call(drag<SVGCircleElement, GraphSimulationNode>()
        .on('start', (event: D3DragEvent<SVGCircleElement, GraphSimulationNode, GraphSimulationNode | undefined>, d: GraphSimulationNode) => {
          if (!event.active) simulation.alphaTarget(0.3).restart()
          // Adjust physics on drag start based on interaction mode
          if (interactionModeRef.current === 'attract') {
            chargeForce.strength(240)
          } else {
            chargeForce.strength(-300)
          }
          isDraggingRef.current = true
          // Suppress any tooltip while dragging
          select('body').selectAll('div.tooltip').style('visibility', 'hidden')
          d.fx = d.x
          d.fy = d.y
        })
        .on('drag', (event: D3DragEvent<SVGCircleElement, GraphSimulationNode, GraphSimulationNode | undefined>, d: GraphSimulationNode) => {
          d.fx = event.x
          d.fy = event.y
        })
        .on('end', (event: D3DragEvent<SVGCircleElement, GraphSimulationNode, GraphSimulationNode | undefined>, d: GraphSimulationNode) => {
          if (!event.active) simulation.alphaTarget(0)
          // Reset physics to default repel after drag ends
          chargeForce.strength(-260)
          isDraggingRef.current = false
          d.fx = null
          d.fy = null
          // Restore labels if toggle is on
          if (showLabels && labelsSelRef.current) {
            labelsSelRef.current.style('opacity', 1)
          }
        }))

    // Add click handler to nodes
    nodes.on('click', (_event: MouseEvent, d: GraphSimulationNode) => {
      // Expand local graph by making this node a focus
      const next = new Set(focusSet)
      if (next.has(String(d.id))) next.delete(String(d.id)); else next.add(String(d.id))
      setFocusSet(next)
      onNodeClickRef.current?.(d.id)
    })

    // Add labels
    const labels = g.append('g')
      .selectAll('text')
      .data(simulationNodes)
      .enter()
      .append('text')
      .text((d: GraphSimulationNode) => (d.title || 'Untitled').length > 20 ? (d.title || 'Untitled').substring(0, 20) + '...' : (d.title || 'Untitled'))
      .attr('font-size', mode === 'mini' ? '10px' : '12px')
      .attr('font-family', 'system-ui, sans-serif')
      .attr('fill', isDark ? '#ffffff' : '#374151')
      .attr('stroke', isDark ? 'none' : '#ffffff')
      .attr('stroke-width', isDark ? 0 : 2)
      .style('paint-order', 'stroke')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .style('pointer-events', 'none')
      .style('opacity', mode === 'mini' ? 0 : (showLabels ? 1 : 0))

    // Save selections for incremental updates
    nodesSelRef.current = nodes as unknown as Selection<SVGCircleElement, unknown, null, undefined>
    linksSelRef.current = links as unknown as Selection<SVGLineElement, unknown, null, undefined>
    labelsSelRef.current = labels as unknown as Selection<SVGTextElement, unknown, null, undefined>

    // Add tooltips (clean any existing first) and configure interactions
    select('body').selectAll('div.tooltip').remove()
    const tooltip = select('body').append('div')
      .attr('class', 'tooltip')
      .style('position', 'absolute')
      .style('visibility', 'hidden')
      .style('background', 'rgba(0, 0, 0, 0.8)')
      .style('color', 'white')
      .style('padding', '8px')
      .style('border-radius', '4px')
      .style('font-size', '12px')
      .style('max-width', '200px')
      .style('z-index', '1000')

    let hoverTimeout: ReturnType<typeof setTimeout> | null = null
    const showTooltip = (html: string) => {
      tooltip.style('visibility', 'visible').html(html)
    }
    const hideTooltip = () => {
      if (hoverTimeout) {
        clearTimeout(hoverTimeout)
        hoverTimeout = null
      }
      tooltip.style('visibility', 'hidden')
    }

    // Precompute neighbors for highlighting
    const neighborMap = new Map<string, Set<string>>()
    validConnections.forEach((l) => {
      const s = String(l.source.id)
      const t = String(l.target.id)
      if (!neighborMap.has(s)) neighborMap.set(s, new Set<string>())
      if (!neighborMap.has(t)) neighborMap.set(t, new Set<string>())
      neighborMap.get(s)!.add(t)
      neighborMap.get(t)!.add(s)
    })

    const dimRest = (id: string) => {
      nodes.style('opacity', (d: GraphSimulationNode) => (d.id === id || neighborMap.get(String(id))?.has(String(d.id)) ? 1 : 0.45))
      if (showLabels) {
        labels.style('opacity', 1)
      } else {
        labels.style('opacity', (d: GraphSimulationNode) => (d.id === id || neighborMap.get(String(id))?.has(String(d.id)) ? 1 : 0))
      }
      links
        .attr('stroke', (l: GraphSimulationLink) => (l.source.id === id || l.target.id === id ? linkBase : (isDark ? '#64748b' : '#94a3b8')))
        .attr('stroke-opacity', 1)
        .attr('stroke-width', (l: GraphSimulationLink) => (l.source.id === id || l.target.id === id ? 2 + Math.max(0.2, l.similarity) * 3.5 : 1 + Math.max(0.2, l.similarity) * 2))
    }

    const clearDim = () => {
      nodes.style('opacity', 1)
      labels.style('opacity', showLabels ? 1 : 0)
      links
        .attr('stroke', (d: GraphSimulationLink) => {
          if (!colorCoded) return linkBase
          return d.connection_type === 'manual' ? (isDark ? '#f59e0b' : '#f97316') : linkBase
        })
        .attr('stroke-opacity', 1)
        .attr('stroke-width', (d: GraphSimulationLink) => 1 + Math.max(0.2, d.similarity) * (3 * linkThicknessMul))
    }

    nodes
      .on('mouseover', (_event: MouseEvent, d: GraphSimulationNode) => {
        if (isDraggingRef.current) return
        if (hoverTimeout) clearTimeout(hoverTimeout)
        hoverTimeout = setTimeout(() => {
          if (isDraggingRef.current) return
          dimRest(String(d.id))
          showTooltip(`
            <strong>${d.title || 'Untitled'}</strong><br/>
            ${d.content_preview || 'No preview available'}<br/>
            <em>${d.word_count || 0} words</em>
          `)
          // On hover, show labels for hovered and adjacent only
          labels.style('opacity', (n: GraphSimulationNode) => (n.id === d.id || neighborMap.get(String(d.id))?.has(String(n.id)) ? 1 : 0))
        }, 250)
      })
      .on('mousemove', (event: MouseEvent) => {
        if (tooltip.style('visibility') === 'visible') {
          tooltip.style('top', (event.pageY - 10) + 'px')
            .style('left', (event.pageX + 10) + 'px')
        }
      })
      .on('mouseout', () => {
        hideTooltip()
        clearDim()
        // After hover, restore global labels state
        if (labelsSelRef.current) {
          labelsSelRef.current.style('opacity', showLabels ? 1 : 0)
        }
      })

    // Update positions on simulation tick
    simulation.on('tick', () => {
      links
        .attr('x1', (d: GraphSimulationLink) => d.source.x || 0)
        .attr('y1', (d: GraphSimulationLink) => d.source.y || 0)
        .attr('x2', (d: GraphSimulationLink) => d.target.x || 0)
        .attr('y2', (d: GraphSimulationLink) => d.target.y || 0)

      nodes
        .attr('cx', (d: GraphSimulationNode) => d.x || 0)
        .attr('cy', (d: GraphSimulationNode) => d.y || 0)

      labels
        .attr('x', (d: GraphSimulationNode) => d.x || 0)
        .attr('y', (d: GraphSimulationNode) => (d.y || 0) + nodeRadius() + 13)
    })

    // Hide tooltip on clicks
    const onAnyClick = () => {
      select('body').selectAll('div.tooltip').style('visibility', 'hidden')
    }
    document.addEventListener('click', onAnyClick)

    // Stop simulation when stabilized to reduce jitter
    simulation.on('end', () => {
      simulation.alphaTarget(0)
    })

    // Zoom & pan
    const zoomBehavior = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 4])
      .on('zoom', (event: D3ZoomEvent<SVGSVGElement, unknown>) => {
        rootG.attr('transform', event.transform.toString())
      })

    svg.call(zoomBehavior)

    // Cleanup function
    return () => {
      tooltip.remove()
      simulation.stop()
      svg.on('.zoom', null)
      document.removeEventListener('click', onAnyClick)
    }
  }, [graphData, viewNodes.length, viewLinks.length, localMode, depth, linkForce, centerForce, repelForce, focusSet])

  // Incremental visual updates for highlight and labels without full rerender
  useEffect(() => {
    const nodes = nodesSelRef.current
    const links = linksSelRef.current
    const labels = labelsSelRef.current
    if (!nodes || !links || !labels) return
    const isDark = typeof document !== 'undefined' && document.documentElement.classList.contains('dark')
    const linkBase = isDark ? '#ffffff' : '#334155'
    const setStrokeColor = (d: GraphSimulationLink) => (colorCoded && d.connection_type === 'manual' ? (isDark ? '#f59e0b' : '#f97316') : linkBase)

    const ids = new Set((highlightNodeIds || []).map(String))
    const hasAny = (() => {
      if (ids.size === 0) return false
      for (const id of ids) if (currentNodeIdsRef.current.has(id)) return true
      return false
    })()
    if (ids.size === 0) {
      const nodeOpacityAll: ValueFn<SVGCircleElement, unknown, number> = () => 1
      const labelOpacityAll: ValueFn<SVGTextElement, unknown, number> = () => (showLabels ? 1 : 0)
      const linkStrokeColorFn: ValueFn<SVGLineElement, unknown, string> = (d) => setStrokeColor(d as unknown as GraphSimulationLink)
      nodes.style('opacity', nodeOpacityAll)
      labels.style('opacity', labelOpacityAll)
      links
        .attr('stroke', linkStrokeColorFn)
        .attr('stroke-opacity', 1)
      return
    }
    if (!hasAny) {
      const nodeOpacityAll: ValueFn<SVGCircleElement, unknown, number> = () => 1
      const labelOpacityAll: ValueFn<SVGTextElement, unknown, number> = () => (showLabels ? 1 : 0)
      const linkStrokeColorFn: ValueFn<SVGLineElement, unknown, string> = (d) => setStrokeColor(d as unknown as GraphSimulationLink)
      nodes.style('opacity', nodeOpacityAll)
      labels.style('opacity', labelOpacityAll)
      links
        .attr('stroke', linkStrokeColorFn)
        .attr('stroke-opacity', 1)
      return
    }
    // Combine search highlight with hideIsolated logic without re-simulating
    // Build connected set from existing links data
    const linkData = (links as Selection<SVGLineElement, unknown, null, undefined>).data() as unknown as GraphSimulationLink[]
    const connected = new Set<string>()
    for (const l of linkData) { connected.add(String(l.source.id)); connected.add(String(l.target.id)) }
    const nodeOpacityFn: ValueFn<SVGCircleElement, unknown, number> = (d) => {
      const datum = d as unknown as GraphSimulationNode
      const idStr = String(datum.id)
      if (hideIsolated && !connected.has(idStr)) return 0
      return ids.has(idStr) ? 1 : 0.25
    }
    const labelOpacityFn: ValueFn<SVGTextElement, unknown, number> = (d) => (ids.has(String((d as unknown as GraphSimulationNode).id)) ? 1 : (showLabels ? 1 : 0))
    const linkOpacityFn: ValueFn<SVGLineElement, unknown, number> = (l) => (ids.has(String((l as unknown as GraphSimulationLink).source.id)) || ids.has(String((l as unknown as GraphSimulationLink).target.id)) ? 1 : 0.3)
    const linkStrokeColorFn: ValueFn<SVGLineElement, unknown, string> = (d) => setStrokeColor(d as unknown as GraphSimulationLink)
    nodes.style('opacity', nodeOpacityFn)
    labels.style('opacity', labelOpacityFn)
    links
      .attr('stroke-opacity', linkOpacityFn)
      .attr('stroke', linkStrokeColorFn)
  }, [highlightNodeIds, colorCoded, showLabels, hideIsolated])

  // Update edge thickness without full re-render to keep layout stable
  useEffect(() => {
    const links = linksSelRef.current as Selection<SVGLineElement, unknown, null, undefined> | null
    if (!links) return
    const widthFn: ValueFn<SVGLineElement, unknown, number> = (d) => 1 + Math.max(0.2, ((d as unknown as GraphSimulationLink).similarity || 0)) * (3 * linkThicknessMul)
    links.attr('stroke-width', widthFn)
  }, [linkThicknessMul])

  // Incremental update: link distance
  useEffect(() => {
    if (!linkForceRef.current || !simulationRef.current) return
    linkForceRef.current.distance(Math.max(20, linkDistance * 5))
    simulationRef.current.alphaTarget(0.2).restart()
    setTimeout(() => simulationRef.current && simulationRef.current.alphaTarget(0), 200)
  }, [linkDistance])

  // Incremental update: node size and collision
  useEffect(() => {
    const nodes = nodesSelRef.current
    if (!nodes || !collisionForceRef.current || !simulationRef.current) return
    const base = Math.max(4, 8 * nodeSizeBase)
    nodes.attr('r', base)
    collisionForceRef.current.radius(base + 6)
    simulationRef.current.alphaTarget(0.15).restart()
    setTimeout(() => simulationRef.current && simulationRef.current.alphaTarget(0), 200)
  }, [nodeSizeBase])

  // Auto-refresh graph when labels are toggled
  useEffect(() => {
    if (!graphData || !svgRef.current) return
    // Trigger a re-render when showLabels changes to properly position labels
    const cleanup = renderGraph()
    return () => {
      if (typeof cleanup === 'function') cleanup()
    }
  }, [showLabels, renderGraph])

  useEffect(() => {
    if (!graphData || !svgRef.current) return
    const cleanup = renderGraph()
    return () => {
      if (typeof cleanup === 'function') cleanup()
    }
  }, [graphData, renderGraph])

  if (loading) {
    return (
      <Card className="bg-white dark:bg-[#0b0f14] border border-gray-200 dark:border-gray-800">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2 text-gray-900 dark:text-gray-100">
            <Network className="h-5 w-5" />
            <span>Notes Graph</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500 mx-auto mb-4"></div>
              <p className="text-gray-600 dark:text-gray-300">Loading graph...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="bg-white dark:bg-[#0b0f14] border border-gray-200 dark:border-gray-800">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2 text-gray-900 dark:text-gray-100">
            <Network className="h-5 w-5" />
            <span>Notes Graph</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 px-4 py-3 rounded mb-4">
              {error}
            </div>
            <Button onClick={loadGraphData}>Try Again</Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
    return (
      <Card className="bg-white dark:bg-[#0b0f14] border border-gray-200 dark:border-gray-800">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2 text-gray-900 dark:text-gray-100">
            <Network className="h-5 w-5" />
            <span>Notes Graph</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <Network className="h-12 w-12 text-gray-400 dark:text-gray-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">No notes to visualize</h3>
            <p className="text-gray-600 dark:text-gray-300">Create at least 2 notes to see connections between them.</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="bg-white dark:bg-[#0b0f14] border border-gray-200 dark:border-gray-800">
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle className="flex items-center space-x-2 text-gray-900 dark:text-gray-100">
            <Network className="h-5 w-5" />
            <span>Notes Graph</span>
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={loadGraphData}
              disabled={loading}
              className="flex items-center space-x-1 dark:border-gray-700 dark:text-gray-200 dark:bg-[#0f1318] dark:hover:bg-[#1d2430]"
            >
              <RefreshCw className="h-4 w-4" />
              <span>Refresh</span>
            </Button>
          </div>
        </div>
        {mode !== 'mini' && (
          <>
            <div className="mt-3 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 items-center text-xs text-gray-700 dark:text-gray-300">
              <label className="flex items-center gap-2"><input type="checkbox" checked={hideIsolated} onChange={(e) => setHideIsolated(e.target.checked)} /> Hide isolated</label>
              <div className="flex items-center gap-2"><span>Distance</span><Input type="number" step={1} value={linkDistance} onChange={(e)=>setLinkDistance(Number(e.target.value)||0)} className="h-7 w-20 dark:bg-[#0f1318] dark:border-gray-700"/></div>
              <div className="flex items-center gap-2"><span>Node size</span><Input type="number" step={0.01} value={nodeSizeBase} onChange={(e)=>setNodeSizeBase(Number(e.target.value)||0)} className="h-7 w-24 dark:bg-[#0f1318] dark:border-gray-700"/></div>
              <div className="flex items-center gap-2"><span>Edge thickness</span><Input type="number" step={0.01} value={linkThicknessMul} onChange={(e)=>setLinkThicknessMul(Number(e.target.value)||0)} className="h-7 w-28 dark:bg-[#0f1318] dark:border-gray-700"/></div>
              <label className="flex items-center gap-2"><input type="checkbox" checked={colorCoded} onChange={(e)=>setColorCoded(e.target.checked)} /> Color coded</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={showLabels} onChange={(e)=>{ setShowLabels(e.target.checked); loadGraphData(); }} /> Labels</label>
            </div>
            <Separator className="mt-3 dark:bg-[#232a36]" />
            <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">
              Showing {viewNodes.length} nodes / {viewLinks.length} edges. Click a node to expand local view. Hover to reveal labels.
            </p>
          </>
        )}
      </CardHeader>
      <CardContent>
        <div className="w-full overflow-x-auto">
          <svg ref={svgRef} className="border border-gray-200 rounded"></svg>
        </div>
      </CardContent>
    </Card>
  )
}

