"""Strict, private scenario manifest loading. Never serialize a manifest to an API."""

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.models.api import Scenario


class ManifestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Facility(ManifestModel):
    id: str = Field(min_length=1)
    type: Literal["supplier", "processing_plant", "distribution_center", "store"]
    name: str = Field(min_length=1)


class Product(ManifestModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: Literal["ingredient", "finished"]


class Lot(ManifestModel):
    id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    kind: Literal["ingredient", "finished"]
    quantity: int = Field(gt=0)
    origin_facility_id: str = Field(min_length=1)


class LotQuantity(ManifestModel):
    lot_id: str = Field(min_length=1)
    quantity: int = Field(gt=0)


class Transformation(ManifestModel):
    id: str = Field(min_length=1)
    facility_id: str = Field(min_length=1)
    timestamp: datetime
    inputs: list[LotQuantity] = Field(min_length=1)
    outputs: list[LotQuantity] = Field(min_length=1)


class Shipment(ManifestModel):
    id: str = Field(min_length=1)
    lot_id: str = Field(min_length=1)
    from_facility_id: str = Field(min_length=1)
    to_facility_id: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    status: Literal["in_transit", "received"]
    timestamp: datetime


class Inventory(ManifestModel):
    lot_id: str = Field(min_length=1)
    location_id: str = Field(min_length=1)
    quantity: int = Field(ge=0)
    status: Literal["available", "allocated", "held", "shipped"]


class Evidence(ManifestModel):
    id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    text: str = Field(min_length=1)


class GroundTruth(ManifestModel):
    affected_lot_ids: list[str] = Field(min_length=1)
    affected_units: int = Field(gt=0)
    correct_containment_scope: list[str] = Field(min_length=1)
    expected_outcome: str = Field(min_length=1)


ActionName = Literal["run_trace_diagnostics", "place_inventory_hold", "block_fulfillment", "escalate_incident"]


class ScenarioManifest(ManifestModel):
    scenario: Scenario
    seed: int = Field(ge=0)
    topology: list[Facility] = Field(min_length=1)
    products: list[Product] = Field(min_length=1)
    lots: list[Lot] = Field(min_length=1)
    transformations: list[Transformation] = Field(min_length=1)
    shipments: list[Shipment] = Field(min_length=1)
    inventory: list[Inventory] = Field(min_length=1)
    initial_alert: Evidence
    decoy_evidence: list[Evidence]
    missing_or_corrupted_records: list[str]
    permitted_actions: list[ActionName] = Field(min_length=1)
    action_consequences: dict[ActionName, str]
    verification_criteria: list[str] = Field(min_length=1)
    ground_truth: GroundTruth

    @model_validator(mode="after")
    def validate_references(self) -> "ScenarioManifest":
        def unique(items: list, label: str) -> dict[str, object]:
            by_id = {item.id: item for item in items}
            if len(by_id) != len(items):
                raise ValueError(f"duplicate {label} identifier")
            return by_id

        facilities = unique(self.topology, "facility")
        products = unique(self.products, "product")
        lots = unique(self.lots, "lot")
        transformations = unique(self.transformations, "transformation")
        shipments = unique(self.shipments, "shipment")
        evidence = unique([self.initial_alert, *self.decoy_evidence], "evidence")
        all_ids = [*facilities, *products, *lots, *transformations, *shipments, *evidence]
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("manifest identifiers must be globally unique")
        if not all(lot.product_id in products and lot.origin_facility_id in facilities
                   and lot.kind == products[lot.product_id].kind for lot in self.lots):
            raise ValueError("lot references unknown or mismatched product/facility")
        for event in self.transformations:
            if event.facility_id not in facilities:
                raise ValueError("transformation references unknown facility")
            if (len({item.lot_id for item in event.inputs}) != len(event.inputs)
                    or len({item.lot_id for item in event.outputs}) != len(event.outputs)):
                raise ValueError("duplicate lot reference within transformation")
            for item in [*event.inputs, *event.outputs]:
                if item.lot_id not in lots or item.quantity > lots[item.lot_id].quantity:
                    raise ValueError("transformation references unknown lot or excessive quantity")
        for shipment in self.shipments:
            if (shipment.lot_id not in lots or shipment.from_facility_id not in facilities
                    or shipment.to_facility_id not in facilities
                    or shipment.quantity > lots[shipment.lot_id].quantity):
                raise ValueError("shipment references unknown lot/facility or excessive quantity")
        for position in self.inventory:
            if position.lot_id not in lots or position.location_id not in facilities:
                raise ValueError("inventory references unknown lot or facility")
        if len({(p.lot_id, p.location_id) for p in self.inventory}) != len(self.inventory):
            raise ValueError("duplicate inventory position")
        if set(self.ground_truth.affected_lot_ids) - lots.keys():
            raise ValueError("ground truth references unknown lot")
        if len(set(self.ground_truth.affected_lot_ids)) != len(self.ground_truth.affected_lot_ids):
            raise ValueError("duplicate affected lot")
        positions = {f"{p.lot_id}@{p.location_id}" for p in self.inventory}
        if set(self.ground_truth.correct_containment_scope) - positions:
            raise ValueError("ground truth references unknown inventory position")
        if len(set(self.ground_truth.correct_containment_scope)) != len(self.ground_truth.correct_containment_scope):
            raise ValueError("duplicate containment position")
        if len(set(self.permitted_actions)) != len(self.permitted_actions):
            raise ValueError("duplicate permitted action")
        if set(self.permitted_actions) != set(self.action_consequences):
            raise ValueError("action consequences must match permitted actions")
        return self


def load_manifest(path: Path) -> ScenarioManifest:
    """Load and validate one manifest; validation errors are intentionally not hidden."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    manifest = ScenarioManifest.model_validate(raw)
    if path.stem != manifest.scenario.id:
        raise ValueError("manifest filename must match scenario ID")
    return manifest


def bundled_manifest(scenario_id: str) -> ScenarioManifest:
    if scenario_id != "clean-trace-01":
        raise FileNotFoundError(f"scenario {scenario_id} is not implemented")
    return load_manifest(Path(__file__).with_name("clean-trace-01.json"))
