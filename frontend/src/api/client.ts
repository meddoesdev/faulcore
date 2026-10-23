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

const useMocks = import.meta.env.VITE_USE_MOCKS !== 'false'
const apiUrl = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

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

export const api = {
  usingMocks: useMocks,

  listScenarios(): Promise<Scenario[]> {
    return useMocks ? listMockScenarios() : request('/api/scenarios')
  },

  getGraph(scenarioId: ScenarioId): Promise<GraphData> {
    return useMocks
      ? getMockGraph(scenarioId)
      : request(`/api/scenarios/${encodeURIComponent(scenarioId)}/graph`)
  },

  startRun(body: StartRunRequest): Promise<StartRunResponse> {
    return useMocks
      ? startMockRun(body)
      : request('/api/runs', { method: 'POST', body: JSON.stringify(body) })
  },

  getRun(runId: string): Promise<Run> {
    return useMocks ? getMockRun(runId) : request(`/api/runs/${encodeURIComponent(runId)}`)
  },
}

