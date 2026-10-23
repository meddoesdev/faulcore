"""Thin, read-only boundary between reasoning agents and deterministic trace tools."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict


class TraceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario_id: str
    seed_lot_id: str
    backward_node_ids: tuple[str, ...] = ()
    forward_node_ids: tuple[str, ...] = ()
    descendant_lot_ids: tuple[str, ...] = ()
    inventory_positions: tuple[dict[str, Any], ...] = ()
    quantity_reconciliations: tuple[dict[str, Any], ...] = ()
    traceability_gaps: tuple[str, ...] = ()


class TraceToolPort(Protocol):
    def collect_evidence(self, scenario_id: str, seed_lot_id: str) -> TraceSnapshot: ...


def _plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "__dict__"):
        return vars(value).copy()
    return value


class PersonBTraceAdapter:
    """Duck-typed adapter for Person B's ``TraceTools`` without owning that code."""

    def __init__(self, tools: Any) -> None:
        self._tools = tools

    def collect_evidence(self, scenario_id: str, seed_lot_id: str) -> TraceSnapshot:
        backward = self._tools.trace_backward(seed_lot_id)
        forward = self._tools.trace_forward(seed_lot_id)
        descendants = tuple(self._tools.find_descendant_lots(seed_lot_id))
        relevant_lots = (seed_lot_id, *descendants)
        positions = tuple(_plain(item) for item in self._tools.get_inventory_positions(relevant_lots))
        reconciliations = tuple(_plain(self._tools.reconcile_quantities(lot_id)) for lot_id in relevant_lots)
        gaps = tuple(
            gap
            for lot_id in relevant_lots
            for gap in self._tools.find_traceability_gaps(lot_id)
        )
        return TraceSnapshot(
            scenario_id=scenario_id,
            seed_lot_id=seed_lot_id,
            backward_node_ids=tuple(backward.node_ids),
            forward_node_ids=tuple(forward.node_ids),
            descendant_lot_ids=descendants,
            inventory_positions=positions,
            quantity_reconciliations=reconciliations,
            traceability_gaps=tuple(dict.fromkeys(gaps)),
        )


@dataclass(frozen=True)
class _Fixture:
    backward: tuple[str, ...]
    forward: tuple[str, ...]
    descendants: tuple[str, ...]
    positions: tuple[dict[str, Any], ...]
    gaps: tuple[str, ...] = ()


class FakeTraceTools:
    """Deterministic evidence for agent development before all manifests are merged."""

    _fixtures = {
        "clean-trace-01": _Fixture(
            backward=("ING-1042",),
            forward=("ING-1042", "TX-210", "LOT-A71", "LOT-A72", "DC-EAST", "STORE-014"),
            descendants=("LOT-A71", "LOT-A72"),
            positions=(
                {"lot_id": "LOT-A71", "location_id": "DC-EAST", "quantity": 420, "status": "available"},
                {"lot_id": "LOT-A72", "location_id": "STORE-014", "quantity": 380, "status": "available"},
            ),
        ),
        "over-recall-01": _Fixture(
            backward=("ING-2010",),
            forward=("ING-2010", "TX-330", "LOT-G31", "DC-WEST"),
            descendants=("LOT-G31",),
            positions=(
                {"lot_id": "LOT-G31", "location_id": "DC-WEST", "quantity": 610, "status": "available"},
                {"lot_id": "LOT-G32", "location_id": "STORE-052", "quantity": 1400, "status": "available", "evidence": "separate ING-2011 branch"},
            ),
        ),
        "broken-trace-01": _Fixture(
            backward=("ING-3018",),
            forward=("ING-3018", "TX-440", "LOT-N18", "DC-NORTH"),
            descendants=("LOT-N18",),
            positions=(
                {"lot_id": "LOT-N18", "location_id": "DC-NORTH", "quantity": 480, "status": "available"},
                {"lot_id": "RELABELLED-UNKNOWN", "location_id": "DC-NORTH", "quantity": 920, "status": "available"},
            ),
            gaps=("Missing mapping from LOT-N18 to its replacement lot code",),
        ),
    }

    def collect_evidence(self, scenario_id: str, seed_lot_id: str) -> TraceSnapshot:
        try:
            fixture = self._fixtures[scenario_id]
        except KeyError:
            raise ValueError(f"unknown scenario: {scenario_id}") from None
        reconciliations = tuple(
            {
                "lot_id": lot_id,
                "recorded_quantity": next(
                    (position["quantity"] for position in fixture.positions if position["lot_id"] == lot_id),
                    0,
                ),
                "issues": list(fixture.gaps),
            }
            for lot_id in (seed_lot_id, *fixture.descendants)
        )
        return TraceSnapshot(
            scenario_id=scenario_id,
            seed_lot_id=seed_lot_id,
            backward_node_ids=fixture.backward,
            forward_node_ids=fixture.forward,
            descendant_lot_ids=fixture.descendants,
            inventory_positions=fixture.positions,
            quantity_reconciliations=reconciliations,
            traceability_gaps=fixture.gaps,
        )
