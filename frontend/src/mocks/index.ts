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
const startedRuns = new Map<string, Run>()

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
  startedRuns.set(runId, { ...copy(fixture), run_id: runId })
  return { run_id: runId, status: 'running' }
}

export async function getMockRun(runId: string): Promise<Run> {
  const run = startedRuns.get(runId) ?? fixtures.find((fixture) => fixture.run_id === runId)
  if (!run) throw new Error(`No mock run found for ${runId}`)
  return copy(run)
}

export const mockFixtureCount = {
  scenarios: scenarios.length,
  graphs: graphs.size,
  runs: fixtures.length,
}
