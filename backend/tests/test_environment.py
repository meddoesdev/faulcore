"""Phase 1 checks that required backend packages are importable."""

from importlib import import_module

import pytest


@pytest.mark.parametrize(
    "module_name",
    ("fastapi", "networkx", "pydantic", "uvicorn"),
)
def test_required_backend_dependency_is_importable(module_name: str) -> None:
    """Fail early when a required backend runtime dependency is unavailable."""
    assert import_module(module_name) is not None
