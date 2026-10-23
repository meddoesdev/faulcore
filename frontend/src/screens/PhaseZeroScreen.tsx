import { MockStatus } from '../components/MockStatus'
import { useScenarios } from '../hooks/useScenarios'

export function PhaseZeroScreen() {
  const scenarios = useScenarios()

  return (
    <main>
      <p className="eyebrow">FaultCore RecallScope</p>
      <h1>Phase 0 scaffold is running.</h1>
      <p className="lede">This intentionally minimal page verifies that the typed API layer and static fixtures load.</p>

      <MockStatus />

      <section aria-labelledby="fixture-heading">
        <h2 id="fixture-heading">Mock scenarios</h2>
        {scenarios.isPending && <p>Loading fixtures…</p>}
        {scenarios.isError && <p role="alert">Could not load fixtures: {scenarios.error.message}</p>}
        {scenarios.data && (
          <ul>
            {scenarios.data.map((scenario) => (
              <li key={scenario.id}>
                <strong>{scenario.name}</strong>
                <span>{scenario.id}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  )
}

