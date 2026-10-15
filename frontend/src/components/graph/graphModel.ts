import type { SimulationLinkDatum, SimulationNodeDatum } from 'd3-force'
import type { GraphConnection, GraphData, GraphNode } from '@/lib/api'

export interface GraphSimulationNode extends GraphNode, SimulationNodeDatum {
  x?: number
  y?: number
  fx?: number | null
  fy?: number | null
}

export interface GraphSimulationLink extends SimulationLinkDatum<GraphSimulationNode> {
  source: GraphSimulationNode
  target: GraphSimulationNode
  similarity: number
  connection_type: string
}

export interface ViewGraph {
  viewNodes: GraphNode[]
  viewLinks: GraphConnection[]
}

export function computeViewGraph(graphData: GraphData | null, hideIsolated: boolean): ViewGraph {
  if (!graphData) return { viewNodes: [], viewLinks: [] }
  if (!hideIsolated) return { viewNodes: graphData.nodes, viewLinks: graphData.connections }
  const linkedIds = new Set<string>()
  for (const link of graphData.connections) {
    linkedIds.add(String(link.source_id))
    linkedIds.add(String(link.target_id))
  }
  return {
    viewNodes: graphData.nodes.filter((node) => linkedIds.has(String(node.id))),
    viewLinks: graphData.connections,
  }
}

export function graphPalette(isDark: boolean) {
  return {
    link: isDark ? '#ffffff' : '#334155',
    linkDimmed: isDark ? '#64748b' : '#94a3b8',
    manualLink: isDark ? '#f59e0b' : '#f97316',
    nodeFill: isDark ? '#fb923c' : '#f97316',
    nodeStroke: isDark ? '#f97316' : '#ea580c',
    label: isDark ? '#ffffff' : '#374151',
    labelHalo: isDark ? 'none' : '#ffffff',
  }
}

export const nodeRadiusFor = (nodeSizeBase: number) => Math.max(4, 8 * nodeSizeBase)
export const linkWidthFor = (similarity: number, thicknessMultiplier: number) => 1 + Math.max(0.2, similarity || 0) * (3 * thicknessMultiplier)
export const linkDistanceFor = (linkDistance: number) => Math.max(20, linkDistance * 5)
