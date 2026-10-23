"""Read-only trace tools built only from recorded links, never hidden truth."""

from dataclasses import dataclass
from typing import Iterable

import networkx as nx

from backend.scenarios.graph import build_trace_graph
from backend.scenarios.loader import Inventory, Lot, ScenarioManifest, Shipment, Transformation


@dataclass(frozen=True)
class TraceResult:
    node_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]


@dataclass(frozen=True)
class QuantityReconciliation:
    lot_id: str
    recorded_quantity: int
    consumed_quantity: int
    produced_quantity: int
    shipped_quantity: int
    inventory_quantity: int
    issues: tuple[str, ...]


class TraceTools:
    """Operational data only. The manifest's ground_truth is never retained."""

    def __init__(self, manifest: ScenarioManifest) -> None:
        self._graph = nx.freeze(build_trace_graph(manifest))
        self._lots: dict[str, Lot] = {lot.id: lot.model_copy(deep=True) for lot in manifest.lots}
        self._transformations: tuple[Transformation, ...] = tuple(
            item.model_copy(deep=True) for item in manifest.transformations
        )
        self._shipments: tuple[Shipment, ...] = tuple(
            item.model_copy(deep=True) for item in manifest.shipments
        )
        self._inventory: tuple[Inventory, ...] = tuple(
            item.model_copy(deep=True) for item in manifest.inventory
        )

    def _require_lot(self, lot_id: str) -> Lot:
        try:
            return self._lots[lot_id]
        except KeyError:
            raise ValueError(f"unknown lot ID: {lot_id}") from None

    def _trace(self, lot_id: str, *, forward: bool) -> TraceResult:
        self._require_lot(lot_id)
        linked = nx.descendants(self._graph, lot_id) if forward else nx.ancestors(self._graph, lot_id)
        subgraph = self._graph.subgraph({lot_id, *linked})
        return TraceResult(
            node_ids=tuple(nx.lexicographical_topological_sort(subgraph, key=str)),
            edge_ids=tuple(sorted(key for _, _, key in subgraph.edges(keys=True))),
        )

    def trace_backward(self, lot_id: str) -> TraceResult:
        return self._trace(lot_id, forward=False)

    def trace_forward(self, lot_id: str) -> TraceResult:
        return self._trace(lot_id, forward=True)

    def find_descendant_lots(self, lot_id: str) -> tuple[str, ...]:
        self._require_lot(lot_id)
        return tuple(sorted(nx.descendants(self._graph, lot_id) & self._lots.keys()))

    def get_inventory_positions(self, lot_ids: Iterable[str]) -> tuple[Inventory, ...]:
        wanted = set(lot_ids)
        for lot_id in wanted:
            self._require_lot(lot_id)
        return tuple(sorted(
            (position.model_copy(deep=True) for position in self._inventory if position.lot_id in wanted),
            key=lambda position: (position.lot_id, position.location_id),
        ))

    def reconcile_quantities(self, lot_id: str) -> QuantityReconciliation:
        lot = self._require_lot(lot_id)
        consumed = sum(item.quantity for event in self._transformations
                       for item in event.inputs if item.lot_id == lot_id)
        produced = sum(item.quantity for event in self._transformations
                       for item in event.outputs if item.lot_id == lot_id)
        shipped = sum(item.quantity for item in self._shipments if item.lot_id == lot_id)
        inventory = sum(item.quantity for item in self._inventory if item.lot_id == lot_id)
        issues: list[str] = []
        if consumed > lot.quantity:
            issues.append("transformation inputs exceed recorded lot quantity")
        if lot.kind == "finished" and produced != lot.quantity:
            issues.append("transformation outputs do not match recorded lot quantity")
        if shipped > lot.quantity:
            issues.append("shipments exceed recorded lot quantity")
        if inventory > lot.quantity:
            issues.append("inventory exceeds recorded lot quantity")
        return QuantityReconciliation(lot_id, lot.quantity, consumed, produced,
                                      shipped, inventory, tuple(issues))

    def find_traceability_gaps(self, lot_id: str) -> tuple[str, ...]:
        """Report missing recorded links without hypothesizing replacement links."""
        self._require_lot(lot_id)
        involved = {lot_id, *self.find_descendant_lots(lot_id)}
        gaps: list[str] = []
        for descendant_id in sorted(involved):
            lot = self._lots[descendant_id]
            if lot.kind == "finished" and not any(
                self._graph.nodes[parent]["public"].type == "transformation"
                for parent in self._graph.predecessors(descendant_id)
            ):
                gaps.append(f"{descendant_id}: missing transformation input")
            for shipment in self._shipments:
                if shipment.lot_id != descendant_id or shipment.status != "received":
                    continue
                matching = [position for position in self._inventory
                            if position.lot_id == descendant_id
                            and position.location_id == shipment.to_facility_id]
                if not matching:
                    gaps.append(f"{shipment.id}: received shipment has no inventory position")
                elif matching[0].quantity < shipment.quantity:
                    gaps.append(f"{shipment.id}: inventory quantity below received quantity")
        return tuple(gaps)
