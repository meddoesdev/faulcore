import { MarkerType, type Edge, type Node } from '@xyflow/react'
import type { GraphData, GraphEdge, GraphNode } from '../../types'

export interface ExposureNodeData extends Record<string, unknown> {
  graphNode: GraphNode
}

export type ExposureFlowNode = Node<ExposureNodeData, 'exposure'>

const columnGap = 270
const rowGap = 118

const edgeAppearance: Record<GraphEdge['exposure'], { color: string; dash?: string; opacity: number }> = {
  confirmed: { color: '#ff647c', opacity: 0.92 },
  possible: { color: '#f7b955', dash: '7 5', opacity: 0.88 },
  excluded: { color: '#657589', dash: '3 7', opacity: 0.55 },
}

function calculateRanks(graph: GraphData): Map<string, number> {
  const nodeIds = new Set(graph.nodes.map((node) => node.id))
  const incoming = new Map(graph.nodes.map((node) => [node.id, 0]))
  const outgoing = new Map(graph.nodes.map((node) => [node.id, [] as string[]]))
  const rank = new Map(graph.nodes.map((node) => [node.id, 0]))

  for (const edge of graph.edges) {
    if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) continue
    incoming.set(edge.target, (incoming.get(edge.target) ?? 0) + 1)
    outgoing.get(edge.source)?.push(edge.target)
  }

  const queue = graph.nodes.filter((node) => incoming.get(node.id) === 0).map((node) => node.id)
  const visited = new Set<string>()

  while (queue.length > 0) {
    const source = queue.shift()
    if (!source || visited.has(source)) continue
    visited.add(source)

    for (const target of outgoing.get(source) ?? []) {
      rank.set(target, Math.max(rank.get(target) ?? 0, (rank.get(source) ?? 0) + 1))
      const nextIncoming = (incoming.get(target) ?? 1) - 1
      incoming.set(target, nextIncoming)
      if (nextIncoming === 0) queue.push(target)
    }
  }

  // Keep malformed cyclic fragments visible in their own trailing column.
  const trailingRank = Math.max(0, ...rank.values()) + 1
  for (const node of graph.nodes) {
    if (!visited.has(node.id)) rank.set(node.id, trailingRank)
  }

  return rank
}

export function layoutGraph(graph: GraphData): { nodes: ExposureFlowNode[]; edges: Edge[] } {
  const ranks = calculateRanks(graph)
  const columns = new Map<number, GraphNode[]>()

  for (const node of graph.nodes) {
    const nodeRank = ranks.get(node.id) ?? 0
    columns.set(nodeRank, [...(columns.get(nodeRank) ?? []), node])
  }

  const tallestColumn = Math.max(1, ...[...columns.values()].map((column) => column.length))
  const flowNodes: ExposureFlowNode[] = []

  for (const [rank, column] of [...columns.entries()].sort(([a], [b]) => a - b)) {
    const verticalOffset = ((tallestColumn - column.length) * rowGap) / 2
    column.forEach((graphNode, index) => {
      flowNodes.push({
        id: graphNode.id,
        type: 'exposure',
        position: { x: rank * columnGap, y: verticalOffset + index * rowGap },
        data: { graphNode },
        draggable: false,
        selectable: true,
      })
    })
  }

  const flowEdges: Edge[] = graph.edges.map((edge) => {
    const appearance = edgeAppearance[edge.exposure]
    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: 'smoothstep',
      label: edge.label,
      style: {
        stroke: appearance.color,
        strokeWidth: edge.exposure === 'confirmed' ? 2.2 : 1.7,
        strokeDasharray: appearance.dash,
        opacity: appearance.opacity,
      },
      labelStyle: { fill: '#8fa1b5', fontSize: 8, fontFamily: 'ui-monospace, monospace' },
      labelBgStyle: { fill: '#08101a', fillOpacity: 0.92 },
      markerEnd: { type: MarkerType.ArrowClosed, color: appearance.color, width: 15, height: 15 },
    }
  })

  return { nodes: flowNodes, edges: flowEdges }
}

