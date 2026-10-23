"""Deterministic, fail-closed policy checks for proposed simulator actions.

This module only decides. Phase 6 will execute approved actions and verify them.
Human approval and correction history are trusted application context, never
fields supplied by an agent or by untrusted evidence text.
"""

import re
from dataclasses import dataclass
from typing import Literal

import networkx as nx

from backend.models.api import PolicyCheck
from backend.scenarios.graph import build_trace_graph
from backend.scenarios.loader import ScenarioManifest, operational_digest
from backend.simulator.state import ScenarioState
from backend.simulator.trace import TraceTools


ALLOWED_ACTIONS = frozenset({
    "run_trace_diagnostics", "place_inventory_hold", "block_fulfillment", "escalate_incident",
})
PROHIBITED_ACTIONS = frozenset({
    "publish_recall_notice", "dispose_inventory", "release_inventory_hold",
    "contact_supplier", "issue_refund",
})
MUTATING_ACTIONS = frozenset({"place_inventory_hold", "block_fulfillment"})
MAX_TARGETS = 20
MAX_AUTONOMOUS_UNITS = 1000
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


@dataclass(frozen=True)
class ActionTarget:
    lot_id: str
    location_id: str
    product_id: str


@dataclass(frozen=True)
class ActionRequest:
    action: str
    targets: tuple[ActionTarget, ...]
    evidence_text: str = ""  # Untrusted; intentionally never read by policy checks.


@dataclass(frozen=True)
class PolicyContext:
    human_approved: bool = False
    corrective_action: bool = False
    correction_cycles_used: int = 0
    executed_action_keys: frozenset[str] = frozenset()


@dataclass(frozen=True)
class PolicyDecision:
    status: Literal["approved", "rejected", "escalate"]
    checks: tuple[PolicyCheck, ...]

    @property
    def approved(self) -> bool:
        return self.status == "approved"


def _check(check_id: str, status: Literal["pass", "fail", "escalate"], detail: str) -> PolicyCheck:
    return PolicyCheck(id=check_id, name=check_id.replace("_", " ").title(),
                       status=status, detail=detail)


