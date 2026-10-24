"""Manifest integrity and the hidden-truth API boundary."""

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import networkx as nx
import pytest
from pydantic import ValidationError

from backend.api.app import create_app
from backend.scenarios.graph import build_trace_graph, public_graph
from backend.scenarios.loader import bundled_manifest, load_manifest


def test_bundled_manifest_has_complete_trace() -> None:
    manifest = bundled_manifest("clean-trace-01")
    assert manifest.scenario.id == "clean-trace-01"
    assert len(manifest.transformations) == 1
    assert len(manifest.shipments) == 2
    assert manifest.ground_truth.affected_units == 800


@pytest.mark.parametrize("change", [
    lambda data: data.pop("ground_truth"),
    lambda data: data["shipments"][0].update(lot_id="UNKNOWN"),
    lambda data: data["lots"].append(data["lots"][0]),
    lambda data: data["ground_truth"].update(correct_containment_scope=["UNKNOWN@DC-EAST"]),
])
def test_loader_rejects_incomplete_or_invalid_manifest(change) -> None:
    data = json.loads(Path(__file__).parents[1].joinpath("scenarios", "clean-trace-01.json").read_text())
    change(data)
    with patch.object(Path, "read_text", return_value=json.dumps(data)):
        with pytest.raises(ValidationError):
            load_manifest(Path("clean-trace-01.json"))


def test_loader_rejects_malformed_json_and_wrong_filename() -> None:
    with patch.object(Path, "read_text", return_value="{"):
        with pytest.raises(json.JSONDecodeError):
            load_manifest(Path("clean-trace-01.json"))
    contents = Path(__file__).parents[1].joinpath("scenarios", "clean-trace-01.json").read_text()
    with patch.object(Path, "read_text", return_value=contents):
        with pytest.raises(ValueError, match="filename"):
            load_manifest(Path("wrong.json"))


def test_graph_integrity_and_public_projection() -> None:
    manifest = bundled_manifest("clean-trace-01")
    graph = build_trace_graph(manifest)
    assert nx.is_directed_acyclic_graph(graph)
    assert nx.has_path(graph, "ING-1042", "DC-EAST")
    assert nx.has_path(graph, "ING-1042", "STORE-014")
    public = public_graph(manifest)
    assert {node.id for node in public.nodes} == set(graph.nodes)
    assert {edge.id for edge in public.edges} == {"TX-210:in:ING-1042", "TX-210:out:LOT-A71", "TX-210:out:LOT-A72", "SHIP-701", "SHIP-702"}
    assert all(edge.source in graph and edge.target in graph for edge in public.edges)
    serialized = public.model_dump_json()
    for secret in ("ground_truth", "affected_units", "correct_containment_scope", "expected_outcome"):
        assert secret not in serialized


def test_api_never_serializes_hidden_truth() -> None:
    app = create_app()

    async def request(path: str) -> str:
        messages = []

        async def receive() -> dict:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict) -> None:
            messages.append(message)

        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                 "method": "GET", "scheme": "http", "path": path, "raw_path": path.encode(),
                 "query_string": b"", "root_path": "", "headers": [],
                 "server": ("localhost", 80), "client": ("127.0.0.1", 1234)}
        await app(scope, receive, send)
        assert messages[0]["status"] == 200
        return messages[1]["body"].decode()

    async def check() -> None:
        for path in ("/api/scenarios", "/api/scenarios/clean-trace-01/graph"):
            body = await request(path)
            for secret in ("ground_truth", "affected_units", "correct_containment_scope", "expected_outcome"):
                assert secret not in body

    asyncio.run(check())
