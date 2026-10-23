"""Deterministic public exposure graph from trace records, never ground truth."""

import networkx as nx

from backend.models.api import GraphData, GraphEdge, GraphNode
from backend.scenarios.loader import ScenarioManifest


def build_trace_graph(manifest: ScenarioManifest) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    inventory = {(p.lot_id, p.location_id): p for p in manifest.inventory}
    for lot in manifest.lots:
        graph.add_node(lot.id, public=GraphNode(
            id=lot.id,
            type="supplier_lot" if lot.kind == "ingredient" else "facility",
            label=f"{'Ingredient' if lot.kind == 'ingredient' else 'Finished lot'} {lot.id}",
            exposure="possible",
            metadata={"product_id": lot.product_id, "units": lot.quantity,
                      "origin_facility_id": lot.origin_facility_id},
        ))
    for event in manifest.transformations:
        graph.add_node(event.id, public=GraphNode(
            id=event.id, type="transformation", label=f"Transformation {event.id}",
            exposure="possible", metadata={"facility_id": event.facility_id},
        ))
        for item in event.inputs:
            edge = GraphEdge(id=f"{event.id}:in:{item.lot_id}", source=item.lot_id,
                             target=event.id, exposure="possible", label="consumed by")
            graph.add_edge(edge.source, edge.target, key=edge.id, public=edge)
        for item in event.outputs:
            edge = GraphEdge(id=f"{event.id}:out:{item.lot_id}", source=event.id,
                             target=item.lot_id, exposure="possible", label="produced")
            graph.add_edge(edge.source, edge.target, key=edge.id, public=edge)
    for record_id in manifest.missing_or_corrupted_records:
        graph.add_node(record_id, public=GraphNode(
            id=record_id, type="transformation", label=f"Missing record {record_id}",
            exposure="possible", metadata={"record_status": "missing"},
        ))
    destinations = {shipment.to_facility_id for shipment in manifest.shipments}
    for facility in manifest.topology:
        if facility.id not in destinations:
            continue
        position_units = sum(p.quantity for p in manifest.inventory if p.location_id == facility.id)
        graph.add_node(facility.id, public=GraphNode(
            id=facility.id, type=facility.type, label=facility.name,
            exposure="possible", metadata={"units": position_units},
        ))
    for shipment in manifest.shipments:
        position = inventory.get((shipment.lot_id, shipment.to_facility_id))
        if position is not None:
            node = graph.nodes[shipment.to_facility_id]["public"]
            if node.inventory_state is None and position.status in {"available", "held"}:
                node.inventory_state = position.status
        edge = GraphEdge(id=shipment.id, source=shipment.lot_id,
                         target=shipment.to_facility_id, exposure="possible", label="shipment")
        graph.add_edge(edge.source, edge.target, key=edge.id, public=edge)
    if not nx.is_directed_acyclic_graph(graph):
        raise ValueError("trace graph must be acyclic")
    return graph


def public_graph(manifest: ScenarioManifest) -> GraphData:
    graph = build_trace_graph(manifest)
    return GraphData(
        scenario_id=manifest.scenario.id,
        nodes=[data["public"] for _, data in graph.nodes(data=True)],
        edges=[data["public"] for _, _, _, data in graph.edges(keys=True, data=True)],
    )
