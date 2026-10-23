import { AlertTriangle, Check, CheckCircle2, Clock3, Gauge, PackageCheck, ShieldCheck, X } from 'lucide-react'
import type { Run } from '../../types'
import { StatusPill } from '../StatusPill'

interface VerificationPanelProps {
  run: Run | null
}

const percent = (value: number) => `${Math.round(value * 100)}%`

export function VerificationPanel({ run }: VerificationPanelProps) {
  if (!run) {
    return <section className="verification-panel verification-wait"><ShieldCheck size={22} /><div><strong>Verification pending</strong><p>Outcome metrics unlock after a containment run completes.</p></div></section>
  }

  if (run.status === 'running') {
    return <section className="verification-panel verification-wait" data-active="true"><div className="agent-orbit"><span /><i /></div><div><strong>Verification queued</strong><p>The workflow is still collecting decisions and containment actions.</p></div></section>
  }

  if (run.status === 'failed') {
    return <section className="verification-panel verification-wait" data-failed="true"><AlertTriangle size={22} /><div><strong>Verification unavailable</strong><p>{run.error ?? 'The run failed before outcomes could be verified.'}</p></div></section>
  }

  if (!run.verification || !run.metrics) {
    return <section className="verification-panel verification-wait"><AlertTriangle size={22} /><div><strong>No verification payload</strong><p>The run completed without the required outcome metrics.</p></div></section>
  }

  const { verification, metrics } = run
  const passedChecks = verification.checks.filter((check) => check.passed).length

  return (
    <section className="verification-panel" aria-labelledby="verification-heading">
      <header className="verification-heading">
        <div><p className="section-kicker"><CheckCircle2 size={14} /> Outcome verification</p><h2 id="verification-heading">Containment effectiveness</h2><p>Measured against the known scenario outcome after the run completed.</p></div>
        <StatusPill tone={verification.residual_risk === 'none' ? 'cleared' : verification.residual_risk === 'high' ? 'confirmed' : 'possible'}>{verification.residual_risk} residual risk</StatusPill>
      </header>

      <div className="verification-metrics">
        <article><span><PackageCheck size={15} /> Affected units</span><strong>{verification.affected_units.toLocaleString()}</strong><small>Known scenario total</small></article>
        <article><span><ShieldCheck size={15} /> Contained</span><strong>{verification.contained_units.toLocaleString()}</strong><small>{verification.missed_units.toLocaleString()} units missed</small></article>
        <article data-warning={verification.safe_units_held > 0}><span><AlertTriangle size={15} /> Safe units held</span><strong>{verification.safe_units_held.toLocaleString()}</strong><small>{verification.safe_units_available.toLocaleString()} remained available</small></article>
        <article><span><Gauge size={15} /> Time to contain</span><strong>{metrics.time_to_containment_seconds}s</strong><small>End-to-end workflow</small></article>
      </div>

      <div className="effectiveness-grid">
        <div><span>Containment precision</span><strong>{percent(metrics.containment_precision)}</strong><i><b style={{ width: percent(metrics.containment_precision) }} /></i></div>
        <div><span>Containment recall</span><strong>{percent(metrics.containment_recall)}</strong><i><b style={{ width: percent(metrics.containment_recall) }} /></i></div>
        <div><span>Safe inventory preserved</span><strong>{percent(metrics.safe_inventory_preserved)}</strong><i><b style={{ width: percent(metrics.safe_inventory_preserved) }} /></i></div>
      </div>

      <div className="verification-checks">
        <header><span>Verification checks</span><strong>{passedChecks}/{verification.checks.length} passed</strong></header>
        {verification.checks.map((check) => <div key={check.name} data-passed={check.passed}><span>{check.passed ? <Check size={13} /> : <X size={13} />}</span><div><strong>{check.name}</strong><p>{check.detail}</p></div></div>)}
        {verification.checks.length === 0 && <p className="empty-copy">No verification checks returned.</p>}
      </div>
      <footer><Clock3 size={13} /> Under-containment {percent(metrics.under_containment_rate)} · Over-containment {percent(metrics.over_containment_rate)}</footer>
    </section>
  )
}
