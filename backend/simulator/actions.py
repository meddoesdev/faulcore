"""Policy-gated, audited execution of the four simulator actions.

This is an internal application service, not an HTTP or model-generated action
interface. It retains operational facts only; hidden scenario truth is reserved
for Phase 7 scoring.
"""

from dataclasses import dataclass
from hashlib import sha256
from typing import Literal

from backend.models.api import PolicyCheck
from backend.policy.engine import ActionRequest, PolicyContext, PolicyEngine
from backend.scenarios.loader import ScenarioManifest, operational_digest
from backend.simulator.state import ScenarioState
from backend.simulator.trace import TraceTools


@dataclass(frozen=True)
class ActionVerification:
    passed: bool
    detail: str


@dataclass(frozen=True)
class ExecutionResult:
    action_id: str
    action: str
    status: Literal["executed", "rejected", "escalated"]
    target_ids: tuple[str, ...]
    detail: str
    policy_checks: tuple[PolicyCheck, ...]
    verification: ActionVerification | None


class ActionExecutor:
    """Owns executed-action history so caller-supplied keys cannot weaken checks."""

    def __init__(self, manifest: ScenarioManifest, state: ScenarioState) -> None:
        if (state.scenario_id != manifest.scenario.id
                or state.manifest_digest != operational_digest(manifest)):
            raise ValueError("action executor and simulator state must use one scenario")
        self._state = state
        self._policy = PolicyEngine(manifest)
        self._trace = TraceTools(manifest)
        self._in_transit_by_lot = {
            lot.id: frozenset(item.id for item in manifest.shipments
                              if item.lot_id == lot.id and item.status == "in_transit")
            for lot in manifest.lots
        }
        self._executed_keys: set[str] = set()

    def reset(self) -> None:
        """Start another deterministic demo run with fresh action history."""
        self._state.reset()
        self._executed_keys.clear()

    @staticmethod
    def _target_ids(request: ActionRequest) -> tuple[str, ...]:
        return tuple(f"{item.lot_id}@{item.location_id}" for item in request.targets)

    @staticmethod
    def _incident_key(request: ActionRequest) -> str:
        digest = sha256(PolicyEngine.action_key(request).encode("utf-8")).hexdigest()[:24]
        return f"incident-{digest}"

    def _verify(self, request: ActionRequest) -> ActionVerification:
        positions = self._state.inventory
        orders = self._state.orders
        if request.action == "run_trace_diagnostics":
            for target in request.targets:
                self._trace.trace_backward(target.lot_id)
                self._trace.trace_forward(target.lot_id)
                self._trace.reconcile_quantities(target.lot_id)
                self._trace.find_traceability_gaps(target.lot_id)
            return ActionVerification(True, "Recorded trace, quantities, and gaps queried for every target.")
        if request.action == "place_inventory_hold":
            shipments = self._state.shipments
            passed = all(
                positions[(target.lot_id, target.location_id)].available == 0
                and not any(
                    order.status == "allocated" and any(
                        allocation.lot_id == target.lot_id
                        and allocation.location_id == target.location_id
                        for allocation in order.allocations
                    ) for order in orders.values()
                )
                and all(shipments[shipment_id] == "exception"
                        for shipment_id in self._in_transit_by_lot[target.lot_id])
                for target in request.targets
            )
            return ActionVerification(passed, "Held inventory, affected orders, and in-transit exceptions queried.")
        if request.action == "block_fulfillment":
            blocked = self._state.blocked_positions
            passed = all(
                (target.lot_id, target.location_id) in blocked
                and not any(
                    order.status == "allocated" and any(
                        allocation.lot_id == target.lot_id
                        and allocation.location_id == target.location_id
                        for allocation in order.allocations
                    ) for order in orders.values()
                )
                for target in request.targets
            )
            return ActionVerification(passed, "Fulfillment block and existing order flags queried.")
        incident_key = self._incident_key(request)
        return ActionVerification(incident_key in self._state.escalations,
                                  "Internal incident escalation record queried.")

    def execute(self, request: object, context: PolicyContext | None = None) -> ExecutionResult:
        """Check policy before touching operational state, then verify the effect."""
        if context is None:
            context = PolicyContext()
        if type(context) is PolicyContext:
            context = PolicyContext(
                human_approved=context.human_approved,
                corrective_action=context.corrective_action,
                correction_cycles_used=context.correction_cycles_used,
                executed_action_keys=frozenset(self._executed_keys | set(context.executed_action_keys))
                if type(context.executed_action_keys) is frozenset else context.executed_action_keys,
            )
        decision = self._policy.evaluate(request, context, self._state)
        action_name = request.action if type(request) is ActionRequest and type(request.action) is str else "invalid"
        target_count = len(request.targets) if type(request) is ActionRequest and type(request.targets) is tuple else 0
        targets = self._target_ids(request) if decision.approved else ()
        action_id = f"action-{len(self._state.audit_events) + 1}"
        if not decision.approved:
            self._state.record_action_attempt(action_name, target_count, decision.status)
            status: Literal["executed", "rejected", "escalated"] = (
                "escalated" if decision.status == "escalate" else "rejected"
            )
            return ExecutionResult(action_id, action_name, status, (),
                                   "Policy did not approve execution.", decision.checks, None)

        checkpoint = self._state._checkpoint()
        try:
            if request.action == "place_inventory_hold":
                for target in request.targets:
                    self._state.place_hold(target.lot_id, target.location_id)
            elif request.action == "block_fulfillment":
                for target in request.targets:
                    self._state.block_fulfillment(target.lot_id, target.location_id)
            elif request.action == "escalate_incident":
                self._state.escalate_incident(self._incident_key(request))
            # Diagnostics are read-only; the query below is their execution.
            verification = self._verify(request)
        except Exception:
            self._state._rollback(checkpoint)
            self._state.record_action_attempt(request.action, len(request.targets), "execution_error")
            raise
        self._executed_keys.add(self._policy.action_key(request))
        result_status: Literal["executed", "rejected", "escalated"] = (
            "executed" if verification.passed else "escalated"
        )
        self._state.record_action_attempt(request.action, len(request.targets), result_status)
        return ExecutionResult(
            action_id, request.action, result_status, targets, verification.detail,
            decision.checks,
            verification,
        )
