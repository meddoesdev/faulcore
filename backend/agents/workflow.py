"""Explicit typed RecallScope workflow with application-enforced context isolation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .mock_provider import DeterministicMockProvider
from .prompts import ARBITER_PROMPT, BASELINE_PROMPT, CORRECTION_PROMPT, INVESTIGATOR_PROMPT, REVIEWER_PROMPT
from .providers import InvalidModelOutput, LLMProvider, ModelRequest, ProviderAttempt, ProviderUnavailable
from .schemas import ArbiterOutput, BaselineOutput, InvestigatorOutput, ReviewerOutput
from .trace import TraceSnapshot, TraceToolPort


class IncidentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario_id: Literal["clean-trace-01", "over-recall-01", "broken-trace-01"]
    seed_lot_id: str = Field(min_length=1, max_length=128)
    alert_type: str = Field(min_length=1, max_length=200)
    product: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=1000)
    untrusted_evidence: tuple[str, ...] = ()


class RunProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str
    model: str
    fallback_used: bool
    unavailable_attempts: tuple[dict[str, str], ...] = ()
    correction_cycle_used: bool = False
    mock: bool = False


class AgentRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    mode: Literal["faultcore", "baseline"]
    investigator: InvestigatorOutput | None = None
    reviewer: ReviewerOutput | None = None
    arbiter: ArbiterOutput | None = None
    baseline: BaselineOutput | None = None
    provenance: RunProvenance | None = None
    error: str | None = None


@dataclass(frozen=True)
class _Completed:
    result: AgentRunResult
    correction_used: bool


class AgentWorkflow:
    """No LangGraph dependency: the small state machine is explicit and auditable."""

    def __init__(
        self,
        trace_tools: TraceToolPort,
        providers: Sequence[LLMProvider],
        *,
        include_mock_fallback: bool = True,
    ) -> None:
        self._trace_tools = trace_tools
        self._providers = list(providers)
        if include_mock_fallback and not any(provider.name == "mock" for provider in self._providers):
            self._providers.append(DeterministicMockProvider())

    def run(self, incident: IncidentInput, mode: Literal["faultcore", "baseline"]) -> AgentRunResult:
        unavailable: list[ProviderAttempt] = []
        for provider_index, provider in enumerate(self._providers):
            if not provider.configured:
                continue
            try:
                completed = self._execute(provider, incident, mode)
                completed.result.provenance = RunProvenance(
                    provider=provider.name,
                    model=provider.model,
                    fallback_used=provider_index > 0 or bool(unavailable),
                    unavailable_attempts=tuple(
                        {"provider": item.provider, "model": item.model, "error": item.error}
                        for item in unavailable
                    ),
                    correction_cycle_used=completed.correction_used,
                    mock=provider.name == "mock",
                )
                return completed.result
            except ProviderUnavailable:
                # Discard every partial result and restart the full reasoning run.
                unavailable.append(
                    ProviderAttempt(provider.name, provider.model, "Provider unavailable.")
                )
                continue
            except InvalidModelOutput as exc:
                return AgentRunResult(status="failed", mode=mode, error=str(exc))
            except Exception:  # clean workflow boundary; never leak partial decisions or errors
                return AgentRunResult(status="failed", mode=mode, error="Agent workflow failed.")
        return AgentRunResult(status="failed", mode=mode, error="No configured provider was available")

    def _execute(
        self,
        provider: LLMProvider,
        incident: IncidentInput,
        mode: Literal["faultcore", "baseline"],
    ) -> _Completed:
        trace = self._trace_tools.collect_evidence(incident.scenario_id, incident.seed_lot_id)
        raw_payload = self._raw_payload(incident, trace)
        if mode == "baseline":
            baseline = provider.generate(ModelRequest(
                role="baseline",
                system_prompt=BASELINE_PROMPT,
                payload=raw_payload,
                output_type=BaselineOutput,
            ))
            return _Completed(
                AgentRunResult(status="completed", mode="baseline", baseline=baseline),
                correction_used=False,
            )

        investigator = provider.generate(ModelRequest(
            role="investigator",
            system_prompt=INVESTIGATOR_PROMPT,
            payload=raw_payload,
            output_type=InvestigatorOutput,
        ))

        # This request is constructed only from the immutable incident and raw trace.
        # The committed Investigator output is deliberately not reachable here.
        reviewer = provider.generate(ModelRequest(
            role="reviewer",
            system_prompt=REVIEWER_PROMPT,
            payload=self._reviewer_payload(incident, trace),
            output_type=ReviewerOutput,
        ))

        arbiter = self._arbitrate(provider, incident, trace, investigator, reviewer, correction_used=False)
        correction_used = False
        if arbiter.decision == "correct" and arbiter.requested_correction:
            correction_used = True
            correction_payload = {
                **raw_payload,
                "arbiter_requested_correction": arbiter.requested_correction,
            }
            investigator = provider.generate(ModelRequest(
                role="investigator_correction",
                system_prompt=CORRECTION_PROMPT,
                payload=correction_payload,
                output_type=InvestigatorOutput,
            ))
            arbiter = self._arbitrate(provider, incident, trace, investigator, reviewer, correction_used=True)

        return _Completed(
            AgentRunResult(
                status="completed",
                mode="faultcore",
                investigator=investigator,
                reviewer=reviewer,
                arbiter=arbiter,
            ),
            correction_used=correction_used,
        )

    @staticmethod
    def _raw_payload(incident: IncidentInput, trace: TraceSnapshot) -> dict:
        return {
            "scenario_id": incident.scenario_id,
            "alert": {
                "type": incident.alert_type,
                "product": incident.product,
                "description": incident.description,
            },
            "untrusted_evidence": list(incident.untrusted_evidence),
            "deterministic_trace": trace.model_dump(mode="json"),
        }

    @classmethod
    def _reviewer_payload(cls, incident: IncidentInput, trace: TraceSnapshot) -> dict:
        """Separate constructor makes the blindness boundary easy to test and audit."""
        return cls._raw_payload(incident, trace)

    @staticmethod
    def _arbitrate(
        provider: LLMProvider,
        incident: IncidentInput,
        trace: TraceSnapshot,
        investigator: InvestigatorOutput,
        reviewer: ReviewerOutput,
        *,
        correction_used: bool,
    ) -> ArbiterOutput:
        return provider.generate(ModelRequest(
            role="arbiter",
            system_prompt=ARBITER_PROMPT,
            payload={
                "scenario_id": incident.scenario_id,
                "deterministic_trace": trace.model_dump(mode="json"),
                "committed_investigator": investigator.model_dump(mode="json"),
                "committed_reviewer": reviewer.model_dump(mode="json"),
                "correction_cycle_used": correction_used,
            },
            output_type=ArbiterOutput,
        ))
