from __future__ import annotations

from typing import Any, Dict, List

from app.models.schemas import SimulateRequest


def _parse_edges(request: SimulateRequest) -> List[Dict[str, Any]]:
    return [e.model_dump() for e in request.edges]


def _parse_nodes_by_type(nodes: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    nodes_by_type: Dict[str, List[Dict[str, Any]]] = {}
    for n in nodes:
        t = str(n.get("type") or "")
        nodes_by_type.setdefault(t, []).append(n)
    return nodes_by_type


