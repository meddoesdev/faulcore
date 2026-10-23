import {
  Activity,
  AlertOctagon,
  Check,
  CheckCircle2,
  CircleAlert,
  Clock3,
  Gavel,
  GitCompareArrows,
  ListChecks,
  Play,
  RotateCcw,
  ShieldCheck,
  X,
} from 'lucide-react'
import { useMemo } from 'react'
import { useRunReplay } from '../../hooks/useRunReplay'
import type { AgentAssessment, RunEvent, ScenarioId } from '../../types'
import { StatusPill } from '../StatusPill'
import { AssessmentPanel } from './AssessmentPanel'

interface ReviewWorkspaceProps {
  scenarioId: ScenarioId
}

function assessmentScope(assessment: AgentAssessment | null) {
  return new Set([...(assessment?.affected_lot_ids ?? []), ...(assessment?.possibly_affected_lot_ids ?? [])])
}

const eventIcon: Record<RunEvent['stage'], typeof Activity> = {
  alert: CircleAlert,
  investigation: Activity,
  review: ShieldCheck,
  arbitration: Gavel,
  policy: ListChecks,
  action: Play,
  verification: CheckCircle2,
}

export function ReviewWorkspace({ scenarioId }: ReviewWorkspaceProps) {
  const replay = useRunReplay(scenarioId)
  const run = replay.run
  const investigatorVisible = replay.hasVisibleStage('investigation')
  const reviewerVisible = replay.hasVisibleStage('review')
  const arbiterVisible = replay.hasVisibleStage('arbitration')
  const policyVisible = replay.hasVisibleStage('policy') || replay.hasVisibleStage('action') || replay.hasVisibleStage('verification') || (arbiterVisible && !run?.events.some((event) => event.stage === 'policy'))
  const actionVisible = replay.hasVisibleStage('action') || replay.hasVisibleStage('verification')

  const comparison = useMemo(() => {
    const investigator = assessmentScope(run?.investigator ?? null)
    const reviewer = assessmentScope(run?.reviewer ?? null)
    return {
      agreed: [...investigator].filter((id) => reviewer.has(id)),
      investigatorOnly: [...investigator].filter((id) => !reviewer.has(id)),
      reviewerOnly: [...reviewer].filter((id) => !investigator.has(id)),
    }
  }, [run])

  if (replay.isLoading) {
    return <section className="review-workspace loading-workspace"><div className="agent-orbit"><span /><i /></div><strong>Loading completed mock run…</strong><p>Preparing independent assessments and event history.</p></section>
  }

  if (replay.error || !run) {
    return <section className="review-workspace error-workspace"><AlertOctagon size={22} /><div><strong>Review workspace unavailable</strong><p>{replay.error?.message ?? 'No completed mock run was found.'}</p></div></section>
  }

  return (
    <section className="review-workspace" aria-labelledby="review-heading">
      <header className="review-heading">
        <div>
          <p className="section-kicker"><GitCompareArrows size={14} /> Independent scope review</p>
          <h2 id="review-heading">Competing assessments</h2>
          <p>Two isolated analyses commit before comparison. The Arbiter resolves only after both are sealed.</p>
        </div>
        <div className="replay-control">
          <div><span style={{ width: `${replay.progress * 100}%` }} /></div>
          <button onClick={replay.replay}><RotateCcw size={14} /> Replay analysis</button>
        </div>
      </header>

      <div className="assessment-grid">
        <AssessmentPanel role="investigator" assessment={run.investigator} visible={investigatorVisible} />
        <AssessmentPanel role="reviewer" assessment={run.reviewer} visible={reviewerVisible} />
      </div>

      <section className="comparison-overlay" data-visible={reviewerVisible}>
        <header><GitCompareArrows size={17} /><div><h3>Scope comparison</h3><p>Set-level agreement and disagreement</p></div></header>
        {reviewerVisible ? (
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
          {!arbiterVisible ? <div className="panel-wait"><Clock3 size={16} /><span>Waiting for both committed assessments</span></div> : run.arbiter ? (
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
          {!policyVisible ? <div className="panel-wait"><Clock3 size={16} /><span>Waiting for Arbiter decision</span></div> : run.policy_checks.length ? (
            <div className="policy-list">{run.policy_checks.map((check) => (
              <div className="policy-row" data-status={check.status} key={check.id}>
                <span>{check.status === 'pass' ? <Check size={13} /> : check.status === 'fail' ? <X size={13} /> : <AlertOctagon size={13} />}</span>
                <div><strong>{check.name}</strong><p>{check.detail}</p></div>
                <em>{check.status}</em>
              </div>
            ))}</div>
          ) : <div className="panel-wait"><X size={16} /><span>No policy checks returned</span></div>}
        </section>
      </div>

      <section className="event-timeline">
        <header><div><Activity size={16} /><span>Execution event stream</span></div><strong>{replay.isComplete ? 'Replay complete' : 'Live replay'}</strong></header>
        <ol>
          {replay.visibleEvents.map((event) => {
            const Icon = eventIcon[event.stage]
            return <li key={event.id} data-status={event.status}><span><Icon size={13} /></span><div><strong>{event.stage}</strong><p>{event.message}</p></div><time>{new Date(event.timestamp).toLocaleTimeString([], { minute: '2-digit', second: '2-digit' })}</time></li>
          })}
        </ol>
        {actionVisible && run.actions.length > 0 && <div className="action-strip">{run.actions.map((action) => <div key={action.id}><StatusPill tone={action.status === 'rejected' ? 'possible' : 'held'}>{action.status}</StatusPill><span>{action.type.replaceAll('_', ' ')}</span><small>{action.detail}</small></div>)}</div>}
      </section>
    </section>
  )
}

