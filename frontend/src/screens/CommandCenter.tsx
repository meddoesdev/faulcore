import {
  AlertTriangle,
  ArrowLeft,
  ArrowUpRight,
  Box,
  Check,
  ChevronRight,
  Clock3,
  MapPin,
  Network,
  PackageCheck,
  Route,
  ShieldAlert,
} from 'lucide-react'
import { StatusPill } from '../components/StatusPill'
import { ExposureGraph } from '../components/graph/ExposureGraph'
import { ReviewWorkspace } from '../components/review/ReviewWorkspace'
import { useGraph } from '../hooks/useGraph'
import type { GraphNode, Scenario } from '../types'

interface CommandCenterProps {
  scenario: Scenario
  onBack: () => void
}

function exposureCount(nodes: GraphNode[], exposure: GraphNode['exposure']) {
  return nodes.filter((node) => node.exposure === exposure).length
}

export function CommandCenter({ scenario, onBack }: CommandCenterProps) {
  const graph = useGraph(scenario.id)
  const nodes = graph.data?.nodes ?? []
  const exposedNodes = nodes.filter((node) => node.exposure !== 'excluded')
  const isBrokenTrace = scenario.id === 'broken-trace-01'

  return (
    <div className="screen-stack command-center">
      <section className="command-heading">
        <div>
          <button className="text-button" onClick={onBack}><ArrowLeft size={15} /> All incidents</button>
          <p className="section-kicker"><span className="live-pulse" /> Active command centre</p>
          <h1>{scenario.name}</h1>
          <p className="incident-id">INCIDENT / {scenario.id.toUpperCase()}</p>
        </div>
        <div className="command-actions">
          <button className="secondary-button">View source data <ArrowUpRight size={15} /></button>
          <button className="primary-button" disabled>Run containment</button>
          <span className="phase-note">Enabled in Phase 4</span>
        </div>
      </section>

      <section className="alert-banner" data-severity={isBrokenTrace ? 'critical' : 'warning'}>
        <div className="alert-icon"><AlertTriangle size={21} /></div>
        <div className="alert-copy">
          <span>Incoming alert</span>
          <strong>{scenario.alert_type}</strong>
          <p>{scenario.description}</p>
        </div>
        <div className="alert-product">
          <span>Product</span>
          <strong>{scenario.product}</strong>
        </div>
        <StatusPill tone={isBrokenTrace ? 'possible' : 'confirmed'}>
          {isBrokenTrace ? 'Evidence gap' : 'Triage required'}
        </StatusPill>
      </section>

      <section className="status-strip" aria-label="Incident status">
        <div><span className="status-icon"><Route size={16} /></span><span>Trace state</span><strong>{graph.isPending ? 'Loading' : 'Evidence loaded'}</strong></div>
        <div><span className="status-icon"><Network size={16} /></span><span>Exposure nodes</span><strong>{graph.data ? exposedNodes.length.toString().padStart(2, '0') : '—'}</strong></div>
        <div><span className="status-icon"><Clock3 size={16} /></span><span>Response clock</span><strong>00:00:00</strong></div>
        <div><span className="status-icon"><ShieldAlert size={16} /></span><span>Containment</span><strong>{isBrokenTrace ? 'Review needed' : 'Not started'}</strong></div>
      </section>

      {graph.isError && <div className="error-panel" role="alert"><AlertTriangle size={20} /><div><strong>Graph fixture unavailable</strong><p>{graph.error.message}</p></div></div>}

      <div className="command-grid">
        <section className="panel exposure-panel">
          <header className="panel-header">
            <div><span className="panel-index">01</span><div><h2>Exposure overview</h2><p>Supply-chain evidence snapshot</p></div></div>
            <span className="panel-hint">Select a node <ChevronRight size={15} /></span>
          </header>

          <div className="exposure-placeholder">
            {graph.data ? <ExposureGraph graph={graph.data} /> : <div className="graph-loading">Preparing exposure topology…</div>}
          </div>

          <div className="exposure-legend">
            <span><i data-color="confirmed" /> Confirmed <strong>{exposureCount(nodes, 'confirmed')}</strong></span>
            <span><i data-color="possible" /> Possible <strong>{exposureCount(nodes, 'possible')}</strong></span>
            <span><i data-color="excluded" /> Excluded <strong>{exposureCount(nodes, 'excluded')}</strong></span>
            <span><i data-color="held" /> Held</span>
            <span><i data-color="cleared" /> Cleared</span>
          </div>
        </section>

        <section className="panel scope-panel">
          <header className="panel-header compact">
            <div><span className="panel-index">02</span><div><h2>Potential scope</h2><p>Affected and possible lots</p></div></div>
          </header>
          <div className="scope-list">
            {graph.isPending && <p className="muted-copy">Loading inventory positions…</p>}
            {exposedNodes.slice(0, 5).map((node) => (
              <div className="scope-row" key={node.id}>
                <span className="node-glyph"><Box size={15} /></span>
                <div><strong>{node.label}</strong><span>{node.id}</span></div>
                <StatusPill tone={node.exposure}>{node.exposure}</StatusPill>
              </div>
            ))}
          </div>
        </section>

        <section className="panel progress-panel">
          <header className="panel-header compact">
            <div><span className="panel-index">03</span><div><h2>Investigation progress</h2><p>Agent workflow readiness</p></div></div>
          </header>
          <ol className="progress-list">
            <li data-state="complete"><span><Check size={13} /></span><div><strong>Alert ingested</strong><small>Scenario evidence available</small></div></li>
            <li data-state="active"><span>2</span><div><strong>Trace investigation</strong><small>Ready to initialise</small></div></li>
            <li data-state="pending"><span>3</span><div><strong>Independent review</strong><small>Waiting for investigation</small></div></li>
            <li data-state="pending"><span>4</span><div><strong>Arbitration + policy</strong><small>Waiting for assessments</small></div></li>
          </ol>
        </section>

        <section className="panel containment-panel">
          <header className="panel-header compact">
            <div><span className="panel-index">04</span><div><h2>Containment status</h2><p>Operational action readiness</p></div></div>
          </header>
          <div className="containment-state">
            <div className="containment-symbol" data-warning={isBrokenTrace}><PackageCheck size={26} /></div>
            <div>
              <span>{isBrokenTrace ? 'HUMAN REVIEW EXPECTED' : 'AWAITING ANALYSIS'}</span>
              <strong>{isBrokenTrace ? 'Traceability gap detected' : 'No holds placed'}</strong>
              <p>{isBrokenTrace ? 'The missing relabelling map may require a broader temporary hold.' : 'Containment actions remain locked until policy validation.'}</p>
            </div>
          </div>
          <div className="containment-footer"><MapPin size={14} /><span>{nodes.filter((node) => node.type === 'store' || node.type === 'distribution_center').length} destination groups in evidence</span></div>
        </section>
      </div>

      <ReviewWorkspace scenarioId={scenario.id} />
    </div>
  )
}
