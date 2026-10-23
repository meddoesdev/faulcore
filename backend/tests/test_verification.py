"""Phase 7 scoring of simulator effects, isolated from agent and policy inputs."""

import pytest

from backend.policy.engine import ActionRequest, ActionTarget
from backend.scenarios.graph import public_graph
from backend.scenarios.loader import ScenarioManifest, bundled_manifest
from backend.simulator.actions import ActionExecutor
from backend.simulator.state import ScenarioState
from backend.simulator.trace import TraceTools
from backend.simulator.verification import score_run


A71 = ActionTarget("LOT-A71", "DC-EAST", "PROD-BARS")
A72 = ActionTarget("LOT-A72", "STORE-014", "PROD-BARS")
SAFE = ActionTarget("LOT-S81", "DC-EAST", "PROD-BARS")


def setup(manifest=None):
    manifest = manifest or bundled_manifest("clean-trace-01")
    state = ScenarioState(manifest)
    return manifest, state, ActionExecutor(manifest, state)


def with_safe_inventory():
    data = bundled_manifest("clean-trace-01").model_dump(mode="json")
    data["lots"].extend([
        {"id": "ING-SAFE", "product_id": "ING-OATS", "kind": "ingredient",
         "quantity": 250, "origin_facility_id": "SUP-ATLAS"},
        {"id": "LOT-S81", "product_id": "PROD-BARS", "kind": "finished",
         "quantity": 200, "origin_facility_id": "PLANT-A"},
    ])
    data["transformations"].append({
        "id": "TX-SAFE", "facility_id": "PLANT-A", "timestamp": "2026-10-21T09:00:00Z",
        "inputs": [{"lot_id": "ING-SAFE", "quantity": 250}],
        "outputs": [{"lot_id": "LOT-S81", "quantity": 200}],
    })
    data["shipments"].append({
        "id": "SHIP-SAFE", "lot_id": "LOT-S81", "from_facility_id": "PLANT-A",
        "to_facility_id": "DC-EAST", "quantity": 200, "status": "received",
        "timestamp": "2026-10-21T17:00:00Z",
    })
    data["inventory"].append({"lot_id": "LOT-S81", "location_id": "DC-EAST",
                              "quantity": 200, "status": "available"})
    return ScenarioManifest.model_validate(data)


def hold(executor, *targets):
    result = executor.execute(ActionRequest("place_inventory_hold", targets))
    assert result.status == "executed"


def test_clean_trace_exact_hand_calculated_metrics_for_both_modes():
    manifest, state, executor = setup()
    hold(executor, A71, A72)
    before = state.snapshot_bytes()
    faultcore = score_run(manifest, state, "faultcore", elapsed_seconds=12.5)
    baseline = score_run(manifest, state, "baseline", elapsed_seconds=12.5)
    assert state.snapshot_bytes() == before
    assert baseline == faultcore
    verification, metrics = faultcore.verification, faultcore.metrics
    assert (verification.affected_units, verification.contained_units,
            verification.missed_units, verification.safe_units_held,
            verification.safe_units_available) == (800, 800, 0, 0, 0)
    assert verification.residual_risk == "none"
    assert all(check.passed for check in verification.checks)
    assert (metrics.containment_precision, metrics.containment_recall,
            metrics.safe_inventory_preserved, metrics.under_containment_rate,
            metrics.over_containment_rate, metrics.time_to_containment_seconds) == (
                1.0, 1.0, 1.0, 0.0, 0.0, 12.5)


def test_partial_hold_reports_under_containment_and_no_completion_time():
    manifest, state, executor = setup()
    hold(executor, A71)
    result = score_run(manifest, state, "faultcore", elapsed_seconds=9.0)
    assert result.verification.contained_units == 420
    assert result.verification.missed_units == 380
    assert result.verification.residual_risk == "high"
    assert result.metrics.containment_precision == 1.0
    assert result.metrics.containment_recall == 420 / 800
    assert result.metrics.under_containment_rate == 380 / 800
    assert result.metrics.time_to_containment_seconds == 0.0
    assert not result.verification.checks[0].passed


