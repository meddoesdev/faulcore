"""Shared Pydantic contracts for the RecallScope HTTP API.

These models are the serialization boundary shared by the frontend, Person A's
agent orchestration, and Person B's API/simulator. Internal domain and model-
generated output schemas should map into these models rather than replacing
them.
"""

from datetime import datetime
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


ScenarioId: TypeAlias = Literal[
    "clean-trace-01",
    "over-recall-01",
    "broken-trace-01",
]
RunMode: TypeAlias = Literal["faultcore", "baseline"]
RunStatus: TypeAlias = Literal["running", "completed", "failed"]
Identifier = Annotated[str, Field(min_length=1, max_length=128)]
UnitCount = Annotated[int, Field(ge=0)]
Ratio = Annotated[float, Field(ge=0.0, le=1.0)]
MetadataValue: TypeAlias = str | int | float | bool | None


class ApiModel(BaseModel):
    """Strict base model used for every public API payload."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Scenario(ApiModel):
    id: ScenarioId
    name: Annotated[str, Field(min_length=1, max_length=200)]
    alert_type: Annotated[str, Field(min_length=1, max_length=200)]
    product: Annotated[str, Field(min_length=1, max_length=200)]
    difficulty: Literal["standard", "adversarial", "critical"]
    description: Annotated[str, Field(min_length=1, max_length=1000)]


class GraphNode(ApiModel):
    id: Identifier
    type: Literal[
        "supplier_lot",
        "transformation",
        "facility",
        "distribution_center",
        "store",
        "order",
    ]
    label: Annotated[str, Field(min_length=1, max_length=200)]
    exposure: Literal["confirmed", "possible", "excluded"]
    inventory_state: Literal["available", "held", "cleared", "in_transit"] | None = None
    metadata: dict[str, MetadataValue] = Field(default_factory=dict)


class GraphEdge(ApiModel):
    id: Identifier
    source: Identifier
    target: Identifier
    exposure: Literal["confirmed", "possible", "excluded"]
    label: Annotated[str, Field(min_length=1, max_length=200)] | None = None


class GraphData(ApiModel):
    scenario_id: ScenarioId
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class EvidenceReference(ApiModel):
    id: Identifier
    kind: Literal[
        "alert",
        "trace",
        "transformation",
        "shipment",
        "inventory",
        "complaint",
    ]
    summary: Annotated[str, Field(min_length=1, max_length=1000)]


class AgentAssessment(ApiModel):
    agent: Literal["investigator", "reviewer", "baseline"]
    summary: Annotated[str, Field(min_length=1, max_length=2000)]
    affected_lot_ids: list[Identifier] = Field(default_factory=list)
    possibly_affected_lot_ids: list[Identifier] = Field(default_factory=list)
    excluded_lot_ids: list[Identifier] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    missing_evidence: list[
        Annotated[str, Field(min_length=1, max_length=500)]
    ] = Field(default_factory=list)
    confidence: Ratio


class ArbiterDecision(ApiModel):
    decision: Literal["accept", "correct", "broaden", "escalate"]
    summary: Annotated[str, Field(min_length=1, max_length=2000)]
    final_scope_lot_ids: list[Identifier] = Field(default_factory=list)
    disagreements: list[
        Annotated[str, Field(min_length=1, max_length=500)]
    ] = Field(default_factory=list)
    requested_correction: Annotated[str, Field(min_length=1, max_length=1000)] | None = None
    confidence: Ratio


class PolicyCheck(ApiModel):
    id: Identifier
    name: Annotated[str, Field(min_length=1, max_length=200)]
    status: Literal["pass", "fail", "escalate"]
    detail: Annotated[str, Field(min_length=1, max_length=1000)]


class Action(ApiModel):
    id: Identifier
    type: Literal[
        "run_trace_diagnostics",
        "place_inventory_hold",
        "block_fulfillment",
        "escalate_incident",
    ]
    status: Literal["approved", "rejected", "executed", "escalated"]
    target_ids: list[Identifier] = Field(default_factory=list)
    detail: Annotated[str, Field(min_length=1, max_length=1000)]


class VerificationCheck(ApiModel):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    passed: bool
    detail: Annotated[str, Field(min_length=1, max_length=1000)]


class Verification(ApiModel):
    affected_units: UnitCount
    contained_units: UnitCount
    missed_units: UnitCount
    safe_units_held: UnitCount
    safe_units_available: UnitCount
    residual_risk: Literal["none", "low", "medium", "high"]
    checks: list[VerificationCheck] = Field(default_factory=list)


class Metrics(ApiModel):
    containment_precision: Ratio
    containment_recall: Ratio
    safe_inventory_preserved: Ratio
    under_containment_rate: Ratio
    over_containment_rate: Ratio
    time_to_containment_seconds: Annotated[float, Field(ge=0.0)]


class RunEvent(ApiModel):
    id: Identifier
    sequence: Annotated[int, Field(ge=1)]
    timestamp: datetime
    stage: Literal[
        "alert",
        "investigation",
        "review",
        "arbitration",
        "policy",
        "action",
        "verification",
    ]
    status: Literal["started", "completed", "failed", "info"]
    message: Annotated[str, Field(min_length=1, max_length=1000)]


class StartRunRequest(ApiModel):
    scenario_id: ScenarioId
    mode: RunMode


class StartRunResponse(ApiModel):
    run_id: Identifier
    status: Literal["running"]


class Run(ApiModel):
    run_id: Identifier
    scenario_id: ScenarioId
    mode: RunMode
    status: RunStatus
    events: list[RunEvent] = Field(default_factory=list)
    investigator: AgentAssessment | None = None
    reviewer: AgentAssessment | None = None
    arbiter: ArbiterDecision | None = None
    policy_checks: list[PolicyCheck] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    verification: Verification | None = None
    metrics: Metrics | None = None
    error: str | None = None


class ErrorResponse(ApiModel):
    code: Annotated[str, Field(min_length=1, max_length=100)]
    message: Annotated[str, Field(min_length=1, max_length=500)]
    request_id: Identifier

