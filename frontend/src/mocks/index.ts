import brokenGraphJson from './graphs/broken-trace-01.json'
import cleanGraphJson from './graphs/clean-trace-01.json'
import overRecallGraphJson from './graphs/over-recall-01.json'
import runsJson from './runs.json'
import scenariosJson from './scenarios.json'
import type {
  GraphData,
  Run,
  Scenario,
  ScenarioId,
  StartRunRequest,
  StartRunResponse,
} from '../types'

const scenarios = scenariosJson as unknown as Scenario[]
const graphs = new Map<ScenarioId, GraphData>(
  [cleanGraphJson, overRecallGraphJson, brokenGraphJson].map((graph) => {
    const typedGraph = graph as unknown as GraphData
    return [typedGraph.scenario_id, typedGraph]
  }),
)
const fixtures = runsJson as unknown as Run[]
interface StartedRun {
  fixture: Run
  startedAt: number
}

const startedRuns = new Map<string, StartedRun>()
const mockEventIntervalMs = 620

const copy = <T>(value: T): T => structuredClone(value)

export async function listMockScenarios(): Promise<Scenario[]> {
  return copy(scenarios)
}

export async function getMockGraph(scenarioId: ScenarioId): Promise<GraphData> {
  const graph = graphs.get(scenarioId)
  if (!graph) throw new Error(`No mock graph found for ${scenarioId}`)
  return copy(graph)
}

export async function startMockRun(request: StartRunRequest): Promise<StartRunResponse> {
  const fixture = fixtures.find(
    (run) => run.scenario_id === request.scenario_id && run.mode === request.mode,
  )
  if (!fixture) throw new Error(`No mock run found for ${request.scenario_id}/${request.mode}`)

  const runId = `mock-${request.scenario_id}-${request.mode}-${Date.now()}`
  startedRuns.set(runId, {
    fixture: { ...copy(fixture), run_id: runId },
    startedAt: Date.now(),
  })
  return { run_id: runId, status: 'running' }
}

export async function getMockRun(runId: string): Promise<Run> {
  const started = startedRuns.get(runId)
  if (!started) {
    const fixture = fixtures.find((candidate) => candidate.run_id === runId)
    if (!fixture) throw new Error(`No mock run found for ${runId}`)
    return copy(fixture)
  }

  const { fixture, startedAt } = started
  const visibleCount = Math.min(
    fixture.events.length,
    Math.max(1, Math.floor((Date.now() - startedAt) / mockEventIntervalMs) + 1),
  )
  const events = fixture.events.slice(0, visibleCount)
  const completed = visibleCount === fixture.events.length
  const hasStage = (...stages: Run['events'][number]['stage'][]) =>
    events.some((event) => stages.includes(event.stage))

  return copy({
    ...fixture,
    status: completed ? fixture.status : 'running',
    events,
    investigator: hasStage('investigation') ? fixture.investigator : null,
    reviewer: hasStage('review') ? fixture.reviewer : null,
    arbiter: hasStage('arbitration') ? fixture.arbiter : null,
    policy_checks: completed || hasStage('policy', 'action', 'verification') ? fixture.policy_checks : [],
    actions: completed || hasStage('action', 'verification') ? fixture.actions : [],
    verification: completed ? fixture.verification : null,
    metrics: completed ? fixture.metrics : null,
    error: completed ? fixture.error : null,
  })
}

export const mockFixtureCount = {
  scenarios: scenarios.length,
  graphs: graphs.size,
  runs: fixtures.length,
}
