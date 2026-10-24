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

interface ApiErrorPayload {
  code?: string
  message?: string
  request_id?: string
}

export class RecallScopeApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
    readonly code: string,
    readonly requestId?: string,
  ) {
    super(message)
    this.name = 'RecallScopeApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${apiUrl}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new RecallScopeApiError(
      `Live API unavailable at ${apiUrl}. Start the backend or explicitly enable demo fixtures with VITE_USE_MOCKS=true.`,
      null,
      'network_unavailable',
    )
  }

  if (!response.ok) {
    let payload: ApiErrorPayload = {}
    try {
      payload = await response.json() as ApiErrorPayload
    } catch {
      // Non-JSON upstream errors still retain a safe status-level message.
    }
    throw new RecallScopeApiError(
      payload.message || `Live API request failed with status ${response.status}.`,
      response.status,
      payload.code || 'api_error',
      payload.request_id,
    )
  }
  return response.json() as Promise<T>
}

export const api = {
  usingMocks: useMocks,
  apiUrl,

  health(): Promise<{ status: string }> {
    return useMocks ? Promise.resolve({ status: 'mock' }) : request('/health')
  },

  listScenarios(): Promise<Scenario[]> {
    return useMocks ? listMockScenarios() : request('/api/scenarios')
  },

  getGraph(scenarioId: ScenarioId): Promise<GraphData> {
    return useMocks ? getMockGraph(scenarioId) : request(`/api/scenarios/${encodeURIComponent(scenarioId)}/graph`)
  },

  startRun(body: StartRunRequest): Promise<StartRunResponse> {
    return useMocks ? startMockRun(body) : request('/api/runs', { method: 'POST', body: JSON.stringify(body) })
  },

  getRun(runId: string): Promise<Run> {
    return useMocks ? getMockRun(runId) : request(`/api/runs/${encodeURIComponent(runId)}`)
  },
}
