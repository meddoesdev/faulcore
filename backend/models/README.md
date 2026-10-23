# Shared API contracts

`api.py` is the agreed serialization boundary between the frontend, agent
orchestration, API, simulator, policy engine, and verification code. Internal
domain models may be richer, but routes must return these public shapes.

## Route shapes

| Method | Route | Request | Successful response |
| --- | --- | --- | --- |
| `GET` | `/api/scenarios` | — | `list[Scenario]` |
| `GET` | `/api/scenarios/{scenario_id}/graph` | — | `GraphData` |
| `POST` | `/api/runs` | `StartRunRequest` | `StartRunResponse` (`202`) |
| `GET` | `/api/runs/{run_id}` | — | `Run` |

All non-success responses use `ErrorResponse`. Unknown scenario and run IDs use
`404`; invalid request bodies or path values use `422`; unexpected failures use
`500` without exposing internal exception text.

The frontend polls `GET /api/runs/{run_id}` every 500–1,000 ms while `status` is
`running`. During a run, incomplete sections are `null` or empty lists. A
baseline run has `reviewer=null` and `arbiter=null` by design.

## Contract rules

- The scenario IDs are exactly `clean-trace-01`, `over-recall-01`, and
  `broken-trace-01`.
- JSON field names remain snake_case to match the existing TypeScript contract.
- Unknown response fields are rejected so accidental contract drift is visible.
- Agents never receive hidden ground truth; verification models are populated
  only after action execution.
- `backend/agents/schemas.py` remains the model-output boundary. Agent results
  are mapped into `AgentAssessment` and `ArbiterDecision` before API exposure.
