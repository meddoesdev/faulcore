import {
  ArrowRight, Beaker, Boxes, CircleAlert, Gavel, GitCompareArrows,
  Network, Search, ShieldAlert, ShieldCheck, Sparkles, Waypoints,
} from 'lucide-react'
import { useScenarios } from '../hooks/useScenarios'
import type { Scenario, ScenarioId } from '../types'

interface IncidentSelectorProps { onSelect: (scenarioId: ScenarioId) => void }

const scenarioIcon = {
  'clean-trace-01': Beaker,
  'over-recall-01': Network,
  'broken-trace-01': ShieldAlert,
} satisfies Record<ScenarioId, typeof Beaker>

const difficultyCopy: Record<Scenario['difficulty'], string> = {
  standard: 'Standard', adversarial: 'Adversarial', critical: 'Critical',
}

export function IncidentSelector({ onSelect }: IncidentSelectorProps) {
  const scenarios = useScenarios()
  const scrollToScenarios = () => document.getElementById('scenario-library')?.scrollIntoView({ behavior: 'smooth' })

  return (
    <div className="screen-stack incident-selector">
      <section className="landing-hero">
        <div className="landing-orbit orbit-one" aria-hidden="true" />
        <div className="landing-orbit orbit-two" aria-hidden="true" />
        <div className="landing-constellation" aria-hidden="true"><span /><span /><span /><span /><span /><span /></div>
        <div className="hero-copy">
          <p className="eyebrow"><Sparkles size={14} /> Evidence-led containment</p>
          <h1>Contain what matters.<br /><em>Preserve the rest.</em></h1>
          <p>Two independent analyses. One defensible boundary. Every action verified.</p>
          <div className="hero-actions">
            <button className="primary-button" onClick={scrollToScenarios}>Choose an incident <ArrowRight size={16} /></button>
            <span><ShieldCheck size={15} /> Deterministic policy remains in control</span>
          </div>
        </div>
        <div className="hero-proof" aria-label="arivu.ai operating principles">
          <span><strong>01</strong> Independent review</span>
          <span><strong>02</strong> Policy-gated action</span>
          <span><strong>03</strong> Verified outcomes</span>
        </div>
      </section>

      <section className="scenario-library" id="scenario-library">
        <div className="section-intro">
          <p className="section-kicker"><CircleAlert size={14} /> Scenario library</p>
          <h2>Choose the evidence pattern.</h2>
          <p>Each scenario resets to the same initial state, so every containment decision can be compared fairly.</p>
        </div>
        {scenarios.isPending && <div className="scenario-grid" aria-label="Loading scenarios">{[0, 1, 2].map((item) => <div className="scenario-card skeleton-card" key={item} />)}</div>}
        {scenarios.isError && <div className="error-panel" role="alert"><CircleAlert size={20} /><div><strong>Scenario feed unavailable</strong><p>{scenarios.error.message}</p></div></div>}
        {scenarios.data && (
          <div className="scenario-grid">
            {scenarios.data.map((scenario, index) => {
              const Icon = scenarioIcon[scenario.id]
              return (
                <article className="scenario-card" key={scenario.id} data-difficulty={scenario.difficulty}>
                  <div className="card-topline"><span className="scenario-number">0{index + 1}</span><span className="difficulty-badge">{difficultyCopy[scenario.difficulty]}</span></div>
                  <div className="scenario-icon"><Icon size={23} /></div>
                  <div className="scenario-copy"><p className="mono-label">{scenario.id}</p><h3>{scenario.name}</h3><p>{scenario.description}</p></div>
                  <dl className="scenario-facts"><div><dt>Alert type</dt><dd>{scenario.alert_type}</dd></div><div><dt>Product</dt><dd>{scenario.product}</dd></div></dl>
                  <button className="scenario-link" onClick={() => onSelect(scenario.id)}>Open incident <ArrowRight size={16} /></button>
                </article>
              )
            })}
          </div>
        )}
      </section>

      <section className="workflow-story">
        <div className="section-intro compact"><p className="section-kicker"><Boxes size={14} /> How arivu.ai works</p><h2>A defensible path from signal to release.</h2></div>
        <ol>
          <li><span><CircleAlert size={17} /></span><strong>Ingest</strong><p>Load the incident and trace evidence.</p></li>
          <li><span><Search size={17} /></span><strong>Investigate</strong><p>Reconstruct the likely exposure path.</p></li>
          <li><span><GitCompareArrows size={17} /></span><strong>Review</strong><p>Run a sealed, independent assessment.</p></li>
          <li><span><Gavel size={17} /></span><strong>Arbitrate</strong><p>Resolve disagreement with evidence.</p></li>
          <li><span><Waypoints size={17} /></span><strong>Contain</strong><p>Apply policy-gated operational actions.</p></li>
          <li><span><ShieldCheck size={17} /></span><strong>Verify</strong><p>Measure the real containment outcome.</p></li>
        </ol>
      </section>
    </div>
  )
}
