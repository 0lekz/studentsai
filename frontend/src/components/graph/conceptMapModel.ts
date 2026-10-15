import type { ConceptMap, ConceptMapNode } from '@/lib/api'
import { STRONG_MASTERY } from '@/components/concepts/mastery'

export const LABEL_NODE_LIMIT = 60
const STUDY_NEXT_LIMIT = 5

export interface StudyNextItem {
  node: ConceptMapNode
  prerequisites: ConceptMapNode[]
}

const isStrong = (node: ConceptMapNode) => node.mastery !== null && node.mastery >= STRONG_MASTERY

export function prerequisitesOf(map: ConceptMap, conceptId: string): ConceptMapNode[] {
  const byId = new Map(map.nodes.map((node) => [node.id, node]))
  return map.edges
    .filter((edge) => edge.kind === 'prerequisite' && edge.target === conceptId)
    .flatMap((edge) => byId.get(edge.source) ?? [])
}

export function dependentsOf(map: ConceptMap, conceptId: string): ConceptMapNode[] {
  const byId = new Map(map.nodes.map((node) => [node.id, node]))
  return map.edges
    .filter((edge) => edge.kind === 'prerequisite' && edge.source === conceptId)
    .flatMap((edge) => byId.get(edge.target) ?? [])
}

export function relatedTo(map: ConceptMap, conceptId: string): ConceptMapNode[] {
  const byId = new Map(map.nodes.map((node) => [node.id, node]))
  return map.edges
    .filter((edge) => edge.kind === 'related' && (edge.source === conceptId || edge.target === conceptId))
    .flatMap((edge) => byId.get(edge.source === conceptId ? edge.target : edge.source) ?? [])
}

// Concepts that are not strong yet and whose prerequisites all are, in course order.
export function studyNext(map: ConceptMap, limit: number = STUDY_NEXT_LIMIT): StudyNextItem[] {
  return [...map.nodes]
    .sort((a, b) => a.order - b.order)
    .filter((node) => !isStrong(node))
    .map((node) => ({ node, prerequisites: prerequisitesOf(map, node.id) }))
    .filter(({ prerequisites }) => prerequisites.every(isStrong))
    .slice(0, limit)
}

export function strongCount(map: ConceptMap): number {
  return map.nodes.filter(isStrong).length
}
