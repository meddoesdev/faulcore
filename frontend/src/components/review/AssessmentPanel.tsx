import { AlertCircle, CheckCircle2, EyeOff, FileSearch, ShieldCheck } from 'lucide-react'
import { StatusPill } from '../StatusPill'
import type { AgentAssessment } from '../../types'

interface AssessmentPanelProps {
  assessment: AgentAssessment | null
  role: 'investigator' | 'reviewer'
  visible: boolean
}

function ScopeGroup({ label, ids, tone }: { label: string; ids: string[]; tone: 'confirmed' | 'possible' | 'excluded' }) {
  return (
    <div className="scope-group">
      <span>{label}</span>
      <div>
        {ids.length > 0 ? ids.map((id) => <StatusPill tone={tone} key={id}>{id}</StatusPill>) : <small>None declared</small>}
      </div>
    </div>
  )
}

export function AssessmentPanel({ assessment, role, visible }: AssessmentPanelProps) {
  const isReviewer = role === 'reviewer'
  const isBaseline = assessment?.agent === 'baseline'

  if (!visible) {
    return (
      <section className="assessment-panel pending-panel" data-role={role} aria-label={`${role} pending`}>
        <div className="agent-orbit"><span /><i /></div>
        <strong>{isReviewer ? 'Independent review queued' : 'Trace investigation running'}</strong>
        <p>{isReviewer ? 'Reviewer context remains isolated until the Investigator commits.' : 'Reconstructing exposure paths from deterministic trace evidence.'}</p>
      </section>
    )
  }

  if (!assessment) {
    return (
      <section className="assessment-panel empty-panel" data-role={role}>
        <AlertCircle size={20} />
        <strong>No {role} assessment</strong>
        <p>The run completed without a structured assessment for this role.</p>
      </section>
    )
  }

  const confidence = Math.round(assessment.confidence * 100)

  return (
    <section className="assessment-panel" data-role={role}>
      <header className="assessment-header">
        <div className="agent-identity">
          <span className="agent-icon">{isReviewer ? <ShieldCheck size={18} /> : <FileSearch size={18} />}</span>
          <div><small>{isReviewer ? 'Independent control' : isBaseline ? 'Reference workflow' : 'Primary analysis'}</small><h3>{isReviewer ? 'Scope Reviewer' : isBaseline ? 'Single Agent Baseline' : 'Trace Investigator'}</h3></div>
        </div>
        <StatusPill tone={isReviewer ? 'cleared' : 'neutral'}>{isReviewer ? 'Blind review' : isBaseline ? 'Baseline' : 'Committed'}</StatusPill>
      </header>

      {isReviewer && <div className="isolation-banner"><EyeOff size={13} /><span>Investigator output was not present in this agent’s input state</span></div>}

      <div className="assessment-body">
        <p className="assessment-summary">{assessment.summary}</p>

        <div className="confidence-block">
          <div><span>Assessment confidence</span><strong>{confidence}%</strong></div>
          <div className="confidence-track" role="meter" aria-valuenow={confidence} aria-valuemin={0} aria-valuemax={100}>
            <i style={{ width: `${confidence}%` }} />
          </div>
        </div>

        <div className="scope-groups">
          <ScopeGroup label="Affected" ids={assessment.affected_lot_ids} tone="confirmed" />
          <ScopeGroup label="Possible" ids={assessment.possibly_affected_lot_ids} tone="possible" />
          <ScopeGroup label="Excluded" ids={assessment.excluded_lot_ids} tone="excluded" />
        </div>

        <div className="evidence-block">
          <h4>Evidence basis</h4>
          {assessment.evidence.length > 0 ? assessment.evidence.slice(0, 3).map((evidence) => (
            <div className="evidence-row" key={evidence.id}><CheckCircle2 size={13} /><div><strong>{evidence.kind}</strong><p>{evidence.summary}</p></div></div>
          )) : <p className="empty-copy">No evidence references returned.</p>}
        </div>

        <div className="gap-block" data-clear={assessment.missing_evidence.length === 0}>
          <h4>{assessment.missing_evidence.length === 0 ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />} Evidence gaps</h4>
          {assessment.missing_evidence.length === 0
            ? <p>No critical gaps declared</p>
            : <ul>{assessment.missing_evidence.map((gap) => <li key={gap}>{gap}</li>)}</ul>}
        </div>
      </div>
    </section>
  )
}
