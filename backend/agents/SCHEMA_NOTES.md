# Agent schema boundary

`schemas.py` contains strict contracts for model-generated agent output only.

Before integration, Person B should review whether these cross-boundary contracts
belong in `backend/models`:

- identifiers and evidence references;
- the normalized agent assessment exposed by `GET /api/runs/{run_id}`;
- arbiter decision values (`accept`, `correct`, `broaden`, `escalate`).

No shared or Person B-owned files are created or changed in Phase 0.
