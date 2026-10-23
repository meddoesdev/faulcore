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

## Backend groundwork

The backend uses Python 3.11+ with FastAPI, Pydantic, NetworkX, Uvicorn, and
pytest. Install the pinned local development dependencies with:

```bash
python -m pip install -r requirements.txt
```

Run the backend test suite with:

```bash
python -m pytest backend/tests
```

The backend package structure, shared API models, structured JSON error
handling, and Phase 1 routes are in place. Start the API with
`python -m uvicorn backend.api.app:app --reload`. The `clean-trace-01` card and
graph now load from a validated JSON manifest. Run creation and polling remain
Phase 1 mocks; a run stays `running` until later phases implement execution.

## Current status

Phase 0 and Phase 1 are complete: Person A's frontend and agent schema
scaffolds are present, shared Pydantic API contracts are merged, and Person B's
FastAPI shell serves the agreed four routes with structured errors. Phase 2
adds the first real scenario manifest (`clean-trace-01`), strict loading,
deterministic NetworkX graph construction, and tests that check hidden ground
truth is not serialized to the scenario or graph API. The other two cards are
still placeholders; their graph routes return `404` until their manifests are
built in Phase 8. Policy checks, action execution, scoring, and completed runs
have not started. Phase 3 adds six read-only deterministic
trace tools for backward/forward traversal, descendant lots, inventory lookup,
quantity reconciliation, and traceability-gap detection. The tools retain no
hidden ground truth and are not yet wired to agents or actions. Phase 4 adds
private in-memory inventory balances, order allocation, dispatch and hold transitions,
in-transit shipment exceptions, an append-only audit, and a reset that restores
the operational snapshot byte-for-byte. The audit remains separate so reset
history is not erased. Policy-gated action execution has not started; Phase 4
is awaiting review before Phase 5.

