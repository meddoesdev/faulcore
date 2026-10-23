"""Phase 1 API shell with contract-shaped mock responses."""

from uuid import uuid4

from fastapi import FastAPI, HTTPException, status

from backend.api.errors import install_error_handlers
from backend.models.api import (
    GraphData,
    Run,
    Scenario,
    ScenarioId,
    StartRunRequest,
    StartRunResponse,
)


SCENARIOS = (
    Scenario(id="clean-trace-01", name="Clean contamination trace", alert_type="Failed laboratory test", product="Harvest Oat Bars", difficulty="standard", description="A contaminated ingredient lot has a complete transformation and shipment trail."),
    Scenario(id="over-recall-01", name="Correlation over-recall trap", alert_type="Complaint cluster", product="Cedar Valley Granola", difficulty="adversarial", description="A recent delivery is a decoy; only descendants of an older ingredient lot are exposed."),
    Scenario(id="broken-trace-01", name="Broken relabelling chain", alert_type="Supplier contamination notice", product="Northstar Almond Bites", difficulty="critical", description="A missing relabelling map prevents a defensible narrow containment boundary."),
)


def create_app() -> FastAPI:
    app = FastAPI(title="FaultCore RecallScope")
    install_error_handlers(app)
    mock_runs: dict[str, Run] = {}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/scenarios", response_model=list[Scenario])
    def list_scenarios() -> list[Scenario]:
        return list(SCENARIOS)

    @app.get("/api/scenarios/{scenario_id}/graph", response_model=GraphData)
    def get_graph(scenario_id: ScenarioId) -> GraphData:
        return GraphData(scenario_id=scenario_id)

    @app.post("/api/runs", response_model=StartRunResponse, status_code=status.HTTP_202_ACCEPTED)
    def start_run(request: StartRunRequest) -> StartRunResponse:
        run_id = f"run-{uuid4().hex}"
        mock_runs[run_id] = Run(run_id=run_id, scenario_id=request.scenario_id, mode=request.mode, status="running")
        return StartRunResponse(run_id=run_id, status="running")

    @app.get("/api/runs/{run_id}", response_model=Run)
    def get_run(run_id: str) -> Run:
        run = mock_runs.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    return app


app = create_app()
