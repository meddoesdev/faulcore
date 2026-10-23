import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import type { ScenarioId } from '../types'

export function useGraph(scenarioId: ScenarioId) {
  return useQuery({
    queryKey: ['scenario-graph', scenarioId],
    queryFn: () => api.getGraph(scenarioId),
  })
}

