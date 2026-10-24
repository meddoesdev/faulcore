export type ScenarioId = 'clean-trace-01' | 'over-recall-01' | 'broken-trace-01'
export type RunMode = 'faultcore' | 'baseline'
export type RunStatus = 'running' | 'completed' | 'failed'
export type Difficulty = 'standard' | 'adversarial' | 'critical'

export interface Scenario {
  id: ScenarioId
  name: string
  alert_type: string
  product: string
  difficulty: Difficulty
  description: string
}

export type GraphNodeType =
  | 'supplier_lot'
  | 'transformation'
  | 'facility'
  | 'distribution_center'
  | 'store'
  | 'order'

export type ExposureState = 'confirmed' | 'possible' | 'excluded'
export type InventoryState = 'available' | 'held' | 'cleared' | 'in_transit'

export interface GraphNode {
  id: string
  type: GraphNodeType
  label: string
  exposure: ExposureState
  inventory_state?: InventoryState
  metadata: Record<string, string | number | boolean | null>
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  exposure: ExposureState
  label?: string
}

export interface GraphData {
  scenario_id: ScenarioId
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface EvidenceReference {
  id: string
  kind: 'alert' | 'trace' | 'transformation' | 'shipment' | 'inventory' | 'complaint'
  summary: string
}

export interface AgentAssessment {
  agent: 'investigator' | 'reviewer' | 'baseline'
  summary: string
  affected_lot_ids: string[]
  possibly_affected_lot_ids: string[]
  excluded_lot_ids: string[]
  evidence: EvidenceReference[]
  missing_evidence: string[]
  confidence: number
}

export interface ArbiterDecision {
  decision: 'accept' | 'correct' | 'broaden' | 'escalate'
  summary: string
  final_scope_lot_ids: string[]
  disagreements: string[]
  requested_correction: string | null
  confidence: number
}

export interface PolicyCheck {
  id: string
  name: string
  status: 'pass' | 'fail' | 'escalate'
  detail: string
}

export interface Action {
  id: string
  type: 'run_trace_diagnostics' | 'place_inventory_hold' | 'block_fulfillment' | 'escalate_incident'
  status: 'approved' | 'rejected' | 'executed' | 'escalated'
  target_ids: string[]
  detail: string
}

export interface Verification {
  affected_units: number
  contained_units: number
  missed_units: number
  safe_units_held: number
  safe_units_available: number
  residual_risk: 'none' | 'low' | 'medium' | 'high'
  checks: Array<{ name: string; passed: boolean; detail: string }>
}

export interface Metrics {
  containment_precision: number
  containment_recall: number
  safe_inventory_preserved: number
  under_containment_rate: number
  over_containment_rate: number
  time_to_containment_seconds: number
}

export interface RunEvent {
  id: string
  sequence: number
  timestamp: string
  stage: 'alert' | 'investigation' | 'review' | 'arbitration' | 'policy' | 'action' | 'verification'
  status: 'started' | 'completed' | 'failed' | 'info'
  message: string
}

export interface Run {
  run_id: string
  scenario_id: ScenarioId
  mode: RunMode
  status: RunStatus
  events: RunEvent[]
  investigator: AgentAssessment | null
  reviewer: AgentAssessment | null
  arbiter: ArbiterDecision | null
  policy_checks: PolicyCheck[]
  actions: Action[]
  verification: Verification | null
  metrics: Metrics | null
  error: string | null
}

export interface StartRunRequest {
  scenario_id: ScenarioId
  mode: RunMode
}

export interface StartRunResponse {
  run_id: string
  status: 'running'
}

