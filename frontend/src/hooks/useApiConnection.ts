import { useQuery } from '@tanstack/react-query'
import { api } from '../api'

export type ApiConnectionState = 'mock' | 'checking' | 'connected' | 'unavailable'

export interface ApiConnection {
  state: ApiConnectionState
  label: string
  detail: string
}

export function useApiConnection(): ApiConnection {
  const health = useQuery({
    queryKey: ['api-health'],
    queryFn: api.health,
    enabled: !api.usingMocks,
    retry: 1,
    refetchInterval: (query) => query.state.status === 'error' ? 5_000 : 30_000,
  })

  if (api.usingMocks) {
    return {
      state: 'mock',
      label: 'Demo fixtures',
      detail: 'Explicit local demo mode · VITE_USE_MOCKS=true',
    }
  }
  if (health.isPending) {
    return {
      state: 'checking',
      label: 'Checking API',
      detail: `Connecting to ${api.apiUrl}`,
    }
  }
  if (health.isError) {
    return {
      state: 'unavailable',
      label: 'API unavailable',
      detail: health.error.message,
    }
  }
  return {
    state: 'connected',
    label: 'Live API connected',
    detail: `Connected to ${api.apiUrl}`,
  }
}
