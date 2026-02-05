from __future__ import annotations

from typing import Dict, Any

import pandapower as pp  # type: ignore[import-not-found]
import pytest

from app.helper.elements.ac.registry import build_ac_registry
from app.helper.elements.base import ElementContext


@pytest.fixture
def net() -> pp.pandapowerNet:  # type: ignore[name-defined]
    """Return a fresh empty pandapower network for each test."""
    return pp.create_empty_network()


@pytest.fixture
def element_context(net: pp.pandapowerNet) -> ElementContext:  # type: ignore[name-defined]
    return ElementContext(net=net)


@pytest.fixture
def ac_registry():
    return build_ac_registry()


def make_node(node_id: str, type_: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to build a node dict similar to ReactFlow node.dump()."""
    return {"id": node_id, "type": type_, "data": data}



