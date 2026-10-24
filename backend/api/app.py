"""RecallScope HTTP routes and per-run coordination."""

from typing import Callable, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from backend.api.errors import install_error_handlers
from backend.api.runs import RunCoordinator, run_agent_workflow
from backend.models.api import (
    GraphData,
    Run,
    Scenario,
    ScenarioId,
    StartRunRequest,
    StartRunResponse,
)
from backend.scenarios.graph import public_graph
from backend.scenarios.loader import bundled_manifest


SCENARIOS = (
    Scenario(id="over-recall-01", name="Correlation over-recall trap", alert_type="Complaint cluster", product="Cedar Valley Granola", difficulty="adversarial", description="A recent delivery is a decoy; only descendants of an older ingredient lot are exposed."),
    Scenario(id="broken-trace-01", name="Broken relabelling chain", alert_type="Supplier contamination notice", product="Northstar Almond Bites", difficulty="critical", description="A missing relabelling map prevents a defensible narrow containment boundary."),
)


def create_app(agent_runner: Callable[[Any, str], Any] = run_agent_workflow,
               *, timeout_seconds: float = 120.0) -> FastAPI:
    app = FastAPI(title="FaultCore RecallScope")
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
    install_error_handlers(app)
    coordinator = RunCoordinator(agent_runner, timeout_seconds=timeout_seconds)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/scenarios", response_model=list[Scenario])
    def list_scenarios() -> list[Scenario]:
        return [bundled_manifest("clean-trace-01").scenario, *SCENARIOS]

    @app.get("/api/scenarios/{scenario_id}/graph", response_model=GraphData)
    def get_graph(scenario_id: ScenarioId) -> GraphData:
        try:
            manifest = bundled_manifest(scenario_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Scenario graph not implemented yet") from None
        return public_graph(manifest)

    @app.post("/api/runs", response_model=StartRunResponse, status_code=status.HTTP_202_ACCEPTED)
    def start_run(request: StartRunRequest) -> StartRunResponse:
        run_id = coordinator.start(request.scenario_id, request.mode)
        return StartRunResponse(run_id=run_id, status="running")

    @app.get("/api/runs/{run_id}", response_model=Run)
    def get_run(run_id: str) -> Run:
        run = coordinator.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    return app


app = create_app()
