import { Activity, AlertOctagon, Check, CheckCircle2, CircleAlert, Clock3, Gavel, GitCompareArrows, ListChecks, Play, RotateCcw, ShieldCheck, X } from 'lucide-react'
import { useMemo } from 'react'
import type { AgentAssessment, Run, RunEvent } from '../../types'
import { StatusPill } from '../StatusPill'
import { AssessmentPanel } from './AssessmentPanel'

interface ReviewWorkspaceProps {
  run: Run | null
  isLoading: boolean
  error: Error | null
  onReplay: () => void
}

function assessmentScope(assessment: AgentAssessment | null) {
  return new Set([...(assessment?.affected_lot_ids ?? []), ...(assessment?.possibly_affected_lot_ids ?? [])])
}

const eventIcon: Record<RunEvent['stage'], typeof Activity> = {
  alert: CircleAlert, investigation: Activity, review: ShieldCheck, arbitration: Gavel,
  policy: ListChecks, action: Play, verification: CheckCircle2,
}

const stageProgress: Record<RunEvent['stage'], number> = {
  alert: 0.1, investigation: 0.28, review: 0.46, arbitration: 0.64,
  policy: 0.78, action: 0.9, verification: 1,
}

function failureCopy(message: string) {
  const normalized = message.toLowerCase()
  if (normalized.includes('invalid') || normalized.includes('schema') || normalized.includes('malformed')) {
    return {
      title: 'Model output rejected safely',
      guidance: 'The response did not satisfy the required contract after repair. No containment action was accepted.',
    }
  }
  if (normalized.includes('provider') || normalized.includes('api key') || normalized.includes('configured')) {
    return {
      title: 'Reasoning provider unavailable',
      guidance: 'Check provider credentials, or restart the backend with LLM_PROVIDER=mock for an explicit offline demo.',
    }
  }
  if (normalized.includes('unavailable') || normalized.includes('network')) {
    return {
      title: 'Backend connection lost',
      guidance: 'The run remains unverified. Restore the live API connection before retrying.',
    }
  }
  return {
    title: 'Agent run stopped safely',
    guidance: 'No containment decision was accepted. Check provider availability and structured output, then retry.',
  }
}

