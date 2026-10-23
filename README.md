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
`python -m uvicorn backend.api.app:app --reload`. All three scenario cards and
graphs now load from validated JSON manifests. Run creation and polling remain
Phase 1 mocks; a run stays `running` until later phases implement execution.

## Current status

Person B's Phase 1–8 backend work is present on stacked review branches. The
shared API models and Phase 1 FastAPI shell provide the agreed four routes.
Phase 2 adds a validated `clean-trace-01` manifest and deterministic graph.
Phase 3 adds six read-only trace tools. Phase 4 adds private in-memory inventory, orders,
shipments, an append-only audit, and deterministic reset. Phase 5 adds the
fail-closed policy checks for the four permitted actions; large or multi-region
containment requires trusted human approval, and missing trace records force
escalation. Phase 6 adds an internal action executor: diagnostics, inventory
holds, fulfillment blocks, and incident escalation all pass policy first,
record an audit outcome, and run a post-action verification query. Reset clears
both operational state and executed-action history for another demo run. Phase 7
adds private post-action scoring for FaultCore and baseline runs. It checks
affected inventory, orders, and in-transit shipments, then calculates
containment precision and recall, safe inventory preservation, under- and
over-containment rates, and time to complete containment. Hidden ground truth
is read only by this verification layer. Phase 8 adds the `over-recall-01` and
`broken-trace-01` manifests and public
graphs. The first has independent affected and safe branches; the second shows
the missing relabelling record without inventing a causal link. Both use the
existing policy and scoring behavior.

These components are not yet wired into completed API runs or Person A's agent
orchestration. `POST /api/runs` still returns a mock run that remains `running`;
the Phase 7 scorer is not yet called by the API. The live run lifecycle is
Phase 9. No action reaches an external system.

