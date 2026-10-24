import { Handle, Position, type NodeProps } from '@xyflow/react'
import {
  Factory,
  GitMerge,
  PackageOpen,
  ShoppingBag,
  Store,
  Warehouse,
} from 'lucide-react'
import type { GraphNodeType } from '../../types'
import type { ExposureFlowNode } from './layoutGraph'

const nodeIcon = {
  supplier_lot: PackageOpen,
  transformation: GitMerge,
  facility: Factory,
  distribution_center: Warehouse,
  store: Store,
  order: ShoppingBag,
} satisfies Record<GraphNodeType, typeof Factory>

const nodeTypeLabel: Record<GraphNodeType, string> = {
  supplier_lot: 'Supplier lot',
  transformation: 'Transformation',
  facility: 'Facility lot',
  distribution_center: 'Distribution centre',
  store: 'Store',
  order: 'Customer order',
}

export function ExposureNode({ data, selected }: NodeProps<ExposureFlowNode>) {
  const node = data.graphNode
  const Icon = nodeIcon[node.type]

  return (
    <div
      className="exposure-flow-node"
      data-exposure={node.exposure}
      data-inventory={node.inventory_state ?? 'none'}
      data-selected={selected}
    >
      <Handle type="target" position={Position.Left} className="flow-handle" />
      <div className="flow-node-icon"><Icon size={17} /></div>
      <div className="flow-node-copy">
        <span>{nodeTypeLabel[node.type]}</span>
        <strong>{node.label}</strong>
        <small>{node.id}</small>
      </div>
      <div className="flow-node-flags">
        <i aria-hidden="true" />
        {node.inventory_state && <em>{node.inventory_state.replace('_', ' ')}</em>}
      </div>
      <Handle type="source" position={Position.Right} className="flow-handle" />
    </div>
  )
}

