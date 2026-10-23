"""Strict output contracts for RecallScope reasoning agents.

These are agent-layer schemas. API/shared model adoption must be coordinated with
Person B before anything is moved into ``backend/models``.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
Identifier = Annotated[str, Field(min_length=1, max_length=128)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EvidenceReference(StrictModel):
    evidence_id: Identifier
    evidence_type: Literal[
        "alert", "trace", "transformation", "shipment", "inventory", "complaint"
    ]
    finding: Annotated[str, Field(min_length=1, max_length=1000)]


class ScopeAssessment(StrictModel):
    summary: Annotated[str, Field(min_length=1, max_length=2000)]
    affected_lot_ids: list[Identifier] = Field(default_factory=list)
    possibly_affected_lot_ids: list[Identifier] = Field(default_factory=list)
    excluded_lot_ids: list[Identifier] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    missing_evidence: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        default_factory=list
    )
    contradictions: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        default_factory=list
    )
    recommended_actions: list[
        Literal[
            "run_trace_diagnostics",
            "place_inventory_hold",
            "block_fulfillment",
            "escalate_incident",
        ]
    ] = Field(default_factory=list)
    confidence: Confidence


class InvestigatorOutput(ScopeAssessment):
    predicted_outcome: Annotated[str, Field(min_length=1, max_length=1000)]


class ReviewerOutput(ScopeAssessment):
    alternative_explanations: list[
        Annotated[str, Field(min_length=1, max_length=500)]
    ] = Field(default_factory=list)


class BaselineOutput(ScopeAssessment):
    pass


class ArbiterOutput(StrictModel):
    decision: Literal["accept", "correct", "broaden", "escalate"]
    summary: Annotated[str, Field(min_length=1, max_length=2000)]
    final_scope_lot_ids: list[Identifier] = Field(default_factory=list)
    agreements: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        default_factory=list
    )
    disagreements: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        default_factory=list
    )
    requested_correction: Annotated[str, Field(min_length=1, max_length=1000)] | None = None
    required_diagnostic: Annotated[str, Field(min_length=1, max_length=1000)] | None = None
    confidence: Confidence

