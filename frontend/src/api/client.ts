import {
  getMockGraph,
  getMockRun,
  listMockScenarios,
  startMockRun,
} from '../mocks'
import type {
  GraphData,
  Run,
  Scenario,
  ScenarioId,
  StartRunRequest,
  StartRunResponse,
} from '../types'

const useMocks = import.meta.env.VITE_USE_MOCKS === 'true'
const apiUrl = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')
let liveApiUnavailable = false

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`RecallScope API ${response.status}: ${detail || response.statusText}`)
  }
  return response.json() as Promise<T>
}

async function withNetworkFallback<T>(live: () => Promise<T>, fallback: () => Promise<T>): Promise<T> {
  if (useMocks || liveApiUnavailable) return fallback()
  try {
    return await live()
  } catch (error) {
    // HTTP responses carry meaningful contract errors and must remain visible.
    // Only a transport failure activates the deterministic local experience.
    if (!(error instanceof TypeError)) throw error
    liveApiUnavailable = true
    return fallback()
  }
}

export const api = {
  usingMocks: useMocks,

  listScenarios(): Promise<Scenario[]> {
    return withNetworkFallback(() => request('/api/scenarios'), listMockScenarios)
  },

  getGraph(scenarioId: ScenarioId): Promise<GraphData> {
    return withNetworkFallback(
      () => request(`/api/scenarios/${encodeURIComponent(scenarioId)}/graph`),
      () => getMockGraph(scenarioId),
    )
  },

  startRun(body: StartRunRequest): Promise<StartRunResponse> {
    return withNetworkFallback(
      () => request('/api/runs', { method: 'POST', body: JSON.stringify(body) }),
      () => startMockRun(body),
    )
  },

  getRun(runId: string): Promise<Run> {
    return withNetworkFallback(
      () => request(`/api/runs/${encodeURIComponent(runId)}`),
      () => getMockRun(runId),
    )
  },
}
