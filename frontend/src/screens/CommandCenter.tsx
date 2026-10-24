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
  Play,
  Route,
  ShieldAlert,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { StatusPill } from '../components/StatusPill'
import { ComparisonReport } from '../components/comparison/ComparisonReport'
import { ExposureGraph } from '../components/graph/ExposureGraph'
import { ReviewWorkspace } from '../components/review/ReviewWorkspace'
import { VerificationPanel } from '../components/verification/VerificationPanel'
import { useGraph } from '../hooks/useGraph'
import { useRunController } from '../hooks/useRunController'
import type { GraphNode, Run, RunMode, Scenario } from '../types'

interface CommandCenterProps {
  scenario: Scenario
  onBack: () => void
}

function exposureCount(nodes: GraphNode[], exposure: GraphNode['exposure']) {
  return nodes.filter((node) => node.exposure === exposure).length
}

export function CommandCenter({ scenario, onBack }: CommandCenterProps) {
  const [mode, setMode] = useState<RunMode>('faultcore')
  const [completedRuns, setCompletedRuns] = useState<Partial<Record<RunMode, Run>>>({})
  const graph = useGraph(scenario.id)
  const runController = useRunController(scenario.id, mode)
  const run = runController.run
  const nodes = graph.data?.nodes ?? []
  const exposedNodes = nodes.filter((node) => node.exposure !== 'excluded')
  const isBrokenTrace = scenario.id === 'broken-trace-01'
  const isRunActive = runController.isStarting || run?.status === 'running'
  const hasStage = (stage: 'investigation' | 'review' | 'arbitration' | 'policy') => run?.events.some((event) => event.stage === stage) ?? false
  const runLabel = runController.isStarting ? 'Starting…' : run?.status === 'running' ? 'Run in progress' : run?.status === 'completed' ? 'Run again' : 'Run containment'

  useEffect(() => {
    if (run?.status === 'completed' && run.metrics && run.verification) {
      setCompletedRuns((current) => ({ ...current, [run.mode]: run }))
    }
  }, [run])

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
          <div className="mode-toggle" aria-label="Run mode">
            <button data-active={mode === 'faultcore'} disabled={isRunActive} onClick={() => setMode('faultcore')}>FaultCore</button>
            <button data-active={mode === 'baseline'} disabled={isRunActive} onClick={() => setMode('baseline')}>Baseline</button>
          </div>
          <button className="primary-button run-button" disabled={isRunActive} onClick={runController.start}><Play size={14} /> {runLabel}</button>
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
        <div><span className="status-icon"><Clock3 size={16} /></span><span>Run mode</span><strong>{mode === 'faultcore' ? 'FaultCore agents' : 'Single-agent baseline'}</strong></div>
        <div><span className="status-icon"><ShieldAlert size={16} /></span><span>Containment</span><strong>{runController.error ? 'Run error' : run?.status === 'completed' ? 'Verified' : run?.status === 'running' || runController.isStarting ? 'In progress' : isBrokenTrace ? 'Review needed' : 'Not started'}</strong></div>
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
            <li data-state={hasStage('investigation') ? 'complete' : isRunActive ? 'active' : 'pending'}><span>{hasStage('investigation') ? <Check size={13} /> : '2'}</span><div><strong>Trace investigation</strong><small>{hasStage('investigation') ? 'Assessment committed' : isRunActive ? 'Reconstructing scope' : 'Ready to initialise'}</small></div></li>
            <li data-state={mode === 'baseline' ? (hasStage('investigation') ? 'complete' : 'pending') : hasStage('review') ? 'complete' : hasStage('investigation') ? 'active' : 'pending'}><span>{mode === 'baseline' || hasStage('review') ? <Check size={13} /> : '3'}</span><div><strong>Independent review</strong><small>{mode === 'baseline' ? 'Bypassed in baseline mode' : hasStage('review') ? 'Blind review committed' : 'Waiting for investigation'}</small></div></li>
            <li data-state={hasStage('policy') || run?.status === 'completed' ? 'complete' : hasStage('arbitration') || (mode === 'baseline' && hasStage('investigation')) ? 'active' : 'pending'}><span>{hasStage('policy') || run?.status === 'completed' ? <Check size={13} /> : '4'}</span><div><strong>Arbitration + policy</strong><small>{run?.status === 'completed' ? 'Policy checks complete' : mode === 'baseline' ? 'Arbiter bypassed; policy remains' : hasStage('arbitration') ? 'Resolving against policy' : 'Waiting for assessments'}</small></div></li>
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

      <ReviewWorkspace run={run} isLoading={runController.isStarting || runController.isPolling} error={runController.error} onReplay={runController.start} />
      <VerificationPanel run={run} />
      <ComparisonReport scenario={scenario} runs={completedRuns} onSelectMode={setMode} />
    </div>
  )
}
