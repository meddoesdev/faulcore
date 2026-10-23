"""Private, in-memory operational state; not an agent action interface.

Policy and action dispatch are deliberately deferred to Phases 5 and 6.
No hidden ground truth is retained here.
"""

import copy
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal

import networkx as nx

from backend.scenarios.graph import build_trace_graph
from backend.scenarios.loader import ScenarioManifest


_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_AUDIT_EPOCH = datetime(2026, 10, 21, tzinfo=timezone.utc)


@dataclass
class InventoryBalances:
    available: int = 0
    allocated: int = 0
    held: int = 0
    shipped: int = 0

    def total(self) -> int:
        return self.available + self.allocated + self.held + self.shipped


@dataclass(frozen=True)
class OrderAllocation:
    lot_id: str
    location_id: str
    quantity: int


@dataclass
class OrderState:
    order_id: str
    product_id: str
    allocations: list[OrderAllocation] = field(default_factory=list)
    status: Literal["allocated", "flagged", "shipped"] = "allocated"


@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    timestamp: str
    actor: str
    action: str
    inputs: dict[str, str | int]
    result: str


@dataclass(frozen=True)
class HoldResult:
    moved_units: int
    flagged_order_ids: tuple[str, ...]
    exception_shipment_ids: tuple[str, ...]
    duplicate: bool


