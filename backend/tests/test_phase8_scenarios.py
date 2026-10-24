"""Phase 8 scenario behavior using recorded paths and policy-gated actions."""

import networkx as nx

from backend.policy.engine import ActionRequest, ActionTarget, PolicyContext
from backend.scenarios.graph import build_trace_graph, public_graph
from backend.scenarios.loader import bundled_manifest
from backend.simulator.actions import ActionExecutor
from backend.simulator.state import ScenarioState
from backend.simulator.trace import TraceTools
from backend.simulator.verification import score_run


G31 = ActionTarget("LOT-G31", "DC-WEST", "PROD-GRANOLA")
G32 = ActionTarget("LOT-G32", "STORE-052", "PROD-GRANOLA")
N18 = ActionTarget("LOT-N18", "STORE-GROUP-7", "PROD-BITES")
UNKNOWN = ActionTarget("LOT-R-UNKNOWN", "STORE-GROUP-7", "PROD-BITES")


def test_over_recall_separates_recorded_branches_and_scores_narrow_containment():
    manifest = bundled_manifest("over-recall-01")
    graph = build_trace_graph(manifest)
    trace = TraceTools(manifest)
    assert trace.find_descendant_lots("ING-2010") == ("LOT-G31",)
    assert trace.find_descendant_lots("ING-2011") == ("LOT-G32",)
    assert nx.has_path(graph, "ING-2010", "DC-WEST")
    assert not nx.has_path(graph, "ING-2010", "LOT-G32")
    assert {node.id for node in public_graph(manifest).nodes} == {
        "ING-2010", "ING-2011", "TX-330", "TX-331", "LOT-G31", "LOT-G32",
        "DC-WEST", "STORE-052",
    }

    state = ScenarioState(manifest)
    executor = ActionExecutor(manifest, state)
    assert executor.execute(ActionRequest("run_trace_diagnostics", (G31,))).status == "executed"
    assert executor.execute(ActionRequest("place_inventory_hold", (G31,))).status == "executed"
    assert executor.execute(ActionRequest("block_fulfillment", (G31,))).status == "executed"
    score = score_run(manifest, state, "faultcore", elapsed_seconds=15)
    assert score.verification.missed_units == 0
    assert score.verification.safe_units_available == 1400
    assert score.metrics.containment_precision == 1.0
    assert score.metrics.containment_recall == 1.0
    assert score.metrics.safe_inventory_preserved == 1.0


def test_over_recall_broad_hold_penalizes_safe_inventory():
    manifest = bundled_manifest("over-recall-01")
    state = ScenarioState(manifest)
    executor = ActionExecutor(manifest, state)
    request = ActionRequest("place_inventory_hold", (G31, G32))
    assert executor.execute(request).status == "escalated"
    assert executor.execute(request, PolicyContext(human_approved=True)).status == "executed"
    score = score_run(manifest, state, "baseline", elapsed_seconds=20)
    assert score.verification.safe_units_held == 1400
    assert score.metrics.containment_precision == 610 / 2010
    assert score.metrics.over_containment_rate == 1.0
    assert score.metrics.safe_inventory_preserved == 0.0


def test_broken_trace_keeps_missing_mapping_unlinked_and_escalates_actions():
    manifest = bundled_manifest("broken-trace-01")
    graph = build_trace_graph(manifest)
    assert nx.has_path(graph, "ING-3099", "LOT-N18")
    assert not nx.has_path(graph, "ING-3099", "LOT-R-UNKNOWN")
    assert graph.degree("RELABEL-MISSING") == 0
    assert graph.nodes["RELABEL-MISSING"]["public"].metadata["record_status"] == "missing"
    trace = TraceTools(manifest)
    assert trace.find_descendant_lots("ING-3099") == ("LOT-N18",)
    assert trace.find_traceability_gaps("LOT-R-UNKNOWN") == (
        "RELABEL-MISSING: missing or corrupted record",
        "LOT-R-UNKNOWN: missing transformation input",
    )

    state = ScenarioState(manifest)
    executor = ActionExecutor(manifest, state)
    assert executor.execute(ActionRequest("run_trace_diagnostics", (UNKNOWN,))).status == "executed"
    attempted = executor.execute(ActionRequest("place_inventory_hold", (N18,)),
                                 PolicyContext(human_approved=True))
    assert attempted.status == "escalated"
    assert any(check.id == "traceability_gaps" and check.status == "escalate"
               for check in attempted.policy_checks)
    assert executor.execute(ActionRequest("escalate_incident", (UNKNOWN,))).status == "executed"
    score = score_run(manifest, state, "faultcore", elapsed_seconds=20)
    assert score.verification.missed_units == 480
    assert score.verification.residual_risk == "high"
    assert score.metrics.time_to_containment_seconds == 0


def test_new_public_graphs_do_not_expose_hidden_truth():
    for scenario_id in ("over-recall-01", "broken-trace-01"):
        serialized = public_graph(bundled_manifest(scenario_id)).model_dump_json()
        for secret in ("ground_truth", "affected_units", "correct_containment_scope",
                       "expected_outcome"):
            assert secret not in serialized
