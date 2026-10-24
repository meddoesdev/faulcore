"""Phase 9 run lifecycle and fail-closed agent-to-action mapping."""

import asyncio
import json
import time
from types import SimpleNamespace as Obj

from backend.api.runs import RunCoordinator
from backend.api.app import create_app
from backend.scenarios.loader import bundled_manifest
from backend.simulator.trace import TraceTools


def assessment(lots):
    return Obj(summary="Recorded scope", affected_lot_ids=lots,
               possibly_affected_lot_ids=[], excluded_lot_ids=[], evidence=[],
               missing_evidence=[], confidence=0.9)


def agent_result(scenario_id, mode):
    if mode == "baseline":
        lots = ["LOT-G31", "LOT-G32"] if scenario_id == "over-recall-01" else ["LOT-A71", "LOT-A72"]
        return Obj(status="completed", baseline=assessment(lots))
    lots = ["LOT-G31"] if scenario_id == "over-recall-01" else ["LOT-A71", "LOT-A72"]
    return Obj(status="completed", investigator=assessment(["LOT-G31", "LOT-G32"]),
               reviewer=assessment(lots),
               arbiter=Obj(decision="accept", summary="Recorded scope", final_scope_lot_ids=lots,
                           disagreements=[], requested_correction=None, confidence=0.95))


def completed(coordinator, run_id):
    for _ in range(200):
        run = coordinator.get(run_id)
        if run.status != "running":
            return run
        time.sleep(0.01)
    raise AssertionError("run did not reach a terminal state")


def test_faultcore_uses_arbiter_scope_not_investigator_scope():
    coordinator = RunCoordinator(lambda manifest, mode: agent_result(manifest.scenario.id, mode))
    run = completed(coordinator, coordinator.start("over-recall-01", "faultcore"))
    assert run.status == "completed"
    assert run.investigator.affected_lot_ids == ["LOT-G31", "LOT-G32"]
    assert run.arbiter.final_scope_lot_ids == ["LOT-G31"]
    assert [action.target_ids for action in run.actions] == [
        ["LOT-G31@DC-WEST"], ["LOT-G31@DC-WEST"],
    ]
    assert all(action.status == "executed" for action in run.actions)
    assert run.verification.missed_units == 0
    assert run.metrics.safe_inventory_preserved == 1.0
    assert [event.sequence for event in run.events] == list(range(1, len(run.events) + 1))


def test_baseline_large_scope_escalates_before_inventory_mutation():
    coordinator = RunCoordinator(lambda manifest, mode: agent_result(manifest.scenario.id, mode))
    run = completed(coordinator, coordinator.start("over-recall-01", "baseline"))
    assert run.status == "completed"
    assert run.investigator.agent == "baseline"
    assert len(run.actions) == 1
    assert run.actions[0].status == "escalated"
    assert run.verification.contained_units == 0
    assert run.metrics.containment_recall == 0


def test_arbiter_escalation_never_executes_mutating_action():
    def runner(manifest, mode):
        result = agent_result(manifest.scenario.id, mode)
        result.arbiter.decision = "escalate"
        result.arbiter.final_scope_lot_ids = ["LOT-N18", "RELABELLED-UNKNOWN"]
        return result

    coordinator = RunCoordinator(runner)
    run = completed(coordinator, coordinator.start("broken-trace-01", "faultcore"))
    assert run.status == "completed"
    assert [action.type for action in run.actions] == ["escalate_incident"]
    assert run.actions[0].status == "executed"
    assert run.verification.missed_units == 480


def test_unresolved_correction_uses_only_escalation_path():
    def runner(manifest, mode):
        result = agent_result(manifest.scenario.id, mode)
        result.arbiter.decision = "correct"
        return result

    coordinator = RunCoordinator(runner)
    run = completed(coordinator, coordinator.start("clean-trace-01", "faultcore"))
    assert run.status == "completed"
    assert [action.type for action in run.actions] == ["escalate_incident"]