export function ReviewWorkspace({ run, isLoading, error, onReplay }: ReviewWorkspaceProps) {
  const baseline = run?.mode === 'baseline'
  const hasStage = (stage: RunEvent['stage']) => run?.events.some((event) => event.stage === stage) ?? false
  const investigatorVisible = hasStage('investigation')
  const reviewerVisible = baseline || hasStage('review')
  const arbiterVisible = baseline || hasStage('arbitration')
  const policyVisible = hasStage('policy') || hasStage('action') || hasStage('verification') || (!baseline && arbiterVisible && !run?.events.some((event) => event.stage === 'policy'))
  const actionVisible = hasStage('action') || hasStage('verification') || run?.status === 'completed'
  const latestStage = run?.events.at(-1)?.stage
  const progress = run?.status === 'completed' ? 1 : latestStage ? stageProgress[latestStage] : 0

  const comparison = useMemo(() => {
    const investigator = assessmentScope(run?.investigator ?? null)
    const reviewer = assessmentScope(run?.reviewer ?? null)
    return {
      agreed: [...investigator].filter((id) => reviewer.has(id)),
      investigatorOnly: [...investigator].filter((id) => !reviewer.has(id)),
      reviewerOnly: [...reviewer].filter((id) => !investigator.has(id)),
    }
  }, [run])

  if (!run && isLoading) {
    return <section className="review-workspace loading-workspace"><div className="agent-orbit"><span /><i /></div><strong>Starting containment run…</strong><p>Waiting for the first workflow event.</p></section>
  }

  if (error || run?.status === 'failed') {
    const message = error?.message ?? run?.error ?? 'The workflow returned a failed state.'
    const copy = failureCopy(message)
    return <section className="review-workspace error-workspace" role="alert" aria-live="assertive"><AlertOctagon size={22} /><div><strong>{copy.title}</strong><p>{message}</p><small>{copy.guidance}</small></div><button className="secondary-button" onClick={onReplay}><RotateCcw size={14} /> Try again</button></section>
  }

  if (!run) {
    return <section className="review-workspace run-empty-state"><Play size={23} /><div><strong>Analysis is ready</strong><p>Choose FaultCore or baseline, then start a run to stream the agent workflow.</p></div></section>
  }

  return (
    <section className="review-workspace" aria-labelledby="review-heading">
      <header className="review-heading">
        <div>
          <p className="section-kicker"><GitCompareArrows size={14} /> {baseline ? 'Single-agent reference' : 'Independent scope review'}</p>
          <h2 id="review-heading">{baseline ? 'Baseline assessment' : 'Competing assessments'}</h2>
          <p>{baseline ? 'The reference workflow uses one assessment without independent review or arbitration.' : 'Two isolated analyses commit before comparison. The Arbiter resolves only after both are sealed.'}</p>
        </div>
        <div className="replay-control">
          <div><span style={{ width: `${progress * 100}%` }} /></div>
          <button onClick={onReplay} disabled={run.status === 'running'}><RotateCcw size={14} /> {run.status === 'running' ? 'Run in progress' : 'Rerun analysis'}</button>
        </div>
      </header>

      <div className="assessment-grid">
        <AssessmentPanel role="investigator" assessment={run.investigator} visible={investigatorVisible} />
        {baseline ? (
          <section className="assessment-panel bypass-panel" data-role="reviewer"><ShieldCheck size={21} /><strong>Independent review bypassed</strong><p>Baseline mode intentionally uses a single agent so its result can be measured against FaultCore.</p></section>
        ) : <AssessmentPanel role="reviewer" assessment={run.reviewer} visible={reviewerVisible} />}
      </div>

      <section className="comparison-overlay" data-visible={reviewerVisible}>
        <header><GitCompareArrows size={17} /><div><h3>Scope comparison</h3><p>Set-level agreement and disagreement</p></div></header>
        {baseline ? <div className="comparison-locked"><X size={15} /> Comparison is unavailable in single-agent baseline mode</div> : reviewerVisible ? (
          <div className="comparison-columns">
            <div data-kind="agreement"><span><Check size={13} /> Agreed scope</span><div>{comparison.agreed.length ? comparison.agreed.map((id) => <StatusPill tone="cleared" key={id}>{id}</StatusPill>) : <small>No shared lot IDs</small>}</div></div>
            <div data-kind="investigator"><span><Activity size={13} /> Investigator only</span><div>{comparison.investigatorOnly.length ? comparison.investigatorOnly.map((id) => <StatusPill tone="possible" key={id}>{id}</StatusPill>) : <small>None</small>}</div></div>
            <div data-kind="reviewer"><span><ShieldCheck size={13} /> Reviewer only</span><div>{comparison.reviewerOnly.length ? comparison.reviewerOnly.map((id) => <StatusPill tone="possible" key={id}>{id}</StatusPill>) : <small>None</small>}</div></div>
          </div>
        ) : <div className="comparison-locked"><Clock3 size={15} /> Comparison locked until both assessments commit</div>}
      </section>

      <div className="resolution-grid">
        <section className="arbiter-panel" data-visible={arbiterVisible}>
          <header><span><Gavel size={17} /></span><div><h3>Containment Arbiter</h3><p>Independent resolution</p></div>{arbiterVisible && run.arbiter && <StatusPill tone={run.arbiter.decision === 'escalate' ? 'possible' : 'cleared'}>{run.arbiter.decision}</StatusPill>}</header>
          {baseline ? <div className="panel-wait"><X size={16} /><span>Arbitration bypassed in baseline mode</span></div> : !arbiterVisible ? <div className="panel-wait"><Clock3 size={16} /><span>Waiting for both committed assessments</span></div> : run.arbiter ? (
            <div className="arbiter-body">
              <p>{run.arbiter.summary}</p>
              <div className="arbiter-scope"><span>Final proposed scope</span><div>{run.arbiter.final_scope_lot_ids.map((id) => <StatusPill tone="confirmed" key={id}>{id}</StatusPill>)}</div></div>
              {run.arbiter.disagreements.length > 0 && <div className="arbiter-note"><AlertOctagon size={14} /><div><strong>Disagreement resolved</strong><p>{run.arbiter.disagreements.join(' · ')}</p></div></div>}
              {run.arbiter.requested_correction && <div className="correction-note"><RotateCcw size={14} /><div><strong>Requested correction</strong><p>{run.arbiter.requested_correction}</p></div></div>}
            </div>
          ) : <div className="panel-wait"><X size={16} /><span>No Arbiter decision returned</span></div>}
        </section>

        <section className="policy-panel" data-visible={policyVisible}>
          <header><span><ListChecks size={17} /></span><div><h3>Deterministic policy</h3><p>Non-negotiable controls</p></div>{policyVisible && <strong>{run.policy_checks.filter((check) => check.status === 'pass').length}/{run.policy_checks.length} passed</strong>}</header>
          {!policyVisible ? <div className="panel-wait"><Clock3 size={16} /><span>Waiting for scope decision</span></div> : run.policy_checks.length ? (
            <div className="policy-list">{run.policy_checks.map((check, index) => (
              <div className="policy-row" data-status={check.status} key={`${check.id}-${index}`}>
                <span>{check.status === 'pass' ? <Check size={13} /> : check.status === 'fail' ? <X size={13} /> : <AlertOctagon size={13} />}</span>
                <div><strong>{check.name}</strong><p>{check.detail}</p></div><em>{check.status}</em>
              </div>
            ))}</div>
          ) : <div className="panel-wait"><X size={16} /><span>No policy checks returned</span></div>}
        </section>
      </div>

      <section className="event-timeline">
        <header><div><Activity size={16} /><span>Execution event stream</span></div><strong>{run.status === 'completed' ? 'Run complete' : 'Live · polling'}</strong></header>
        <ol>{run.events.map((event) => {
          const Icon = eventIcon[event.stage]
          return <li key={event.id} data-status={event.status}><span><Icon size={13} /></span><div><strong>{event.stage}</strong><p>{event.message}</p></div><time>{new Date(event.timestamp).toLocaleTimeString([], { minute: '2-digit', second: '2-digit' })}</time></li>
        })}</ol>
        {actionVisible && run.actions.length > 0 && <div className="action-strip">{run.actions.map((action) => <div key={action.id}><StatusPill tone={action.status === 'rejected' ? 'possible' : 'held'}>{action.status}</StatusPill><span>{action.type.replaceAll('_', ' ')}</span><small>{action.detail}</small></div>)}</div>}
      </section>
    </section>
  )
}
