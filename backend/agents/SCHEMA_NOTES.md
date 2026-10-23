# Agent schema boundary

`schemas.py` contains strict contracts for model-generated agent output only.

The reviewed HTTP boundary now lives in `backend/models/api.py`. Agent outputs
must be explicitly mapped into its `AgentAssessment` and `ArbiterDecision`
models before they are exposed by `GET /api/runs/{run_id}`.

Keeping these layers separate preserves prompt-specific fields such as
contradictions and alternative explanations without silently expanding the
shared API response.
