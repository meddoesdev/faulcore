"""Per-run coordinator: agent decisions, policy-gated actions, and private scoring."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from backend.models.api import Action, AgentAssessment, ArbiterDecision, EvidenceReference, Run, RunEvent
from backend.policy.engine import ActionRequest, ActionTarget
from backend.scenarios.loader import ScenarioManifest, bundled_manifest
from backend.simulator.actions import ActionExecutor
from backend.simulator.state import ScenarioState
from backend.simulator.trace import TraceTools
from backend.simulator.verification import score_run


def run_agent_workflow(manifest: ScenarioManifest, mode: str) -> Any:
    """Import Person A's published interface only when an actual run starts."""
    from backend.agents.providers import provider_chain_from_env
    from backend.agents.trace import PersonBTraceAdapter
    from backend.agents.workflow import AgentWorkflow, IncidentInput

    seed_lot = next(lot.id for lot in manifest.lots if lot.kind == "ingredient")
    incident = IncidentInput(
        scenario_id=manifest.scenario.id,
        seed_lot_id=seed_lot,
        alert_type=manifest.scenario.alert_type,
        product=manifest.scenario.product,
        description=manifest.scenario.description,
        untrusted_evidence=(manifest.initial_alert.text,
                            *(item.text for item in manifest.decoy_evidence)),
    )
    workflow = AgentWorkflow(PersonBTraceAdapter(TraceTools(manifest)), provider_chain_from_env())
    return workflow.run(incident, mode)


def _assessment(agent: str, result: Any) -> AgentAssessment:
    return AgentAssessment(
        agent=agent, summary=result.summary, affected_lot_ids=result.affected_lot_ids,
        possibly_affected_lot_ids=result.possibly_affected_lot_ids,
        excluded_lot_ids=result.excluded_lot_ids,
        evidence=[EvidenceReference(id=item.evidence_id, kind=item.evidence_type,
                                    summary=item.finding) for item in result.evidence],
        missing_evidence=result.missing_evidence, confidence=result.confidence,
    )


def _arbiter(result: Any) -> ArbiterDecision:
    return ArbiterDecision(
        decision=result.decision, summary=result.summary,
        final_scope_lot_ids=result.final_scope_lot_ids,
        disagreements=result.disagreements,
        requested_correction=result.requested_correction, confidence=result.confidence,
    )


def _targets(manifest: ScenarioManifest, lot_ids: list[str]) -> tuple[ActionTarget, ...]:
    """Expand complete lot IDs from trusted inventory; reject unknown or empty scope."""
    if not lot_ids or len(lot_ids) != len(set(lot_ids)):
        raise ValueError("empty or duplicate action scope")
    products = {lot.id: lot.product_id for lot in manifest.lots}
    if any(lot_id not in products for lot_id in lot_ids):
        raise ValueError("action scope has an unknown lot")
    wanted = set(lot_ids)
    positions = sorted((item for item in manifest.inventory if item.lot_id in wanted),
                       key=lambda item: (item.lot_id, item.location_id))
    if {item.lot_id for item in positions} != wanted:
        raise ValueError("action scope has no recorded inventory position")
    return tuple(ActionTarget(item.lot_id, item.location_id, products[item.lot_id])
                 for item in positions)


