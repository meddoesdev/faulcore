import { api } from '../api'
import { mockFixtureCount } from '../mocks'

export function MockStatus() {
  return (
    <dl className="mock-status">
      <div><dt>Data source</dt><dd>{api.usingMocks ? 'Static mocks' : 'Backend API'}</dd></div>
      <div><dt>Scenario fixtures</dt><dd>{mockFixtureCount.scenarios}</dd></div>
      <div><dt>Graph fixtures</dt><dd>{mockFixtureCount.graphs}</dd></div>
      <div><dt>Completed run fixtures</dt><dd>{mockFixtureCount.runs}</dd></div>
    </dl>
  )
}

