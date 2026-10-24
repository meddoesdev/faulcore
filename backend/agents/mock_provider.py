"""Deterministic, visibly labeled provider used when external APIs are unavailable."""

from __future__ import annotations

from typing import Any

from .providers import ModelRequest, OutputT
from .schemas import ArbiterOutput, BaselineOutput, EvidenceReference, InvestigatorOutput, ReviewerOutput


def _evidence(evidence_id: str, finding: str, evidence_type: str = "trace") -> EvidenceReference:
    return EvidenceReference(evidence_id=evidence_id, evidence_type=evidence_type, finding=finding)


class DeterministicMockProvider:
    name = "mock"
    model = "deterministic-recallscope-v1"

    @property
    def configured(self) -> bool:
        return True

    def generate(self, request: ModelRequest[OutputT]) -> OutputT:
        scenario = str(request.payload.get("scenario_id"))
        value = self._output(request.role, scenario, request.payload)
        return request.output_type.model_validate(value.model_dump(mode="json"))

    def _output(self, role: str, scenario: str, payload: Any):
        if role in {"investigator", "investigator_correction"}:
            return self._investigator(scenario, corrected=role.endswith("correction"))
        if role == "reviewer":
            return self._reviewer(scenario)
        if role == "arbiter":
            return self._arbiter(scenario, corrected=bool(payload.get("correction_cycle_used")))
        if role == "baseline":
            return self._baseline(scenario)
        raise ValueError(f"unsupported mock role: {role}")

    @staticmethod
    def _investigator(scenario: str, *, corrected: bool) -> InvestigatorOutput:
        if scenario == "clean-trace-01":
            return InvestigatorOutput(
                summary="ING-1042 has recorded transformation paths into LOT-A71 and LOT-A72.",
                affected_lot_ids=["LOT-A71", "LOT-A72"],
                evidence=[_evidence("trace-clean", "Both finished lots descend from ING-1042.")],
                recommended_actions=["place_inventory_hold", "block_fulfillment"],
                confidence=0.97,
                predicted_outcome="All 800 affected units become non-allocatable.",
            )
        if scenario == "over-recall-01":
            broad = not corrected
            return InvestigatorOutput(
                summary="The complaint timing initially implicates G-31 and G-32." if broad else "Correction retains only the recorded ING-2010 descendant G-31.",
                affected_lot_ids=["LOT-G31"],
                possibly_affected_lot_ids=["LOT-G32"] if broad else [],
                excluded_lot_ids=[] if broad else ["LOT-G32"],
                evidence=[_evidence("trace-over", "Only G-31 has a recorded path from ING-2010.")],
                contradictions=["G-32 timing correlates but its transformation uses ING-2011"],
                recommended_actions=["place_inventory_hold", "block_fulfillment"],
                confidence=0.68 if broad else 0.95,
                predicted_outcome="Contain G-31 while preserving the independent G-32 branch.",
            )
        return InvestigatorOutput(
            summary="Known LOT-N18 exposure is confirmed, while LOT-R-UNKNOWN has no recorded source link.",
            affected_lot_ids=["LOT-N18"],
            possibly_affected_lot_ids=["LOT-R-UNKNOWN"],
            evidence=[_evidence("trace-broken", "Recorded trace ends before any link to LOT-R-UNKNOWN.")],
            missing_evidence=["Relabelling map"],
            recommended_actions=["run_trace_diagnostics", "escalate_incident"],
            confidence=0.55,
            predicted_outcome="Known inventory can be held, while unresolved inventory requires escalation.",
        )

    @staticmethod
    def _reviewer(scenario: str) -> ReviewerOutput:
        if scenario == "clean-trace-01":
            return ReviewerOutput(
                summary="Independent reconstruction confirms A71 and A72 as ING-1042 descendants.",
                affected_lot_ids=["LOT-A71", "LOT-A72"],
                evidence=[_evidence("review-clean", "Transformation and shipment records agree.")],
                recommended_actions=["place_inventory_hold", "block_fulfillment"],
                confidence=0.96,
            )
        if scenario == "over-recall-01":
            return ReviewerOutput(
                summary="Only G-31 descends from the older implicated lot; G-32 is a safe decoy branch.",
                affected_lot_ids=["LOT-G31"],
                excluded_lot_ids=["LOT-G32"],
                evidence=[_evidence("review-over", "G-32 transformation records identify ING-2011.")],
                alternative_explanations=["Complaint timing created a non-causal association with G-32"],
                recommended_actions=["place_inventory_hold", "block_fulfillment"],
                confidence=0.96,
            )
        return ReviewerOutput(
            summary="A narrow scope is not defensible while LOT-R-UNKNOWN has no recorded source mapping.",
            affected_lot_ids=["LOT-N18"],
            possibly_affected_lot_ids=["LOT-R-UNKNOWN"],
            evidence=[_evidence("review-broken", "Relabelled stock lacks a recorded source mapping.")],
            missing_evidence=["Relabelling map"],
            alternative_explanations=["Replacement stock may contain affected or safe source lots"],
            recommended_actions=["run_trace_diagnostics", "escalate_incident"],
            confidence=0.48,
        )

    @staticmethod
    def _arbiter(scenario: str, *, corrected: bool) -> ArbiterOutput:
        if scenario == "clean-trace-01":
            return ArbiterOutput(
                decision="accept", summary="Both committed assessments identify the same supported scope.",
                final_scope_lot_ids=["LOT-A71", "LOT-A72"], agreements=["A71 and A72 affected"], confidence=0.98,
            )
        if scenario == "over-recall-01" and not corrected:
            return ArbiterOutput(
                decision="correct", summary="The Reviewer provides the stronger causal transformation path.",
                final_scope_lot_ids=["LOT-G31"], disagreements=["Whether G-32 is possibly affected"],
                requested_correction="Remove G-32 unless a recorded ING-2010 transformation path is produced.",
                confidence=0.95,
            )
        if scenario == "over-recall-01":
            return ArbiterOutput(
                decision="accept", summary="The corrected Investigator scope now matches the independent trace.",
                final_scope_lot_ids=["LOT-G31"], agreements=["G-31 affected", "G-32 excluded"], confidence=0.97,
            )
        return ArbiterOutput(
            decision="escalate", summary="Missing relabelling evidence prevents a defensible narrow action.",
            final_scope_lot_ids=["LOT-N18", "LOT-R-UNKNOWN"],
            disagreements=["Exact identity of relabelled descendants"],
            required_diagnostic="Recover or reconcile the relabelling map.", confidence=0.91,
        )

    @staticmethod
    def _baseline(scenario: str) -> BaselineOutput:
        if scenario == "clean-trace-01":
            return BaselineOutput(
                summary="Hold both recorded ING-1042 descendants.", affected_lot_ids=["LOT-A71", "LOT-A72"],
                evidence=[_evidence("baseline-clean", "Forward trace identifies two lots.")],
                recommended_actions=["place_inventory_hold", "block_fulfillment"], confidence=0.94,
            )
        if scenario == "over-recall-01":
            return BaselineOutput(
                summary="Hold the entire product family around the complaint window.",
                affected_lot_ids=["LOT-G31", "LOT-G32"],
                evidence=[_evidence("baseline-over", "Both lots are temporally correlated.", "complaint")],
                recommended_actions=["place_inventory_hold", "block_fulfillment"], confidence=0.81,
            )
        return BaselineOutput(
            summary="Hold known LOT-N18 while the replacement identity remains unresolved.",
            affected_lot_ids=["LOT-N18"], missing_evidence=["Relabelling map"],
            evidence=[_evidence("baseline-broken", "Trace ends at LOT-N18.")],
            recommended_actions=["place_inventory_hold"], confidence=0.52,
        )
