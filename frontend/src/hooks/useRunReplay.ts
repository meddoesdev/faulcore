import { useCallback, useEffect, useMemo, useState } from 'react'
import { getMockRun } from '../mocks'
import type { Run, RunEvent, ScenarioId } from '../types'

const replayIntervalMs = 720

export function useRunReplay(scenarioId: ScenarioId) {
  const [run, setRun] = useState<Run | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [visibleEventCount, setVisibleEventCount] = useState(0)

  useEffect(() => {
    let active = true
    setIsLoading(true)
    setError(null)
    setRun(null)
    setVisibleEventCount(0)

    getMockRun(`mock-${scenarioId}-faultcore`)
      .then((nextRun) => {
        if (!active) return
        setRun(nextRun)
        setVisibleEventCount(1)
      })
      .catch((reason: unknown) => {
        if (!active) return
        setError(reason instanceof Error ? reason : new Error('Mock run could not be loaded'))
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })

    return () => { active = false }
  }, [scenarioId])

  useEffect(() => {
    if (!run || visibleEventCount >= run.events.length) return
    const timer = window.setTimeout(
      () => setVisibleEventCount((count) => Math.min(count + 1, run.events.length)),
      replayIntervalMs,
    )
    return () => window.clearTimeout(timer)
  }, [run, visibleEventCount])

  const visibleEvents = useMemo(
    () => run?.events.slice(0, visibleEventCount) ?? [],
    [run, visibleEventCount],
  )

  const hasVisibleStage = useCallback(
    (stage: RunEvent['stage']) => visibleEvents.some((event) => event.stage === stage),
    [visibleEvents],
  )

  const replay = useCallback(() => setVisibleEventCount(run ? 1 : 0), [run])

  return {
    run,
    error,
    isLoading,
    visibleEvents,
    hasVisibleStage,
    replay,
    isComplete: Boolean(run && visibleEventCount >= run.events.length),
    progress: run?.events.length ? visibleEventCount / run.events.length : 0,
  }
}