class RunCoordinator:
    """In-memory run store; each run owns a fresh simulator and executor."""

    def __init__(self, agent_runner: Callable[[ScenarioManifest, str], Any] = run_agent_workflow,
                 *, timeout_seconds: float = 120.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("run timeout must be positive")
        self._agent_runner = agent_runner
        self._timeout_seconds = timeout_seconds
        self._runs: dict[str, Run] = {}
        self._lock = threading.RLock()

    def start(self, scenario_id: str, mode: str) -> str:
        run_id = f"run-{uuid4().hex}"
        with self._lock:
            self._runs[run_id] = Run(run_id=run_id, scenario_id=scenario_id,
                                     mode=mode, status="running")
            self._event(run_id, "alert", "completed", "Scenario alert received.")
        threading.Thread(target=self._execute, args=(run_id,), daemon=True).start()
        return run_id

    def get(self, run_id: str) -> Run | None:
        with self._lock:
            run = self._runs.get(run_id)
            return run.model_copy(deep=True) if run is not None else None

    def _event(self, run_id: str, stage: str, status: str, message: str) -> None:
        run = self._runs[run_id]
        sequence = len(run.events) + 1
        run.events.append(RunEvent(id=f"event-{sequence}", sequence=sequence,
                                   timestamp=datetime.now(timezone.utc), stage=stage,
                                   status=status, message=message))

    def _fail(self, run_id: str, stage: str, message: str) -> None:
        with self._lock:
            run = self._runs[run_id]
            if run.status != "running":
                return
            run.status = "failed"
            run.error = message
            self._event(run_id, stage, "failed", message)

    def _execute(self, run_id: str) -> None:
        with self._lock:
            run = self._runs[run_id]
            scenario_id, mode = run.scenario_id, run.mode
            self._event(run_id, "investigation", "started", "Agent workflow started.")
        started = time.monotonic()
        timer = threading.Timer(self._timeout_seconds, self._fail,
                                args=(run_id, "investigation", "Run timed out."))
        timer.daemon = True
        timer.start()
        stage = "investigation"
        try:
            manifest = bundled_manifest(scenario_id)
            result = self._agent_runner(manifest, mode)
            with self._lock:
                run = self._runs[run_id]
                if run.status != "running":
                    return
                if result.status != "completed":
                    self._fail(run_id, "investigation", "Agent workflow failed.")
                    return
                provenance = getattr(result, "provenance", None)
                if provenance is not None:
                    self._event(run_id, "investigation", "info",
                                f"Provider: {provenance.provider}; mock: {provenance.mock}.")
                if mode == "faultcore":
                    if result.investigator is None or result.reviewer is None or result.arbiter is None:
                        raise ValueError("incomplete FaultCore agent result")
                    run.investigator = _assessment("investigator", result.investigator)
                    self._event(run_id, "investigation", "completed", "Investigator assessment committed.")
                    run.reviewer = _assessment("reviewer", result.reviewer)
                    self._event(run_id, "review", "completed", "Blind Reviewer assessment committed.")
                    run.arbiter = _arbiter(result.arbiter)
                    self._event(run_id, "arbitration", "completed", "Arbiter scope committed.")
                else:
                    if result.baseline is None:
                        raise ValueError("incomplete baseline result")
                    run.investigator = _assessment("baseline", result.baseline)
                    self._event(run_id, "investigation", "completed", "Baseline assessment committed.")

            stage = "policy"
            state = ScenarioState(manifest)
            executor = ActionExecutor(manifest, state)
            if mode == "faultcore" and result.arbiter.decision in {"escalate", "correct"}:
                # Escalation is non-mutating. Use a known inventory target without
                # interpreting or repairing any unknown model-generated lot ID.
                position = sorted(manifest.inventory,
                                  key=lambda item: (item.lot_id, item.location_id))[0]
                product = next(lot.product_id for lot in manifest.lots if lot.id == position.lot_id)
                targets = (ActionTarget(position.lot_id, position.location_id, product),)
                action_names = ("escalate_incident",)
            else:
                scope = (result.arbiter.final_scope_lot_ids if mode == "faultcore"
                         else result.baseline.affected_lot_ids)
                targets = _targets(manifest, scope)
                action_names = ("place_inventory_hold", "block_fulfillment")

            for action_name in action_names:
                with self._lock:
                    if self._runs[run_id].status != "running":
                        return
                executed = executor.execute(ActionRequest(action_name, targets))
                public_action = Action(
                    id=executed.action_id, type=action_name, status=executed.status,
                    target_ids=list(executed.target_ids), detail=executed.detail,
                )
                with self._lock:
                    run = self._runs[run_id]
                    if run.status != "running":
                        return
                    run.policy_checks.extend(executed.policy_checks)
                    run.actions.append(public_action)
                    self._event(run_id, "policy", "completed", f"Policy evaluated {action_name}.")
                    self._event(run_id, "action", "completed" if executed.status == "executed" else "info",
                                f"{action_name}: {executed.status}.")
                if executed.status != "executed":
                    break

            stage = "verification"
            scored = score_run(manifest, state, mode, elapsed_seconds=time.monotonic() - started)
            with self._lock:
                run = self._runs[run_id]
                if run.status != "running":
                    return
                run.verification = scored.verification
                run.metrics = scored.metrics
                self._event(run_id, "verification", "completed", "Post-action verification completed.")
                run.status = "completed"
        except Exception:
            self._fail(run_id, stage, "Run failed during integration.")
        finally:
            timer.cancel()
