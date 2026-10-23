# FaultCore RecallScope

FaultCore RecallScope is a multi-agent product-containment prototype for
supply-chain incidents. It compares an Investigator's proposed recall scope
with an independently produced Reviewer scope, resolves disagreements through
an Arbiter, and submits the result to deterministic policy controls before any
simulated containment action.

## Canonical scenarios

- `clean-trace-01`
- `over-recall-01`
- `broken-trace-01`

These IDs are part of the shared API contract and must match across the
frontend, simulator manifests, and API responses.

## Ownership

- Person A: `frontend/**`, `backend/agents/**`
- Person B: `backend/api/**`, `backend/policy/**`, `backend/simulator/**`,
  `backend/scenarios/**`
- Shared review required: `backend/models/**`, root documentation, and API
  contract changes

See [`AGENTS.md`](AGENTS.md) for repository working rules.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend uses deterministic mock data by default. Copy
`frontend/.env.example` to `frontend/.env` and set `VITE_USE_MOCKS=false` when
the backend API is available.

## Current status

Phase 0 is complete on Person A's side: the frontend scaffold, typed API
contracts, mock scenario/run data, API client switch, and draft agent output
schemas are present. Later phases must be approved before implementation.