class ScenarioState:
    """Scenario-specific inventory/order state with a separate append-only audit."""

    def __init__(self, manifest: ScenarioManifest) -> None:
        self.scenario_id = manifest.scenario.id
        self._lot_products = {lot.id: lot.product_id for lot in manifest.lots}
        self._locations = {facility.id for facility in manifest.topology}
        self._graph = nx.freeze(build_trace_graph(manifest))
        self._initial_inventory: dict[tuple[str, str], InventoryBalances] = {}
        for position in manifest.inventory:
            balances = InventoryBalances()
            setattr(balances, position.status, position.quantity)
            self._initial_inventory[(position.lot_id, position.location_id)] = balances
        self._initial_shipments = {shipment.id: (shipment.lot_id, shipment.status)
                                   for shipment in manifest.shipments}
        self._inventory = copy.deepcopy(self._initial_inventory)
        self._shipments = {shipment_id: status for shipment_id, (_, status)
                           in self._initial_shipments.items()}
        self._orders: dict[str, OrderState] = {}
        self._audit_events: list[AuditEvent] = []
        self._initial_snapshot = self.snapshot_bytes()

    @property
    def inventory(self) -> dict[tuple[str, str], InventoryBalances]:
        return copy.deepcopy(self._inventory)

    @property
    def shipments(self) -> dict[str, str]:
        return self._shipments.copy()

    @property
    def orders(self) -> dict[str, OrderState]:
        return copy.deepcopy(self._orders)

    @property
    def audit_events(self) -> tuple[AuditEvent, ...]:
        return tuple(copy.deepcopy(self._audit_events))

    def _audit(self, action: str, inputs: dict[str, str | int], result: str) -> None:
        sequence = len(self._audit_events) + 1
        self._audit_events.append(AuditEvent(
            sequence=sequence,
            timestamp=(_AUDIT_EPOCH + timedelta(seconds=sequence)).isoformat(),
            actor="simulator",
            action=action,
            inputs=inputs,
            result=result,
        ))

    def _require_position(self, lot_id: str, location_id: str) -> InventoryBalances:
        if lot_id not in self._lot_products or location_id not in self._locations:
            raise ValueError("unknown lot or location ID")
        position = self._inventory.get((lot_id, location_id))
        if position is None:
            raise ValueError("unknown inventory position")
        if lot_id not in self._graph or location_id not in self._graph or not nx.has_path(
            self._graph, lot_id, location_id
        ):
            raise ValueError("no recorded evidence path for inventory position")
        return position

    def allocate_order(self, order_id: str, product_id: str, lot_id: str,
                       location_id: str, quantity: int) -> OrderState:
        """Simulate normal order allocation; never exposed as an agent action."""
        if not isinstance(order_id, str) or not _IDENTIFIER.fullmatch(order_id):
            raise ValueError("order ID must be a structured identifier")
        if type(quantity) is not int or quantity <= 0:
            raise ValueError("allocation quantity must be a positive integer")
        position = self._require_position(lot_id, location_id)
        if self._lot_products[lot_id] != product_id:
            raise ValueError("lot does not belong to product")
        if position.available < quantity:
            raise ValueError("insufficient available inventory")
        order = self._orders.get(order_id)
        if order is not None and (order.product_id != product_id or order.status != "allocated"):
            raise ValueError("order cannot receive this allocation")
        if order is None:
            order = OrderState(order_id=order_id, product_id=product_id)
            self._orders[order_id] = order
        position.available -= quantity
        position.allocated += quantity
        order.allocations.append(OrderAllocation(lot_id, location_id, quantity))
        self._audit("allocate_order", {"order_id": order_id, "product_id": product_id,
                                       "lot_id": lot_id, "location_id": location_id,
                                       "quantity": quantity}, "allocated")
        return copy.deepcopy(order)

    def place_hold(self, lot_id: str, location_id: str) -> HoldResult:
        """Primitive used only after later policy approval; currently not API-wired."""
        position = self._require_position(lot_id, location_id)
        moved = position.available
        position.available = 0
        position.held += moved
        flagged_orders: list[str] = []
        for order in self._orders.values():
            if order.status == "allocated" and any(
                allocation.lot_id == lot_id and allocation.location_id == location_id
                for allocation in order.allocations
            ):
                order.status = "flagged"
                flagged_orders.append(order.order_id)
        exception_shipments: list[str] = []
        for shipment_id, (shipment_lot_id, _) in self._initial_shipments.items():
            if shipment_lot_id == lot_id and self._shipments[shipment_id] == "in_transit":
                self._shipments[shipment_id] = "exception"
                exception_shipments.append(shipment_id)
        duplicate = moved == 0 and not flagged_orders and not exception_shipments
        self._audit("place_hold", {"lot_id": lot_id, "location_id": location_id},
                    "duplicate" if duplicate else "held")
        return HoldResult(moved, tuple(sorted(flagged_orders)),
                          tuple(sorted(exception_shipments)), duplicate)

    def dispatch_order(self, order_id: str) -> OrderState:
        """Simulate ordinary fulfillment, refusing orders flagged by a hold."""
        order = self._orders.get(order_id)
        if order is None or order.status != "allocated":
            raise ValueError("order is not dispatchable")
        for allocation in order.allocations:
            if self._inventory[(allocation.lot_id, allocation.location_id)].allocated < allocation.quantity:
                raise ValueError("allocated inventory is insufficient")
        for allocation in order.allocations:
            position = self._inventory[(allocation.lot_id, allocation.location_id)]
            position.allocated -= allocation.quantity
            position.shipped += allocation.quantity
        order.status = "shipped"
        self._audit("dispatch_order", {"order_id": order_id}, "shipped")
        return copy.deepcopy(order)

    def snapshot_bytes(self) -> bytes:
        """Canonical operational snapshot; excludes the append-only lifecycle audit."""
        payload = {
            "scenario_id": self.scenario_id,
            "inventory": [
                {"lot_id": lot_id, "location_id": location_id, **asdict(position)}
                for (lot_id, location_id), position in sorted(self._inventory.items())
            ],
            "shipments": dict(sorted(self._shipments.items())),
            "orders": [asdict(order) for _, order in sorted(self._orders.items())],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def reset(self) -> None:
        self._inventory = copy.deepcopy(self._initial_inventory)
        self._shipments = {shipment_id: status for shipment_id, (_, status)
                           in self._initial_shipments.items()}
        self._orders.clear()
        if self.snapshot_bytes() != self._initial_snapshot:
            raise RuntimeError("reset failed to restore initial operational state")
        self._audit("reset", {"scenario_id": self.scenario_id}, "restored")
