"""Exercise Phase 1 route shapes through ASGI without extra dependencies."""

import asyncio
import json

from backend.api.app import create_app
from backend.models.api import GraphData, Run, Scenario, StartRunResponse


def test_mock_routes_match_shared_models() -> None:
    app = create_app()

    async def request(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
        messages: list[dict] = []
        payload = json.dumps(body).encode() if body is not None else b""

        async def receive() -> dict:
            return {"type": "http.request", "body": payload, "more_body": False}

        async def send(message: dict) -> None:
            messages.append(message)

        scope = {
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": method, "scheme": "http", "path": path,
            "raw_path": path.encode(), "query_string": b"", "root_path": "",
            "headers": [(b"content-type", b"application/json")],
            "server": ("localhost", 80), "client": ("127.0.0.1", 1234),
        }
        await app(scope, receive, send)
        return messages[0]["status"], json.loads(messages[1]["body"])

    async def check() -> None:
        code, cards = await request("GET", "/api/scenarios")
        assert code == 200
        assert {card["id"] for card in cards} == {"clean-trace-01", "over-recall-01", "broken-trace-01"}
        for card in cards:
            Scenario.model_validate(card)

        code, graph = await request("GET", "/api/scenarios/clean-trace-01/graph")
        assert code == 200
        GraphData.model_validate(graph)
        assert len(graph["nodes"]) == 6
        assert len(graph["edges"]) == 5

        for scenario_id in ("over-recall-01", "broken-trace-01"):
            code, graph = await request("GET", f"/api/scenarios/{scenario_id}/graph")
            assert code == 200
            assert GraphData.model_validate(graph).scenario_id == scenario_id

        code, started = await request("POST", "/api/runs", {"scenario_id": "clean-trace-01", "mode": "baseline"})
        assert code == 202
        start = StartRunResponse.model_validate(started)
        code, run = await request("GET", f"/api/runs/{start.run_id}")
        assert code == 200
        assert Run.model_validate(run).mode == "baseline"
        assert run["metrics"] is None

        code, error = await request("GET", "/api/runs/absent")
        assert code == 404
        assert set(error) == {"code", "message", "request_id"}

        code, error = await request("POST", "/api/runs", {"scenario_id": "unknown", "mode": "baseline"})
        assert code == 422
        assert error["code"] == "validation_error"
        assert set(error) == {"code", "message", "request_id"}

    asyncio.run(check())
