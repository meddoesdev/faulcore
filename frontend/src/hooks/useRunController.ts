import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { RunMode, ScenarioId } from '../types'

export function useRunController(scenarioId: ScenarioId, mode: RunMode) {
  const [runId, setRunId] = useState<string | null>(null)

  const startRun = useMutation({
    mutationFn: () => api.startRun({ scenario_id: scenarioId, mode }),
    onSuccess: (response) => setRunId(response.run_id),
  })

  const runQuery = useQuery({
    queryKey: ['run', runId],
    queryFn: () => api.getRun(runId!),
    enabled: Boolean(runId),
    refetchInterval: (query) => query.state.data?.status === 'running' ? 700 : false,
  })

  useEffect(() => {
    setRunId(null)
    startRun.reset()
  }, [scenarioId, mode]) // eslint-disable-line react-hooks/exhaustive-deps

  const reset = () => {
    setRunId(null)
    startRun.reset()
  }

  return {
    run: runQuery.data ?? null,
    runId,
    start: () => startRun.mutate(),
    reset,
    isStarting: startRun.isPending,
    isPolling: Boolean(runId && (runQuery.isPending || runQuery.data?.status === 'running')),
    error: startRun.error ?? runQuery.error ?? null,
  }
}