def test_safe_inventory_preservation_and_over_containment():
    manifest, state, executor = setup(with_safe_inventory())
    hold(executor, A71, A72)
    preserved = score_run(manifest, state, "baseline", elapsed_seconds=5.0)
    assert preserved.verification.safe_units_available == 200
    assert preserved.metrics.safe_inventory_preserved == 1.0
    assert preserved.metrics.over_containment_rate == 0.0

    hold(executor, SAFE)
    over = score_run(manifest, state, "baseline", elapsed_seconds=7.0)
    assert over.verification.safe_units_held == 200
    assert over.verification.safe_units_available == 0
    assert over.verification.contained_units == 1000
    assert over.metrics.containment_precision == 0.8
    assert over.metrics.containment_recall == 1.0
    assert over.metrics.safe_inventory_preserved == 0.0
    assert over.metrics.over_containment_rate == 1.0
    assert not over.verification.checks[3].passed


def test_fulfillment_block_counts_as_containment_without_changing_hold_balance():
    manifest, state, executor = setup()
    state.allocate_order("ORDER-1", "PROD-BARS", "LOT-A71", "DC-EAST", 20)
    result = executor.execute(ActionRequest("block_fulfillment", (A71, A72)))
    assert result.status == "executed"
    score = score_run(manifest, state, "faultcore", elapsed_seconds=4.0)
    assert score.verification.contained_units == 800
    assert score.verification.missed_units == 0
    assert score.verification.safe_units_held == 0
    assert score.metrics.time_to_containment_seconds == 4.0
    assert all(check.passed for check in score.verification.checks)
    assert state.inventory[("LOT-A71", "DC-EAST")].held == 0


def test_affected_order_and_in_transit_shipment_must_be_flagged():
    data = bundled_manifest("clean-trace-01").model_dump(mode="json")
    data["shipments"].append({
        "id": "SHIP-TRANSIT", "lot_id": "LOT-A71", "from_facility_id": "PLANT-A",
        "to_facility_id": "STORE-014", "quantity": 5, "status": "in_transit",
        "timestamp": "2026-10-21T18:00:00Z",
    })
    manifest, state, executor = setup(ScenarioManifest.model_validate(data))
    state.allocate_order("ORDER-1", "PROD-BARS", "LOT-A71", "DC-EAST", 20)
    before = score_run(manifest, state, "faultcore", elapsed_seconds=1.0)
    assert not before.verification.checks[1].passed
    assert not before.verification.checks[2].passed
    hold(executor, A71, A72)
    after = score_run(manifest, state, "faultcore", elapsed_seconds=3.0)
    assert all(check.passed for check in after.verification.checks)
    assert after.verification.contained_units == 800
    assert state.orders["ORDER-1"].status == "flagged"
    assert state.shipments["SHIP-TRANSIT"] == "exception"
    with pytest.raises(ValueError, match="not dispatchable"):
        state.dispatch_order("ORDER-1")


def test_scoring_truth_is_private_and_cannot_change_operational_state():
    manifest, state, _ = setup()
    before = state.snapshot_bytes()
    result = score_run(manifest, state, "faultcore", elapsed_seconds=0.0)
    assert state.snapshot_bytes() == before
    assert "ground_truth" not in public_graph(manifest).model_dump_json()
    assert "ground_truth" not in manifest.scenario.model_dump_json()
    assert "ground_truth" not in vars(TraceTools(manifest))
    assert "ground_truth" not in vars(state)
    assert "ground_truth" not in result.verification.model_dump_json()
    assert "ground_truth" not in result.metrics.model_dump_json()


def test_scoring_rejects_wrong_state_and_invalid_elapsed_time():
    manifest, state, _ = setup()
    altered = manifest.model_copy(deep=True)
    altered.inventory[0].quantity -= 1
    with pytest.raises(ValueError, match="does not match"):
        score_run(altered, state, "faultcore", elapsed_seconds=1.0)
    for invalid in (-1.0, float("nan"), float("inf"), True):
        with pytest.raises(ValueError, match="elapsed time"):
            score_run(manifest, state, "faultcore", elapsed_seconds=invalid)
