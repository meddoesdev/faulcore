"""Phase 4 state transitions, audit, evidence checks, and deterministic reset."""

import pytest

from backend.scenarios.loader import ScenarioManifest, bundled_manifest
from backend.simulator.state import ScenarioState


def test_allocate_hold_flags_order_and_is_idempotent() -> None:
    state = ScenarioState(bundled_manifest("clean-trace-01"))
    initial = state.snapshot_bytes()
    order = state.allocate_order("ORDER-1", "PROD-BARS", "LOT-A71", "DC-EAST", 20)
    assert order.status == "allocated"
    assert state.inventory[("LOT-A71", "DC-EAST")].available == 400
    assert state.inventory[("LOT-A71", "DC-EAST")].allocated == 20
    assert state.inventory[("LOT-A71", "DC-EAST")].total() == 420

    hold = state.place_hold("LOT-A71", "DC-EAST")
    assert hold.moved_units == 400
    assert hold.flagged_order_ids == ("ORDER-1",)
    assert state.orders["ORDER-1"].status == "flagged"
    with pytest.raises(ValueError, match="not dispatchable"):
        state.dispatch_order("ORDER-1")
    assert state.inventory[("LOT-A71", "DC-EAST")].held == 400
    assert state.inventory[("LOT-A71", "DC-EAST")].allocated == 20
    assert state.inventory[("LOT-A71", "DC-EAST")].total() == 420
    assert state.place_hold("LOT-A71", "DC-EAST").duplicate is True
    assert [event.result for event in state.audit_events] == ["allocated", "held", "duplicate"]
    assert state.snapshot_bytes() != initial

    state.reset()
    assert state.snapshot_bytes() == initial
    assert state.orders == {}
    assert state.audit_events[-1].action == "reset"
    assert [event.sequence for event in state.audit_events] == [1, 2, 3, 4]
    state.reset()
    assert state.snapshot_bytes() == initial


def test_multi_lot_order_and_in_transit_exception() -> None:
    data = bundled_manifest("clean-trace-01").model_dump(mode="json")
    data["shipments"].append({"id": "SHIP-TRANSIT", "lot_id": "LOT-A71",
                              "from_facility_id": "PLANT-A", "to_facility_id": "STORE-014",
                              "quantity": 5, "status": "in_transit", "timestamp": "2026-10-21T18:00:00Z"})
    state = ScenarioState(ScenarioManifest.model_validate(data))
    state.allocate_order("ORDER-MULTI", "PROD-BARS", "LOT-A71", "DC-EAST", 10)
    state.allocate_order("ORDER-MULTI", "PROD-BARS", "LOT-A72", "STORE-014", 15)
    assert len(state.orders["ORDER-MULTI"].allocations) == 2
    hold = state.place_hold("LOT-A71", "DC-EAST")
    assert hold.flagged_order_ids == ("ORDER-MULTI",)
    assert hold.exception_shipment_ids == ("SHIP-TRANSIT",)
    assert state.shipments["SHIP-TRANSIT"] == "exception"
    with pytest.raises(ValueError, match="cannot receive"):
        state.allocate_order("ORDER-MULTI", "PROD-BARS", "LOT-A72", "STORE-014", 1)
    state.reset()
    assert state.shipments["SHIP-TRANSIT"] == "in_transit"


def test_unflagged_order_moves_allocated_units_to_shipped() -> None:
    state = ScenarioState(bundled_manifest("clean-trace-01"))
    state.allocate_order("ORDER-SAFE", "PROD-BARS", "LOT-A72", "STORE-014", 12)
    dispatched = state.dispatch_order("ORDER-SAFE")
    assert dispatched.status == "shipped"
    balances = state.inventory[("LOT-A72", "STORE-014")]
    assert (balances.available, balances.allocated, balances.shipped) == (368, 0, 12)
    assert balances.total() == 380
    assert state.audit_events[-1].action == "dispatch_order"
    with pytest.raises(ValueError, match="not dispatchable"):
        state.dispatch_order("ORDER-SAFE")


def test_mutation_requires_valid_identifiers_quantities_and_evidence_path() -> None:
    state = ScenarioState(bundled_manifest("clean-trace-01"))
    initial = state.snapshot_bytes()
    invalid = [
        lambda: state.allocate_order("bad order", "PROD-BARS", "LOT-A71", "DC-EAST", 1),
        lambda: state.allocate_order("ORDER-2", "PROD-BARS", "LOT-A71", "DC-EAST", 0),
        lambda: state.allocate_order("ORDER-2", "ING-OATS", "LOT-A71", "DC-EAST", 1),
        lambda: state.place_hold("UNKNOWN", "DC-EAST"),
    ]
    for mutation in invalid:
        with pytest.raises(ValueError):
            mutation()
    assert state.snapshot_bytes() == initial
    assert state.audit_events == ()

    data = bundled_manifest("clean-trace-01").model_dump(mode="json")
    data["inventory"].append({"lot_id": "LOT-A71", "location_id": "STORE-014",
                              "quantity": 1, "status": "available"})
    no_route = ScenarioState(ScenarioManifest.model_validate(data))
    with pytest.raises(ValueError, match="evidence path"):
        no_route.place_hold("LOT-A71", "STORE-014")
    assert no_route.audit_events == ()


def test_snapshot_and_read_views_do_not_leak_or_mutate_state() -> None:
    state = ScenarioState(bundled_manifest("clean-trace-01"))
    original = state.snapshot_bytes()
    state.inventory[("LOT-A71", "DC-EAST")].available = 0
    state.shipments["SHIP-701"] = "exception"
    assert state.snapshot_bytes() == original
    state.place_hold("LOT-A71", "DC-EAST")
    state.audit_events[0].inputs["lot_id"] = "TAMPERED"
    assert state.audit_events[0].inputs["lot_id"] == "LOT-A71"
    assert b"ground_truth" not in original
    assert "ground_truth" not in vars(state)