def test_unknown_model_scope_fails_without_action():
    def runner(manifest, mode):
        result = agent_result(manifest.scenario.id, mode)
        result.arbiter.final_scope_lot_ids = ["LOT-NOT-RECORDED"]
        return result

    coordinator = RunCoordinator(runner)
    run = completed(coordinator, coordinator.start("clean-trace-01", "faultcore"))
    assert run.status == "failed"
    assert run.actions == []
    assert run.metrics is None


def test_failed_agent_run_has_no_partial_decision_or_actions():
    coordinator = RunCoordinator(lambda manifest, mode: Obj(status="failed", error="malformed output"))
    run = completed(coordinator, coordinator.start("clean-trace-01", "faultcore"))
    assert run.status == "failed"
    assert run.investigator is None and run.reviewer is None and run.arbiter is None
    assert run.actions == []
    assert run.error == "Agent workflow failed."


def test_timeout_is_terminal_and_late_agent_result_cannot_mutate_run():
    def slow(manifest, mode):
        time.sleep(0.08)
        return agent_result(manifest.scenario.id, mode)

    coordinator = RunCoordinator(slow, timeout_seconds=0.01)
    run_id = coordinator.start("clean-trace-01", "faultcore")
    assert completed(coordinator, run_id).status == "failed"
    time.sleep(0.1)
    assert coordinator.get(run_id).actions == []


def test_runs_are_isolated_and_restart_has_no_stale_run():
    runner = lambda manifest, mode: agent_result(manifest.scenario.id, mode)
    coordinator = RunCoordinator(runner)
    first = completed(coordinator, coordinator.start("clean-trace-01", "faultcore"))
    second = completed(coordinator, coordinator.start("clean-trace-01", "faultcore"))
    assert first.run_id != second.run_id
    assert first.verification == second.verification
    assert RunCoordinator(runner).get(first.run_id) is None


def test_declared_broken_record_is_visible_as_gap_without_fabricated_path():
    trace = TraceTools(bundled_manifest("broken-trace-01"))
    assert "RELABEL-MISSING: missing or corrupted record" in trace.find_traceability_gaps("ING-3099")
    assert "LOT-R-UNKNOWN" not in trace.find_descendant_lots("ING-3099")


def test_http_run_progression_and_explicit_vite_cors():
    app = create_app(lambda manifest, mode: agent_result(manifest.scenario.id, mode))

    async def request(method, path, body=None, headers=None):
        messages = []
        payload = json.dumps(body).encode() if body is not None else b""

        async def receive():
            return {"type": "http.request", "body": payload, "more_body": False}

        async def send(message):
            messages.append(message)

        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                 "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
                 "query_string": b"", "root_path": "", "headers": headers or [],
                 "server": ("localhost", 80), "client": ("127.0.0.1", 1234)}
        await app(scope, receive, send)
        return messages[0]["status"], dict(messages[0]["headers"]), messages[1]["body"]

    async def check():
        status, headers, _ = await request("OPTIONS", "/api/runs", headers=[
            (b"origin", b"http://localhost:5173"),
            (b"access-control-request-method", b"POST"),
        ])
        assert status == 200
        assert headers[b"access-control-allow-origin"] == b"http://localhost:5173"
        status, _, raw = await request("POST", "/api/runs",
                                       {"scenario_id": "clean-trace-01", "mode": "baseline"},
                                       [(b"content-type", b"application/json")])
        assert status == 202
        run_id = json.loads(raw)["run_id"]
        for _ in range(200):
            status, _, raw = await request("GET", f"/api/runs/{run_id}")
            run = json.loads(raw)
            if run["status"] != "running":
                break
            await asyncio.sleep(0.01)
        assert status == 200 and run["status"] == "completed"
        assert run["investigator"]["agent"] == "baseline"
        assert len(run["actions"]) == 2
        assert run["verification"]["missed_units"] == 0
        assert run["metrics"]["containment_recall"] == 1.0
        assert b"ground_truth" not in raw

    asyncio.run(check())
