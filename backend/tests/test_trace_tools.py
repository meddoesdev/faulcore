"""Phase 3 deterministic trace behavior, including broken records."""

import pytest
from pydantic import ValidationError

from backend.scenarios.loader import ScenarioManifest, bundled_manifest
from backend.simulator.trace import TraceTools


def _scenario_data() -> dict:
    return bundled_manifest("clean-trace-01").model_dump(mode="json")


def test_clean_trace_split_and_shipments() -> None:
    tools = TraceTools(bundled_manifest("clean-trace-01"))
    forward = tools.trace_forward("ING-1042")
    assert set(forward.node_ids) == {
        "ING-1042", "TX-210", "LOT-A71", "LOT-A72", "DC-EAST", "STORE-014"
    }
    assert set(forward.edge_ids) == {
        "TX-210:in:ING-1042", "TX-210:out:LOT-A71", "TX-210:out:LOT-A72",
        "SHIP-701", "SHIP-702",
    }
    assert tools.find_descendant_lots("ING-1042") == ("LOT-A71", "LOT-A72")
    assert set(tools.trace_backward("LOT-A71").node_ids) == {"ING-1042", "TX-210", "LOT-A71"}
    assert tools.get_inventory_positions(["LOT-A72", "LOT-A71"])[0].lot_id == "LOT-A71"
    assert tools.find_traceability_gaps("ING-1042") == ()
    assert tools.reconcile_quantities("LOT-A71").issues == ()
    assert "ground_truth" not in vars(tools)


def test_combined_inputs_are_traced_without_guessing_links() -> None:
    data = _scenario_data()
    data["lots"].append({"id": "ING-1043", "product_id": "ING-OATS", "kind": "ingredient",
                         "quantity": 200, "origin_facility_id": "SUP-ATLAS"})
    data["transformations"][0]["inputs"].append({"lot_id": "ING-1043", "quantity": 200})
    tools = TraceTools(ScenarioManifest.model_validate(data))
    assert set(tools.trace_backward("LOT-A71").node_ids) == {
        "ING-1042", "ING-1043", "TX-210", "LOT-A71"
    }
    assert tools.find_descendant_lots("ING-1043") == ("LOT-A71", "LOT-A72")


def test_missing_link_and_missing_receipt_are_reported() -> None:
    data = _scenario_data()
    data["lots"].append({"id": "LOT-ORPHAN", "product_id": "PROD-BARS", "kind": "finished",
                         "quantity": 50, "origin_facility_id": "PLANT-A"})
    data["shipments"].append({"id": "SHIP-ORPHAN", "lot_id": "LOT-ORPHAN",
                              "from_facility_id": "PLANT-A", "to_facility_id": "STORE-014",
                              "quantity": 50, "status": "received", "timestamp": "2026-10-21T17:00:00Z"})
    tools = TraceTools(ScenarioManifest.model_validate(data))
    assert tools.find_traceability_gaps("LOT-ORPHAN") == (
        "LOT-ORPHAN: missing transformation input",
        "SHIP-ORPHAN: received shipment has no inventory position",
    )
    assert "ING-1042" not in tools.trace_backward("LOT-ORPHAN").node_ids


def test_quantity_reconciliation_detects_aggregate_overshipment() -> None:
    data = _scenario_data()
    data["shipments"].append({"id": "SHIP-703", "lot_id": "LOT-A71",
                              "from_facility_id": "PLANT-A", "to_facility_id": "DC-EAST",
                              "quantity": 5, "status": "received", "timestamp": "2026-10-21T18:00:00Z"})
    result = TraceTools(ScenarioManifest.model_validate(data)).reconcile_quantities("LOT-A71")
    assert result.shipped_quantity == 425
    assert "shipments exceed recorded lot quantity" in result.issues


def test_duplicate_identifiers_and_unknown_lots_are_rejected() -> None:
    data = _scenario_data()
    data["shipments"][0]["id"] = "LOT-A71"
    with pytest.raises(ValidationError, match="globally unique"):
        ScenarioManifest.model_validate(data)
    data = _scenario_data()
    data["transformations"][0]["inputs"].append(data["transformations"][0]["inputs"][0])
    with pytest.raises(ValidationError, match="duplicate lot reference"):
        ScenarioManifest.model_validate(data)
    tools = TraceTools(bundled_manifest("clean-trace-01"))
    for call in (lambda: tools.trace_forward("UNKNOWN"),
                 lambda: tools.trace_backward("UNKNOWN"),
                 lambda: tools.get_inventory_positions(["UNKNOWN"])):
        with pytest.raises(ValueError, match="unknown lot ID"):
            call()
