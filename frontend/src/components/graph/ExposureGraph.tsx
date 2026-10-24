import {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
  type NodeMouseHandler,
} from '@xyflow/react'
import { Braces, CircleX, LocateFixed, PackageSearch, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { GraphData, GraphNode } from '../../types'
import { ExposureNode } from './ExposureNode'
import { layoutGraph, type ExposureFlowNode } from './layoutGraph'

const nodeTypes = { exposure: ExposureNode }

interface ExposureGraphProps {
  graph: GraphData
}

function formatMetadataKey(key: string) {
  return key.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function ExposureGraph({ graph }: ExposureGraphProps) {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const elements = useMemo(() => layoutGraph(graph), [graph])

  useEffect(() => setSelectedNode(null), [graph.scenario_id])

  const handleNodeClick: NodeMouseHandler<ExposureFlowNode> = (_event, node) => {
    setSelectedNode(node.data.graphNode)
  }

  return (
    <div className="graph-shell">
      <ReactFlow<ExposureFlowNode>
        nodes={elements.nodes}
        edges={elements.edges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        onPaneClick={() => setSelectedNode(null)}
        nodesConnectable={false}
        nodesDraggable={false}
        minZoom={0.45}
        maxZoom={1.65}
        fitView
        fitViewOptions={{ padding: 0.2, maxZoom: 1.1 }}
      >
        <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="#26384a" />
        <Controls showInteractive={false} position="bottom-left" />
      </ReactFlow>

      {!selectedNode && (
        <div className="graph-instruction"><LocateFixed size={14} /> Select a node for trace evidence</div>
      )}

      {selectedNode && (
        <aside className="node-drawer" aria-label={`${selectedNode.label} details`}>
          <header>
            <div><PackageSearch size={17} /><span>Node evidence</span></div>
            <button onClick={() => setSelectedNode(null)} aria-label="Close node details"><X size={16} /></button>
          </header>
          <div className="drawer-body">
            <p className="drawer-type">{selectedNode.type.replaceAll('_', ' ')}</p>
            <h3>{selectedNode.label}</h3>
            <code>{selectedNode.id}</code>

            <div className="drawer-statuses">
              <span data-exposure={selectedNode.exposure}><i />{selectedNode.exposure}</span>
              {selectedNode.inventory_state && <span data-inventory={selectedNode.inventory_state}><i />{selectedNode.inventory_state.replace('_', ' ')}</span>}
            </div>

            <section>
              <h4><Braces size={13} /> Trace metadata</h4>
              {Object.keys(selectedNode.metadata).length === 0 ? (
                <p className="drawer-empty"><CircleX size={13} /> No additional metadata recorded</p>
              ) : (
                <dl>
                  {Object.entries(selectedNode.metadata).map(([key, value]) => (
                    <div key={key}><dt>{formatMetadataKey(key)}</dt><dd>{String(value)}</dd></div>
                  ))}
                </dl>
              )}
            </section>
          </div>
        </aside>
      )}
    </div>
  )
}
