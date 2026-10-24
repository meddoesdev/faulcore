"""Private, read-only post-action verification and ground-truth scoring.

Only this layer reads ``manifest.ground_truth``. Agents, policy, operational
state, and public graph construction remain independent of hidden truth.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from backend.models.api import Metrics, Verification, VerificationCheck
from backend.scenarios.loader import ScenarioManifest, operational_digest
from backend.simulator.state import ScenarioState


@dataclass(frozen=True)
class ScoreResult:
    verification: Verification
    metrics: Metrics


def score_run(
    manifest: ScenarioManifest,
    state: ScenarioState,
    mode: Literal["faultcore", "baseline"],
    *,
    elapsed_seconds: float,
) -> ScoreResult:
    """Score either mode with identical rules after its policy-gated actions.

    ``elapsed_seconds`` is measured by the future run coordinator from alert
    receipt to this verification. A value of zero in the public metric means
    full containment has not yet been achieved.
    """
    if state.scenario_id != manifest.scenario.id or state.manifest_digest != operational_digest(manifest):
        raise ValueError("verification manifest does not match simulator state")
    if mode not in {"faultcore", "baseline"}:
        raise ValueError("unknown scoring mode")
    if (type(elapsed_seconds) not in {int, float} or not math.isfinite(elapsed_seconds)
            or elapsed_seconds < 0):
        raise ValueError("elapsed time must be a finite nonnegative number")

    truth = manifest.ground_truth
    affected_positions = set(truth.correct_containment_scope)
    affected_lots = set(truth.affected_lot_ids)
    inventory = state.inventory
    orders = state.orders
    shipments = state.shipments
    blocked = state.blocked_positions

    affected_contained = 0
    safe_contained = 0
    safe_held = 0
    safe_available = 0
    safe_total = 0
    affected_allocatable = 0

    for (lot_id, location_id), balances in inventory.items():
        position_id = f"{lot_id}@{location_id}"
        is_blocked = (lot_id, location_id) in blocked
        flagged_allocated = sum(
            allocation.quantity
            for order in orders.values() if order.status == "flagged"
            for allocation in order.allocations
            if (allocation.lot_id, allocation.location_id) == (lot_id, location_id)
        )
        # A held unit, blocked available unit, or flagged allocation cannot
        # enter ordinary fulfillment. Shipped units are never counted as held.
        contained = min(
            balances.total(),
            balances.held + flagged_allocated + (balances.available if is_blocked else 0),
        )
        if position_id in affected_positions:
            affected_contained += contained
            if not is_blocked:
                affected_allocatable += balances.available
        else:
            safe_total += balances.total()
            safe_contained += contained
            safe_held += balances.held
            if not is_blocked:
                safe_available += balances.available

    affected_contained = min(affected_contained, truth.affected_units)
    missed = truth.affected_units - affected_contained
    dispatchable_orders = sum(
        1 for order in orders.values()
        if order.status == "allocated"
        and any(allocation.lot_id in affected_lots for allocation in order.allocations)
        and not any((allocation.lot_id, allocation.location_id) in blocked
                    for allocation in order.allocations)
    )
    unflagged_shipments = sum(
        1 for shipment in manifest.shipments
        if shipment.lot_id in affected_lots and shipment.status == "in_transit"
        and shipments[shipment.id] != "exception"
    )
    checks = [
        VerificationCheck(
            name="No affected units allocatable", passed=affected_allocatable == 0,
            detail=f"{affected_allocatable} affected units remain available for allocation.",
        ),
        VerificationCheck(
            name="No affected order dispatchable", passed=dispatchable_orders == 0,
            detail=f"{dispatchable_orders} affected orders remain dispatchable.",
        ),
        VerificationCheck(
            name="In-transit shipments flagged", passed=unflagged_shipments == 0,
            detail=f"{unflagged_shipments} affected in-transit shipments lack an exception.",
        ),
        VerificationCheck(
            name="Safe inventory preserved", passed=safe_contained == 0,
            detail=f"{safe_contained} safe units are held, blocked, or flagged.",
        ),
    ]
    fully_contained = missed == 0 and all(check.passed for check in checks[:3])
    residual_risk = "high" if not fully_contained else "low" if safe_contained else "none"
    verification = Verification(
        affected_units=truth.affected_units,
        contained_units=affected_contained + safe_contained,
        missed_units=missed,
        safe_units_held=safe_held,
        safe_units_available=safe_available,
        residual_risk=residual_risk,
        checks=checks,
    )
    all_contained = affected_contained + safe_contained
    metrics = Metrics(
        containment_precision=affected_contained / all_contained if all_contained else 0.0,
        containment_recall=affected_contained / truth.affected_units,
        safe_inventory_preserved=safe_available / safe_total if safe_total else 1.0,
        under_containment_rate=missed / truth.affected_units,
        over_containment_rate=safe_contained / safe_total if safe_total else 0.0,
        time_to_containment_seconds=float(elapsed_seconds) if fully_contained else 0.0,
    )
    return ScoreResult(verification, metrics)
