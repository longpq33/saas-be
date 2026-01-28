from __future__ import annotations

import pytest

from app.models.schemas import ReactFlowEdge, ReactFlowNode, RunSettings, SimulateRequest
from app.services.simulate import simulate_from_reactflow


@pytest.mark.parametrize("return_network", ["summary", "tables"])
def test_simulate_happy_case_converges_and_returns_network(return_network: str) -> None:
    # 2 buses
    bus1 = ReactFlowNode(
        id="bus-1",
        type="bus",
        data={
            "name": "Bus 1",
            "vn_kv": 22,
            "min_vm_pu": 0.95,
            "max_vm_pu": 1.05,
            "in_service": True,
        },
    )
    bus2 = ReactFlowNode(
        id="bus-2",
        type="bus",
        data={
            "name": "Bus 2",
            "vn_kv": 22,
            "min_vm_pu": 0.95,
            "max_vm_pu": 1.05,
            "in_service": True,
        },
    )

    # ext_grid at bus-1
    ext_grid = ReactFlowNode(
        id="ext-grid-1",
        type="ext_grid",
        data={
            "name": "Grid",
            "busId": "bus-1",
            "vm_pu": 1.02,
            "va_degree": 0,
            "in_service": True,
        },
    )

    # load at bus-2
    load = ReactFlowNode(
        id="load-1",
        type="load",
        data={
            "name": "Load",
            "busId": "bus-2",
            "p_mw": 10,
            "q_mvar": 4,
            "scaling": 1,
            "in_service": True,
        },
    )

    # single valid line edge bus-1 <-> bus-2
    line = ReactFlowEdge(
        id="e-bus1-bus2",
        source="bus-1",
        target="bus-2",
        data={
            "name": "Line 1",
            "std_type": "NAYY 4x50 SE",
            "length_km": 1,
            "parallel": 1,
            "df": 1,
            "in_service": True,
        },
    )

    req = SimulateRequest(
        nodes=[bus1, bus2, ext_grid, load],
        edges=[line],
        settings=RunSettings(return_network=return_network),
    )

    res = simulate_from_reactflow(req)

    assert res.summary.converged is True
    assert res.errors == {} or (len(res.errors.get("validation", [])) == 0 and len(res.errors.get("powerflow", [])) == 0)

    # Core results should exist
    assert "bus-1" in res.bus_by_id
    assert "bus-2" in res.bus_by_id
    assert res.results.get("lines") is not None

    # Network payload should exist
    assert res.network is not None
    assert "meta" in res.network

    if return_network == "summary":
        # summary mode: only meta and counts
        assert "counts" in res.network["meta"]
        assert res.network["meta"]["counts"]["bus"] == 2
    else:
        # tables mode: tables + results
        assert "tables" in res.network
        assert "results" in res.network
        assert len(res.network["tables"]["bus"]) == 2
        assert len(res.network["tables"]["line"]) == 1
        assert len(res.network["tables"]["load"]) == 1
        assert len(res.network["tables"]["ext_grid"]) == 1
        # When converged, res_bus should exist in results
        assert len(res.network["results"]["res_bus"]) == 2

