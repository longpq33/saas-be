from __future__ import annotations

import time
from typing import Any, Dict, List

import pandapower as pp

from app.helper.network_creation import (
    _add_buses,
    _add_ext_grids,
    _add_gens,
    _add_lines_from_edges,
    _add_loads,
    _add_motors,
    _add_sgens,
    _add_shunts,
    _add_storages,
    _add_switches,
    _add_trafo3w,
    _add_transformers,
    _ensure_slack,
)
from app.helper.result_collection import _collect_simulation_results
from app.helper.validation import _validate_network
from app.models.schemas import (
    SimulateRequest,
    SimulateResponse,
    CreationStatus,
)


def simulate_from_reactflow(req: SimulateRequest) -> SimulateResponse:
    start = time.perf_counter()
    warnings: List[str] = []
    all_creation_failed: List[CreationStatus] = []
    element_status: Dict[str, CreationStatus] = {}

    # Parse nodes and edges
    all_nodes = [n.model_dump() for n in req.nodes]
    bus_nodes = [n for n in all_nodes if n.get("type") == "bus"]
    load_nodes = [n for n in all_nodes if n.get("type") == "load"]
    ext_grid_nodes = [n for n in all_nodes if n.get("type") == "ext_grid"]
    gen_nodes = [n for n in all_nodes if n.get("type") == "gen"]
    sgen_nodes = [n for n in all_nodes if n.get("type") == "sgen"]
    motor_nodes = [n for n in all_nodes if n.get("type") == "motor"]
    shunt_nodes = [n for n in all_nodes if n.get("type") == "shunt"]
    storage_nodes = [n for n in all_nodes if n.get("type") == "storage"]
    transformer_nodes = [n for n in all_nodes if n.get("type") == "transformer"]
    trafo3w_nodes = [n for n in all_nodes if n.get("type") == "trafo3w"]
    switch_nodes = [n for n in all_nodes if n.get("type") == "switch"]
    edges = [e.model_dump() for e in req.edges]

    # Create network and add buses first
    net = pp.create_empty_network()
    bus_index_by_node_id, _ = _add_buses(net, bus_nodes)

    # Validate network before creating elements
    validation_errors = _validate_network(all_nodes, edges, bus_index_by_node_id)

    # If validation errors exist, return early with errors
    if validation_errors:
        slack_bus_id = ""
        if ext_grid_nodes:
            first_ext_grid = ext_grid_nodes[0]
            slack_bus_id = str(first_ext_grid.get("data", {}).get("busId", ""))

        return SimulateResponse(
            summary={
                "converged": False,
                "runtime_ms": int((time.perf_counter() - start) * 1000),
                "slack_bus_id": slack_bus_id,
            },
            bus_by_id={},
            res_bus=[],
            warnings=warnings,
            errors={"validation": [e.model_dump() for e in validation_errors], "creation": [], "simulation": []},
            element_status={},
            results={},
        )

    # Track element indices for results collection
    load_index_by_node_id: Dict[str, int] = {}
    gen_index_by_node_id: Dict[str, int] = {}
    sgen_index_by_node_id: Dict[str, int] = {}
    motor_index_by_node_id: Dict[str, int] = {}
    shunt_index_by_node_id: Dict[str, int] = {}
    storage_index_by_node_id: Dict[str, int] = {}
    trafo3w_index_by_node_id: Dict[str, int] = {}

    # Add elements and track creation status
    _, failed = _add_loads(net, load_nodes, bus_index_by_node_id)
    all_creation_failed.extend(failed)
    # Track successful loads
    for node in load_nodes:
        node_id = node.get("id", "")
        if node_id not in [f.element_id for f in failed]:
            # Find the index in net.load
            bus_id = str(node.get("data", {}).get("busId", ""))
            if bus_id in bus_index_by_node_id:
                # Find matching load by bus
                for idx in net.load.index:
                    if net.load.loc[idx, "bus"] == bus_index_by_node_id[bus_id]:
                        load_index_by_node_id[node_id] = int(idx)
                        break

    _, failed = _add_ext_grids(net, ext_grid_nodes, bus_index_by_node_id)
    all_creation_failed.extend(failed)

    _, failed = _add_gens(net, gen_nodes, bus_index_by_node_id)
    all_creation_failed.extend(failed)
    # Track successful gens
    for node in gen_nodes:
        node_id = node.get("id", "")
        if node_id not in [f.element_id for f in failed]:
            bus_id = str(node.get("data", {}).get("busId", ""))
            if bus_id in bus_index_by_node_id:
                for idx in net.gen.index:
                    if net.gen.loc[idx, "bus"] == bus_index_by_node_id[bus_id]:
                        gen_index_by_node_id[node_id] = int(idx)
                        break

    _, failed = _add_sgens(net, sgen_nodes, bus_index_by_node_id)
    all_creation_failed.extend(failed)
    # Track successful sgens
    for node in sgen_nodes:
        node_id = node.get("id", "")
        if node_id not in [f.element_id for f in failed]:
            bus_id = str(node.get("data", {}).get("busId", ""))
            if bus_id in bus_index_by_node_id:
                for idx in net.sgen.index:
                    if net.sgen.loc[idx, "bus"] == bus_index_by_node_id[bus_id]:
                        sgen_index_by_node_id[node_id] = int(idx)
                        break

    _, failed = _add_motors(net, motor_nodes, bus_index_by_node_id)
    all_creation_failed.extend(failed)
    # Track successful motors
    for node in motor_nodes:
        node_id = node.get("id", "")
        if node_id not in [f.element_id for f in failed]:
            bus_id = str(node.get("data", {}).get("busId", ""))
            if bus_id in bus_index_by_node_id:
                for idx in net.motor.index:
                    if net.motor.loc[idx, "bus"] == bus_index_by_node_id[bus_id]:
                        motor_index_by_node_id[node_id] = int(idx)
                        break

    _, failed = _add_shunts(net, shunt_nodes, bus_index_by_node_id)
    all_creation_failed.extend(failed)
    # Track successful shunts
    for node in shunt_nodes:
        node_id = node.get("id", "")
        if node_id not in [f.element_id for f in failed]:
            bus_id = str(node.get("data", {}).get("busId", ""))
            if bus_id in bus_index_by_node_id:
                for idx in net.shunt.index:
                    if net.shunt.loc[idx, "bus"] == bus_index_by_node_id[bus_id]:
                        shunt_index_by_node_id[node_id] = int(idx)
                        break

    _, failed = _add_storages(net, storage_nodes, bus_index_by_node_id)
    all_creation_failed.extend(failed)
    # Track successful storages
    for node in storage_nodes:
        node_id = node.get("id", "")
        if node_id not in [f.element_id for f in failed]:
            bus_id = str(node.get("data", {}).get("busId", ""))
            if bus_id in bus_index_by_node_id:
                for idx in net.storage.index:
                    if net.storage.loc[idx, "bus"] == bus_index_by_node_id[bus_id]:
                        storage_index_by_node_id[node_id] = int(idx)
                        break

    line_edges, failed = _add_lines_from_edges(net, edges, bus_index_by_node_id)
    all_creation_failed.extend(failed)
    line_index_by_edge_id = {edge_id: line_idx for line_idx, edge_id, _ in line_edges}

    trafo_edges, failed = _add_transformers(net, transformer_nodes, bus_index_by_node_id)
    all_creation_failed.extend(failed)
    trafo_index_by_node_id = {node_id: trafo_idx for trafo_idx, node_id, _ in trafo_edges}

    _, failed = _add_trafo3w(net, trafo3w_nodes, bus_index_by_node_id)
    all_creation_failed.extend(failed)
    # Track successful trafo3w
    for node in trafo3w_nodes:
        node_id = node.get("id", "")
        if node_id not in [f.element_id for f in failed]:
            data = node.get("data", {})
            hv_bus_id = str(data.get("hvBusId", ""))
            if hv_bus_id in bus_index_by_node_id:
                for idx in net.trafo3w.index:
                    if net.trafo3w.loc[idx, "hv_bus"] == bus_index_by_node_id[hv_bus_id]:
                        trafo3w_index_by_node_id[node_id] = int(idx)
                        break

    # Create switches from line edges (if switch config in edge.data)
    for line_idx, edge_id, edge_data in line_edges:
        switch_data = edge_data.get("switch")
        if not switch_data or not switch_data.get("enabled"):
            continue

        switch_side = str(switch_data.get("side", "source"))
        edge = next((e for e in edges if e.get("id") == edge_id), None)
        if not edge:
            continue

        switch_bus_id = edge.get("source") if switch_side == "source" else edge.get("target")
        if not switch_bus_id or switch_bus_id not in bus_index_by_node_id:
            continue

        try:
            pp.create_switch(
                net,
                bus=bus_index_by_node_id[switch_bus_id],
                element=line_idx,
                et="l",
                closed=bool(switch_data.get("closed", True)),
                type=str(switch_data.get("type", "")) if switch_data.get("type") else None,
                z_ohm=float(switch_data.get("z_ohm", 0.0)) if switch_data.get("z_ohm") is not None else None,
                in_service=bool(switch_data.get("in_service", True)),
            )
        except Exception as e:  # noqa: BLE001
            all_creation_failed.append(
                CreationStatus(
                    element_id=edge_id,
                    element_type="switch",
                    success=False,
                    error=str(e),
                )
            )

    # Create switches from switch nodes
    _, failed = _add_switches(net, switch_nodes, bus_index_by_node_id, line_index_by_edge_id, trafo_index_by_node_id)
    all_creation_failed.extend(failed)

    # Build element_status dict
    for node in all_nodes:
        node_id = node.get("id", "")
        node_type = node.get("type", "")
        failed_status = next((f for f in all_creation_failed if f.element_id == node_id), None)
        if failed_status:
            element_status[node_id] = failed_status
        else:
            element_status[node_id] = CreationStatus(
                element_id=node_id,
                element_type=node_type,
                success=True,
                error=None,
            )

    # Also track edge status
    for edge in edges:
        edge_id = edge.get("id", "")
        failed_status = next((f for f in all_creation_failed if f.element_id == edge_id), None)
        if failed_status:
            element_status[edge_id] = failed_status
        else:
            element_status[edge_id] = CreationStatus(
                element_id=edge_id,
                element_type="line",
                success=True,
                error=None,
            )

    try:
        _ensure_slack(net)
    except ValueError as e:
        warnings.append(str(e))
        return SimulateResponse(
            summary={
                "converged": False,
                "runtime_ms": int((time.perf_counter() - start) * 1000),
                "slack_bus_id": "",
            },
            bus_by_id={},
            res_bus=[],
            warnings=warnings,
            errors={
                "validation": [],
                "creation": [f.model_dump() for f in all_creation_failed],
                "simulation": [str(e)],
            },
            element_status={k: v.model_dump() for k, v in element_status.items()},
            results={},
        )

    converged = False
    try:
        pp.runpp(
            net,
            algorithm=req.settings.algorithm,
            max_iteration=req.settings.max_iter,
            tolerance_mva=req.settings.tolerance_mva,
            init="auto",
        )
        converged = bool(net.get("converged", False))
    except Exception as e:  # noqa: BLE001
        warnings.append(str(e))

    runtime_ms = int((time.perf_counter() - start) * 1000)

    # Collect simulation results
    simulation_errors: List[str] = []
    if not converged:
        simulation_errors.append("Power flow did not converge")

    results = _collect_simulation_results(
        net=net,
        converged=converged,
        load_node_ids=[n.get("id", "") for n in load_nodes],
        gen_node_ids=[n.get("id", "") for n in gen_nodes],
        sgen_node_ids=[n.get("id", "") for n in sgen_nodes],
        motor_node_ids=[n.get("id", "") for n in motor_nodes],
        shunt_node_ids=[n.get("id", "") for n in shunt_nodes],
        storage_node_ids=[n.get("id", "") for n in storage_nodes],
        line_edge_ids=[e.get("id", "") for e in edges],
        trafo_node_ids=[n.get("id", "") for n in transformer_nodes],
        trafo3w_node_ids=[n.get("id", "") for n in trafo3w_nodes],
        load_index_by_node_id=load_index_by_node_id,
        gen_index_by_node_id=gen_index_by_node_id,
        sgen_index_by_node_id=sgen_index_by_node_id,
        motor_index_by_node_id=motor_index_by_node_id,
        shunt_index_by_node_id=shunt_index_by_node_id,
        storage_index_by_node_id=storage_index_by_node_id,
        line_index_by_edge_id=line_index_by_edge_id,
        trafo_index_by_node_id=trafo_index_by_node_id,
        trafo3w_index_by_node_id=trafo3w_index_by_node_id,
    )

    bus_by_id: Dict[str, Dict[str, Any]] = {}
    if converged and hasattr(net, "res_bus"):
        for node_id, bus_idx in bus_index_by_node_id.items():
            if bus_idx not in net.res_bus.index:
                continue
            row = net.res_bus.loc[bus_idx]
            bus_by_id[node_id] = {
                "vm_pu": float(row.get("vm_pu")),
                "va_degree": float(row.get("va_degree")),
                "p_mw": float(row.get("p_mw")),
                "q_mvar": float(row.get("q_mvar")),
            }

    res_bus_records: List[Dict[str, Any]] = []
    if converged and hasattr(net, "res_bus"):
        res_bus_records = net.res_bus.reset_index().to_dict(orient="records")

    # Get first ext_grid bus as slack_bus_id for summary
    slack_bus_id = ""
    if ext_grid_nodes:
        first_ext_grid = ext_grid_nodes[0]
        slack_bus_id = str(first_ext_grid.get("data", {}).get("busId", ""))

    return SimulateResponse(
        summary={
            "converged": converged,
            "runtime_ms": runtime_ms,
            "slack_bus_id": slack_bus_id,
        },
        bus_by_id=bus_by_id,
        res_bus=res_bus_records,
        warnings=warnings,
        errors={
            "validation": [],
            "creation": [f.model_dump() for f in all_creation_failed],
            "simulation": simulation_errors,
        },
        element_status={k: v.model_dump() for k, v in element_status.items()},
        results=results,
    )

