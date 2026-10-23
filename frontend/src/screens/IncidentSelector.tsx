import {
  ArrowRight,
  Beaker,
  Boxes,
  CircleAlert,
  Network,
  ShieldAlert,
} from 'lucide-react'
import { useScenarios } from '../hooks/useScenarios'
import type { Scenario, ScenarioId } from '../types'

interface IncidentSelectorProps {
  onSelect: (scenarioId: ScenarioId) => void
}

const scenarioIcon = {
  'clean-trace-01': Beaker,
  'over-recall-01': Network,
  'broken-trace-01': ShieldAlert,
} satisfies Record<ScenarioId, typeof Beaker>

const difficultyCopy: Record<Scenario['difficulty'], string> = {
  standard: 'Standard',
  adversarial: 'Adversarial',
  critical: 'Critical',
}

export function IncidentSelector({ onSelect }: IncidentSelectorProps) {
  const scenarios = useScenarios()

  return (
    <div className="screen-stack incident-selector">
      <section className="page-heading">
        <div>
          <p className="section-kicker"><CircleAlert size={14} /> Incident intake</p>
          <h1>Select an active incident</h1>
          <p>Load a deterministic supply-chain scenario into the containment command centre.</p>
        </div>
        <div className="heading-metrics" aria-label="Scenario fixture summary">
          <div><strong>03</strong><span>Seeded incidents</span></div>
          <div><strong>02</strong><span>Run modes</span></div>
          <div><strong>100%</strong><span>Repeatable</span></div>
        </div>
      </section>

      <div className="section-label-row">
        <h2>Scenario library</h2>
        <span>Choose one incident to initialise</span>
      </div>

      {scenarios.isPending && (
        <div className="scenario-grid" aria-label="Loading scenarios">
          {[0, 1, 2].map((item) => <div className="scenario-card skeleton-card" key={item} />)}
        </div>
      )}

      {scenarios.isError && (
        <div className="error-panel" role="alert">
          <CircleAlert size={20} />
          <div><strong>Scenario feed unavailable</strong><p>{scenarios.error.message}</p></div>
        </div>
      )}

      {scenarios.data && (
        <div className="scenario-grid">
          {scenarios.data.map((scenario, index) => {
            const Icon = scenarioIcon[scenario.id]
            return (
              <article className="scenario-card" key={scenario.id} data-difficulty={scenario.difficulty}>
                <div className="card-topline">
                  <span className="scenario-number">0{index + 1}</span>
                  <span className="difficulty-badge">{difficultyCopy[scenario.difficulty]}</span>
                </div>
                <div className="scenario-icon"><Icon size={23} /></div>
                <div className="scenario-copy">
                  <p className="mono-label">{scenario.id}</p>
                  <h3>{scenario.name}</h3>
                  <p>{scenario.description}</p>
                </div>
                <dl className="scenario-facts">
                  <div><dt>Alert type</dt><dd>{scenario.alert_type}</dd></div>
                  <div><dt>Product</dt><dd>{scenario.product}</dd></div>
                </dl>
                <button className="primary-button" onClick={() => onSelect(scenario.id)}>
                  Open incident <ArrowRight size={16} />
                </button>
              </article>
            )
          })}
        </div>
      )}

      <aside className="workflow-note">
        <Boxes size={19} />
        <div>
          <strong>Controlled simulation</strong>
          <span>All scenarios reset to the same initial state. Hidden ground truth remains isolated from agents.</span>
        </div>
      </aside>
    </div>
  )
}

