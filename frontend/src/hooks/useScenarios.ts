import { useQuery } from '@tanstack/react-query'
import { api } from '../api'

export function useScenarios() {
  return useQuery({
    queryKey: ['scenarios'],
    queryFn: api.listScenarios,
  })
}