class PolicyEngine:
    """Holds operational trace facts only; never retains hidden ground truth."""

    def __init__(self, manifest: ScenarioManifest) -> None:
        self.scenario_id = manifest.scenario.id
        self.manifest_digest = operational_digest(manifest)
        self._graph = nx.freeze(build_trace_graph(manifest))
        self._lot_products = {lot.id: lot.product_id for lot in manifest.lots}
        self._regions = {facility.id: facility.region for facility in manifest.topology}
        self._positions = {(item.lot_id, item.location_id) for item in manifest.inventory}
        self._permitted = frozenset(manifest.permitted_actions)
        self._declared_trace_gap = bool(manifest.missing_or_corrupted_records)
        self._trace_tools = TraceTools(manifest)

    @staticmethod
    def action_key(request: ActionRequest) -> str:
        targets = sorted((item.lot_id, item.location_id, item.product_id)
                         for item in request.targets)
        return repr((request.action, targets))

    @staticmethod
    def _valid_targets(request: ActionRequest) -> bool:
        return (type(request.targets) is tuple and 0 < len(request.targets) <= MAX_TARGETS
                and all(type(item) is ActionTarget
                        and all(type(value) is str and _IDENTIFIER.fullmatch(value)
                                for value in (item.lot_id, item.location_id, item.product_id))
                        for item in request.targets))

    def check_action_allowlist(self, request: ActionRequest) -> PolicyCheck:
        passed = type(request.action) is str and request.action in ALLOWED_ACTIONS
        passed = passed and request.action in self._permitted
        return _check("action_allowlist", "pass" if passed else "fail",
                      "Action is permitted." if passed else "Action is not permitted.")

    def check_prohibited_behavior(self, request: ActionRequest) -> PolicyCheck:
        passed = request.action not in PROHIBITED_ACTIONS
        return _check("prohibited_behavior", "pass" if passed else "fail",
                      "No prohibited behavior requested." if passed else "Requested behavior is prohibited.")

    def check_structured_identifiers(self, request: ActionRequest) -> PolicyCheck:
        if not self._valid_targets(request):
            return _check("structured_identifiers", "fail", "Targets must be 1–20 typed identifiers.")
        identities = {(item.lot_id, item.location_id, item.product_id) for item in request.targets}
        valid = len(identities) == len(request.targets) and all(
            item.lot_id in self._lot_products
            and item.location_id in self._regions
            and self._lot_products[item.lot_id] == item.product_id
            for item in request.targets
        )
        return _check("structured_identifiers", "pass" if valid else "fail",
                      "Lot, location, and product IDs match." if valid
                      else "Unknown, duplicated, or mismatched target identifiers.")

    def check_evidence_paths(self, request: ActionRequest) -> PolicyCheck:
        if not self._valid_targets(request):
            return _check("evidence_paths", "fail", "Cannot verify malformed targets.")
        if request.action not in MUTATING_ACTIONS:
            return _check("evidence_paths", "pass", "Non-mutating diagnostics or escalation may report gaps.")
        valid = all(
            (item.lot_id, item.location_id) in self._positions
            and item.lot_id in self._graph and item.location_id in self._graph
            and nx.has_path(self._graph, item.lot_id, item.location_id)
            for item in request.targets
        )
        return _check("evidence_paths", "pass" if valid else "fail",
                      "Every target has a recorded trace path." if valid
                      else "At least one target lacks a recorded trace path.")

    def check_scope_limits(self, request: ActionRequest) -> PolicyCheck:
        passed = self._valid_targets(request)
        return _check("scope_limits", "pass" if passed else "fail",
                      "Target count is within the hard limit." if passed
                      else "Target count or shape exceeds the hard limit.")

    def check_human_approval(self, request: ActionRequest, context: PolicyContext,
                             state: ScenarioState) -> PolicyCheck:
        if not self._valid_targets(request):
            return _check("human_approval", "fail", "Cannot assess malformed scope.")
        if request.action not in MUTATING_ACTIONS:
            return _check("human_approval", "pass", "No autonomous inventory mutation requested.")
        positions = state.inventory
        units = sum(positions[(item.lot_id, item.location_id)].total()
                    for item in request.targets if (item.lot_id, item.location_id) in positions)
        regions = {self._regions[item.location_id] for item in request.targets
                   if item.location_id in self._regions}
        needs_approval = units > MAX_AUTONOMOUS_UNITS or len(regions) > 1
        status = "escalate" if needs_approval and not context.human_approved else "pass"
        return _check("human_approval", status,
                      "Human approval required for large or multi-region scope."
                      if status == "escalate" else "Scope is within autonomous limits or approved.")

    def check_traceability_gaps(self, request: ActionRequest) -> PolicyCheck:
        if not self._valid_targets(request):
            return _check("traceability_gaps", "fail", "Cannot assess malformed targets.")
        if request.action not in MUTATING_ACTIONS:
            return _check("traceability_gaps", "pass", "Diagnostics and escalation remain available.")
        if self._declared_trace_gap:
            return _check("traceability_gaps", "escalate", "Unresolved trace records require escalation.")
        for item in request.targets:
            if item.lot_id in self._lot_products and self._trace_tools.find_traceability_gaps(item.lot_id):
                return _check("traceability_gaps", "escalate", "Recorded links are incomplete; escalate.")
        return _check("traceability_gaps", "pass", "No declared traceability gap blocks this scope.")

    def check_duplicate_action(self, request: ActionRequest, context: PolicyContext,
                               state: ScenarioState) -> PolicyCheck:
        if not self._valid_targets(request):
            return _check("duplicate_action", "fail", "Cannot compare malformed targets.")
        duplicate = self.action_key(request) in context.executed_action_keys
        if request.action == "place_inventory_hold":
            held = {(event.inputs.get("lot_id"), event.inputs.get("location_id"))
                    for event in state.audit_events if event.action == "place_hold"}
            duplicate = duplicate or any((item.lot_id, item.location_id) in held
                                         for item in request.targets)
        return _check("duplicate_action", "fail" if duplicate else "pass",
                      "Duplicate action is blocked." if duplicate else "Action has not already executed.")

    def check_correction_limit(self, context: PolicyContext) -> PolicyCheck:
        valid = (type(context.corrective_action) is bool
                 and type(context.correction_cycles_used) is int
                 and context.correction_cycles_used >= 0)
        passed = valid and (not context.corrective_action or context.correction_cycles_used < 1)
        return _check("correction_limit", "pass" if passed else "fail",
                      "Correction cycle is available." if passed
                      else "At most one autonomous correction cycle is permitted.")

    def evaluate(self, request: object, context: PolicyContext,
                 state: ScenarioState) -> PolicyDecision:
        """Run every check and reject closed; no check can override another failure."""
        if (type(request) is not ActionRequest or type(context) is not PolicyContext
                or type(state) is not ScenarioState or type(request.action) is not str):
            return PolicyDecision("rejected", (_check("request_shape", "fail",
                                                       "Typed request and trusted context are required."),))
        if (type(context.human_approved) is not bool
                or type(context.corrective_action) is not bool
                or type(context.correction_cycles_used) is not int
                or context.correction_cycles_used < 0
                or type(context.executed_action_keys) is not frozenset
                or not all(type(key) is str for key in context.executed_action_keys)):
            return PolicyDecision("rejected", (_check("context_shape", "fail",
                                                       "Trusted context has an invalid shape."),))
        if state.scenario_id != self.scenario_id or state.manifest_digest != self.manifest_digest:
            return PolicyDecision("rejected", (_check("scenario_identity", "fail",
                                                       "Policy and state operational manifests differ."),))
        checks = (
            self.check_action_allowlist(request),
            self.check_prohibited_behavior(request),
            self.check_structured_identifiers(request),
            self.check_evidence_paths(request),
            self.check_scope_limits(request),
            self.check_human_approval(request, context, state),
            self.check_traceability_gaps(request),
            self.check_duplicate_action(request, context, state),
            self.check_correction_limit(context),
        )
        if any(check.status == "fail" for check in checks):
            status: Literal["approved", "rejected", "escalate"] = "rejected"
        elif any(check.status == "escalate" for check in checks):
            status = "escalate"
        else:
            status = "approved"
        return PolicyDecision(status, checks)
