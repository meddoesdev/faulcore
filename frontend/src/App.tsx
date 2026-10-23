import { useState } from 'react'
import { AppShell } from './components/AppShell'
import { useScenarios } from './hooks/useScenarios'
import { CommandCenter } from './screens/CommandCenter'
import { IncidentSelector } from './screens/IncidentSelector'
import type { ScenarioId } from './types'

export default function App() {
  const [selectedScenarioId, setSelectedScenarioId] = useState<ScenarioId | null>(null)
  const scenarios = useScenarios()
  const selectedScenario = scenarios.data?.find((scenario) => scenario.id === selectedScenarioId)
  const view = selectedScenarioId ? 'command' : 'incidents'

  return (
    <AppShell
      view={view}
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
