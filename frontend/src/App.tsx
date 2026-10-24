import { useLayoutEffect, useState } from 'react'
import { AppShell } from './components/AppShell'
import { useScenarios } from './hooks/useScenarios'
import { useApiConnection } from './hooks/useApiConnection'
import { CommandCenter } from './screens/CommandCenter'
import { IncidentSelector } from './screens/IncidentSelector'
import type { ScenarioId } from './types'

export default function App() {
  const [selectedScenarioId, setSelectedScenarioId] = useState<ScenarioId | null>(null)
  const scenarios = useScenarios()
  const connection = useApiConnection()
  const selectedScenario = scenarios.data?.find((scenario) => scenario.id === selectedScenarioId)
  const view = selectedScenarioId ? 'command' : 'incidents'

  useLayoutEffect(() => {
    if (!selectedScenarioId) return
    const root = document.documentElement
    const previousScrollBehavior = root.style.scrollBehavior
    root.style.scrollBehavior = 'auto'
    root.scrollTop = 0
    document.body.scrollTop = 0
    const restoreFrame = window.requestAnimationFrame(() => {
      root.style.scrollBehavior = previousScrollBehavior
    })
    return () => {
      window.cancelAnimationFrame(restoreFrame)
      root.style.scrollBehavior = previousScrollBehavior
    }
  }, [selectedScenarioId])

  return (
    <AppShell
      view={view}
      connection={connection}
      incidentLabel={selectedScenario?.id.toUpperCase()}
      onNavigate={(nextView) => {
        if (nextView === 'incidents') setSelectedScenarioId(null)
      }}
    >
      {selectedScenario ? (
        <CommandCenter scenario={selectedScenario} onBack={() => setSelectedScenarioId(null)} />
      ) : (
        <IncidentSelector onSelect={setSelectedScenarioId} />
      )}
    </AppShell>
  )
}
