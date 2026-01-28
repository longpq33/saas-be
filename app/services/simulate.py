from __future__ import annotations

import math
import time
from typing import Any, Dict, List

import pandapower as pp
from pandapower.powerflow import LoadflowNotConverged

from app.helper import network_creation, result_collection, validation
from app.helper.net_export import export_network
from app.models.schemas import (
    BusResult,
    CreationStatus,
    SimulateRequest,
    SimulateResponse,
    Summary,
    ValidationError,
)

def _to_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _sanitize_json_floats(obj: Any) -> Any:
    """Đảm bảo JSON hợp lệ: thay NaN/Infinity thành None (null)."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, list):
        return [_sanitize_json_floats(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _sanitize_json_floats(v) for k, v in obj.items()}
    return obj


def simulate_from_reactflow(request: SimulateRequest) -> SimulateResponse:
    """
    Tạo grid power từ ReactFlow nodes/edges và chạy power flow simulation theo pandapower.

    Luồng xử lý:
    1. Chuẩn hoá và tách nodes/edges theo type
    2. Tạo network rỗng với pp.create_empty_network
    3. Tạo buses trước tiên
    4. Validate network
    5. Tạo các phần tử theo thứ tự: lines, transformers, ext_grids, loads/gens/etc, switches
    6. Chạy pp.runpp với settings
    7. Gom kết quả và trả về SimulateResponse
    """
    start_time = time.time()

    # 1. Chuẩn hoá dữ liệu: convert Pydantic models sang dict
    nodes_dict = [node.model_dump() for node in request.nodes]
    edges_dict = []
    for i, edge in enumerate(request.edges):
        edge_dict = edge.model_dump()
        # Đảm bảo mỗi edge có id (fallback nếu không có)
        if not edge_dict.get("id"):
            edge_dict["id"] = f"edge_{i}"
        edges_dict.append(edge_dict)

    # Tách nodes theo type
    bus_nodes = [n for n in nodes_dict if n.get("type") == "bus"]
    ext_grid_nodes = [n for n in nodes_dict if n.get("type") == "ext_grid"]
    load_nodes = [n for n in nodes_dict if n.get("type") == "load"]
    gen_nodes = [n for n in nodes_dict if n.get("type") == "gen"]
    sgen_nodes = [n for n in nodes_dict if n.get("type") == "sgen"]
    motor_nodes = [n for n in nodes_dict if n.get("type") == "motor"]
    shunt_nodes = [n for n in nodes_dict if n.get("type") == "shunt"]
    storage_nodes = [n for n in nodes_dict if n.get("type") == "storage"]
    line_nodes = [n for n in nodes_dict if n.get("type") == "line"]
    transformer_nodes = [n for n in nodes_dict if n.get("type") == "transformer"]
    trafo3w_nodes = [n for n in nodes_dict if n.get("type") == "trafo3w"]
    switch_nodes = [n for n in nodes_dict if n.get("type") == "switch"]

    # Khởi tạo các biến để track kết quả
    element_status: Dict[str, CreationStatus] = {}
    errors: Dict[str, List[ValidationError]] = {}
    warnings: List[str] = []
    converged = False
    slack_bus_id = ""

    # Mapping indices cho các phần tử
    bus_index_by_node_id: Dict[str, int] = {}
    line_index_by_node_id: Dict[str, int] = {}
    trafo_index_by_node_id: Dict[str, int] = {}
    trafo3w_index_by_node_id: Dict[str, int] = {}
    load_index_by_node_id: Dict[str, int] = {}
    gen_index_by_node_id: Dict[str, int] = {}
    sgen_index_by_node_id: Dict[str, int] = {}
    motor_index_by_node_id: Dict[str, int] = {}
    shunt_index_by_node_id: Dict[str, int] = {}
    storage_index_by_node_id: Dict[str, int] = {}

    # Lists để track node/edge IDs cho result collection
    load_node_ids: List[str] = [n["id"] for n in load_nodes]
    gen_node_ids: List[str] = [n["id"] for n in gen_nodes]
    sgen_node_ids: List[str] = [n["id"] for n in sgen_nodes]
    motor_node_ids: List[str] = [n["id"] for n in motor_nodes]
    shunt_node_ids: List[str] = [n["id"] for n in shunt_nodes]
    storage_node_ids: List[str] = [n["id"] for n in storage_nodes]
    transformer_node_ids: List[str] = [n["id"] for n in transformer_nodes]
    trafo3w_node_ids: List[str] = [n["id"] for n in trafo3w_nodes]
    line_node_ids: List[str] = [n["id"] for n in line_nodes]

    try:
        # 2. Tạo network rỗng
        net = pp.create_empty_network()

        # 3. Tạo buses trước tiên
        if not bus_nodes:
            errors["validation"] = [
                ValidationError(
                    element_id="",
                    element_type="network",
                    element_name=None,
                    field="bus",
                    message="At least one bus is required",
                )
            ]
            return _build_error_response(
                start_time, errors, element_status, warnings, slack_bus_id
            )

        bus_index_by_node_id, slack_bus_id = network_creation._add_buses(net, bus_nodes)

        # 4. Validate network
        validation_errors = validation._validate_network(nodes_dict, edges_dict, bus_index_by_node_id)
        if validation_errors:
            errors["validation"] = validation_errors

            # Fail-fast: nếu có lỗi validation thì dừng sớm, không tạo phần tử / không chạy power flow
            for err in validation_errors:
                if err.element_id:
                    element_status.setdefault(
                        err.element_id,
                        CreationStatus(
                            element_id=err.element_id,
                            element_type=err.element_type,
                            success=False,
                            error=err.message,
                        ),
                    )

            return _build_error_response(
                start_time, errors, element_status, warnings, slack_bus_id
            )

        # 5. Tạo các phần tử theo thứ tự phụ thuộc

        # (a) Lines từ Line nodes (NEW model)
        line_created, line_index_by_node_id, line_failed = network_creation._add_lines_from_nodes(
            net, line_nodes, bus_index_by_node_id
        )
        for line_idx, node_id, _ in line_created:
            element_status[node_id] = CreationStatus(
                element_id=node_id, element_type="line", success=True, error=None
            )
        for status in line_failed:
            element_status[status.element_id] = status

        # (b) Transformers (2-winding)
        trafo_edges, trafo_failed = network_creation._add_transformers(
            net, transformer_nodes, bus_index_by_node_id
        )
        for trafo_idx, node_id, _ in trafo_edges:
            trafo_index_by_node_id[node_id] = trafo_idx
            # Track thành công
            element_status[node_id] = CreationStatus(
                element_id=node_id, element_type="transformer", success=True, error=None
            )
        for status in trafo_failed:
            element_status[status.element_id] = status

        # Trafo3W
        trafo3w_count_before = len(net.trafo3w) if hasattr(net, "trafo3w") else 0
        trafo3w_success, trafo3w_failed = network_creation._add_trafo3w(
            net, trafo3w_nodes, bus_index_by_node_id
        )
        # Build trafo3w_index_by_node_id theo thứ tự tạo
        trafo3w_idx = trafo3w_count_before
        for node in trafo3w_nodes:
            node_id = node.get("id", "")
            if any(status.element_id == node_id for status in trafo3w_failed):
                continue
            if trafo3w_idx < len(net.trafo3w):
                trafo3w_index_by_node_id[node_id] = int(net.trafo3w.index[trafo3w_idx])
                element_status[node_id] = CreationStatus(
                    element_id=node_id, element_type="trafo3w", success=True, error=None
                )
                trafo3w_idx += 1
        for status in trafo3w_failed:
            element_status[status.element_id] = status

        # (c) Slack/External grid
        ext_grid_success, ext_grid_failed = network_creation._add_ext_grids(
            net, ext_grid_nodes, bus_index_by_node_id, edges_dict
        )
        # Track thành công cho ext_grid
        for node in ext_grid_nodes:
            node_id = node.get("id", "")
            if not any(status.element_id == node_id for status in ext_grid_failed):
                element_status[node_id] = CreationStatus(
                    element_id=node_id, element_type="ext_grid", success=True, error=None
                )
        for status in ext_grid_failed:
            element_status[status.element_id] = status

        # Xác định slack_bus_id từ ext_grid thực tế trong pandapower network
        if hasattr(net, "ext_grid") and len(net.ext_grid) > 0:
            if len(net.ext_grid) > 1:
                warnings.append("Multiple ext_grids detected; using the first for slack reporting")

            try:
                slack_bus_idx = int(net.ext_grid.iloc[0].bus)
                # reverse map bus index -> node id
                node_id_by_bus_idx = {idx: node_id for node_id, idx in bus_index_by_node_id.items()}
                slack_bus_id = node_id_by_bus_idx.get(slack_bus_idx, slack_bus_id)
            except Exception:  # noqa: BLE001
                # fallback giữ nguyên slack_bus_id hiện tại
                pass

        try:
            network_creation._ensure_slack(net)
        except ValueError as e:
            errors.setdefault("network", []).append(
                ValidationError(
                    element_id="",
                    element_type="network",
                    field="ext_grid",
                    message=str(e),
                )
            )

        # (d) Loads / Gens / SGens / Motors / Shunts / Storages
        # Loads
        load_count_before = len(net.load) if hasattr(net, "load") else 0
        load_success, load_failed = network_creation._add_loads(net, load_nodes, bus_index_by_node_id)
        # Build load_index_by_node_id: map theo thứ tự tạo (chỉ các node thành công)
        load_idx = load_count_before
        for node in load_nodes:
            node_id = node.get("id", "")
            # Skip nếu node này failed
            if any(status.element_id == node_id for status in load_failed):
                continue
            if load_idx < len(net.load):
                load_index_by_node_id[node_id] = int(net.load.index[load_idx])
                element_status[node_id] = CreationStatus(
                    element_id=node_id, element_type="load", success=True, error=None
                )
                load_idx += 1
        for status in load_failed:
            element_status[status.element_id] = status

        # Gens
        gen_count_before = len(net.gen) if hasattr(net, "gen") else 0
        gen_success, gen_failed = network_creation._add_gens(net, gen_nodes, bus_index_by_node_id)
        gen_idx = gen_count_before
        for node in gen_nodes:
            node_id = node.get("id", "")
            if any(status.element_id == node_id for status in gen_failed):
                continue
            if gen_idx < len(net.gen):
                gen_index_by_node_id[node_id] = int(net.gen.index[gen_idx])
                element_status[node_id] = CreationStatus(
                    element_id=node_id, element_type="gen", success=True, error=None
                )
                gen_idx += 1
        for status in gen_failed:
            element_status[status.element_id] = status

        # SGens
        sgen_count_before = len(net.sgen) if hasattr(net, "sgen") else 0
        sgen_success, sgen_failed = network_creation._add_sgens(net, sgen_nodes, bus_index_by_node_id)
        sgen_idx = sgen_count_before
        for node in sgen_nodes:
            node_id = node.get("id", "")
            if any(status.element_id == node_id for status in sgen_failed):
                continue
            if sgen_idx < len(net.sgen):
                sgen_index_by_node_id[node_id] = int(net.sgen.index[sgen_idx])
                element_status[node_id] = CreationStatus(
                    element_id=node_id, element_type="sgen", success=True, error=None
                )
                sgen_idx += 1
        for status in sgen_failed:
            element_status[status.element_id] = status

        # Motors
        motor_count_before = len(net.motor) if hasattr(net, "motor") else 0
        motor_success, motor_failed = network_creation._add_motors(net, motor_nodes, bus_index_by_node_id)
        motor_idx = motor_count_before
        for node in motor_nodes:
            node_id = node.get("id", "")
            if any(status.element_id == node_id for status in motor_failed):
                continue
            if motor_idx < len(net.motor):
                motor_index_by_node_id[node_id] = int(net.motor.index[motor_idx])
                element_status[node_id] = CreationStatus(
                    element_id=node_id, element_type="motor", success=True, error=None
                )
                motor_idx += 1
        for status in motor_failed:
            element_status[status.element_id] = status

        # Shunts
        shunt_count_before = len(net.shunt) if hasattr(net, "shunt") else 0
        shunt_success, shunt_failed = network_creation._add_shunts(net, shunt_nodes, bus_index_by_node_id)
        shunt_idx = shunt_count_before
        for node in shunt_nodes:
            node_id = node.get("id", "")
            if any(status.element_id == node_id for status in shunt_failed):
                continue
            if shunt_idx < len(net.shunt):
                shunt_index_by_node_id[node_id] = int(net.shunt.index[shunt_idx])
                element_status[node_id] = CreationStatus(
                    element_id=node_id, element_type="shunt", success=True, error=None
                )
                shunt_idx += 1
        for status in shunt_failed:
            element_status[status.element_id] = status

        # Storages
        storage_count_before = len(net.storage) if hasattr(net, "storage") else 0
        storage_success, storage_failed = network_creation._add_storages(
            net, storage_nodes, bus_index_by_node_id
        )
        storage_idx = storage_count_before
        for node in storage_nodes:
            node_id = node.get("id", "")
            if any(status.element_id == node_id for status in storage_failed):
                continue
            if storage_idx < len(net.storage):
                storage_index_by_node_id[node_id] = int(net.storage.index[storage_idx])
                element_status[node_id] = CreationStatus(
                    element_id=node_id, element_type="storage", success=True, error=None
                )
                storage_idx += 1
        for status in storage_failed:
            element_status[status.element_id] = status

        # (e) Switches (phụ thuộc line/trafo đã có index)
        switch_success, switch_failed = network_creation._add_switches(
            net, switch_nodes, bus_index_by_node_id, line_index_by_node_id, trafo_index_by_node_id
        )
        # Track thành công cho switches
        for node in switch_nodes:
            node_id = node.get("id", "")
            if not any(status.element_id == node_id for status in switch_failed):
                element_status[node_id] = CreationStatus(
                    element_id=node_id, element_type="switch", success=True, error=None
                )
        for status in switch_failed:
            element_status[status.element_id] = status

        # 6. Chạy power flow với settings
        try:
            pp.runpp(
                net,
                algorithm=request.settings.algorithm,
                max_iteration=request.settings.max_iter,
                tolerance_mva=request.settings.tolerance_mva,
            )
            converged = True
        except LoadflowNotConverged as e:
            converged = False

            # Trả lỗi chi tiết hơn dựa trên thông tin solver
            errors.setdefault("powerflow", []).append(
                ValidationError(
                    element_id="",
                    element_type="network",
                    field="runpp",
                    message=(
                        "Power flow did not converge. "
                        f"algorithm={request.settings.algorithm}, "
                        f"max_iter={request.settings.max_iter}, "
                        f"tolerance_mva={request.settings.tolerance_mva}. "
                        f"detail={str(e)}"
                    ),
                )
            )

            # Hints từ trạng thái network (nếu có)
            try:
                if hasattr(net, "converged") and not bool(getattr(net, "converged")):
                    errors.setdefault("powerflow", []).append(
                        ValidationError(
                            element_id="",
                            element_type="network",
                            field="converged",
                            message="pandapower net.converged is False",
                        )
                    )
            except Exception:  # noqa: BLE001
                pass

        except Exception as e:  # noqa: BLE001
            converged = False
            errors.setdefault("powerflow", []).append(
                ValidationError(
                    element_id="",
                    element_type="network",
                    field="runpp",
                    message=(
                        "Power flow failed unexpectedly. "
                        f"algorithm={request.settings.algorithm}, "
                        f"max_iter={request.settings.max_iter}, "
                        f"tolerance_mva={request.settings.tolerance_mva}. "
                        f"detail={str(e)}"
                    ),
                )
            )

        # 7. Gom kết quả
        runtime_ms = int((time.time() - start_time) * 1000)

        # Bus results
        bus_by_id: Dict[str, BusResult] = {}
        res_bus: List[Dict[str, Any]] = []

        if converged and hasattr(net, "res_bus") and len(net.res_bus) > 0:
            for node_id, bus_idx in bus_index_by_node_id.items():
                if bus_idx in net.res_bus.index:
                    row = net.res_bus.loc[bus_idx]
                    bus_by_id[node_id] = BusResult(
                        vm_pu=_to_optional_float(row.get("vm_pu", 1.0)),
                        va_degree=_to_optional_float(row.get("va_degree", 0.0)),
                        p_mw=_to_optional_float(row.get("p_mw", 0.0)),
                        q_mvar=_to_optional_float(row.get("q_mvar", 0.0)),
                    )

            # res_bus as list of dicts
            res_bus = _sanitize_json_floats(net.res_bus.reset_index().to_dict("records"))

        # --- Violations reporting (mark success=false so UI counts failed elements) ---
        if converged:
            # Voltage limits per bus (default 0.95..1.05, can be overridden by bus node data)
            bus_data_by_id: Dict[str, Dict[str, Any]] = {
                n.get("id", ""): (n.get("data") or {})
                for n in bus_nodes
                if n.get("id")
            }

            default_min_vm = 0.95
            default_max_vm = 1.05

            for bus_node_id, br in bus_by_id.items():
                if br.vm_pu is None:
                    continue
                data = bus_data_by_id.get(bus_node_id, {})
                min_vm = _to_optional_float(data.get("min_vm_pu", default_min_vm)) or default_min_vm
                max_vm = _to_optional_float(data.get("max_vm_pu", default_max_vm)) or default_max_vm

                if br.vm_pu < min_vm or br.vm_pu > max_vm:
                    msg = f"Voltage violation at bus '{bus_node_id}': vm_pu={br.vm_pu} not in [{min_vm}, {max_vm}]"
                    warnings.append(msg)
                    element_status[bus_node_id] = CreationStatus(
                        element_id=bus_node_id,
                        element_type="bus",
                        success=False,
                        error=msg,
                    )

            # Line overload
            if hasattr(net, "res_line") and len(net.res_line) > 0:
                for node_id, line_idx in line_index_by_node_id.items():
                    if line_idx not in net.res_line.index:
                        continue
                    loading = _to_optional_float(net.res_line.loc[line_idx].get("loading_percent", None))
                    if loading is None:
                        continue
                    if loading > 100.0:
                        msg = f"Line overload '{node_id}': loading_percent={loading} > 100"
                        warnings.append(msg)
                        element_status[node_id] = CreationStatus(
                            element_id=node_id,
                            element_type="line",
                            success=False,
                            error=msg,
                        )

            # Trafo overload
            if hasattr(net, "res_trafo") and len(net.res_trafo) > 0:
                for node_id, trafo_idx in trafo_index_by_node_id.items():
                    if trafo_idx not in net.res_trafo.index:
                        continue
                    loading = _to_optional_float(net.res_trafo.loc[trafo_idx].get("loading_percent", None))
                    if loading is None:
                        continue
                    if loading > 100.0:
                        msg = f"Transformer overload '{node_id}': loading_percent={loading} > 100"
                        warnings.append(msg)
                        element_status[node_id] = CreationStatus(
                            element_id=node_id,
                            element_type="transformer",
                            success=False,
                            error=msg,
                        )

            # Gen Q limits (only when min/max provided)
            gen_data_by_id: Dict[str, Dict[str, Any]] = {
                n.get("id", ""): (n.get("data") or {})
                for n in gen_nodes
                if n.get("id")
            }
            if hasattr(net, "res_gen") and len(net.res_gen) > 0:
                for node_id, gen_idx in gen_index_by_node_id.items():
                    if gen_idx not in net.res_gen.index:
                        continue
                    data = gen_data_by_id.get(node_id, {})
                    qmin = _to_optional_float(data.get("min_q_mvar", None))
                    qmax = _to_optional_float(data.get("max_q_mvar", None))
                    if qmin is None and qmax is None:
                        continue

                    q = _to_optional_float(net.res_gen.loc[gen_idx].get("q_mvar", None))
                    if q is None:
                        continue

                    if qmin is not None and q < qmin:
                        msg = f"Generator Q below min at '{node_id}': q_mvar={q} < min_q_mvar={qmin}"
                        warnings.append(msg)
                        element_status[node_id] = CreationStatus(
                            element_id=node_id,
                            element_type="gen",
                            success=False,
                            error=msg,
                        )
                    elif qmax is not None and q > qmax:
                        msg = f"Generator Q above max at '{node_id}': q_mvar={q} > max_q_mvar={qmax}"
                        warnings.append(msg)
                        element_status[node_id] = CreationStatus(
                            element_id=node_id,
                            element_type="gen",
                            success=False,
                            error=msg,
                        )

        # Results cho các phần tử khác
        results = result_collection._collect_simulation_results(
            net=net,
            converged=converged,
            load_node_ids=load_node_ids,
            gen_node_ids=gen_node_ids,
            sgen_node_ids=sgen_node_ids,
            motor_node_ids=motor_node_ids,
            shunt_node_ids=shunt_node_ids,
            storage_node_ids=storage_node_ids,
            line_edge_ids=line_node_ids,
            trafo_node_ids=transformer_node_ids,
            trafo3w_node_ids=trafo3w_node_ids,
            load_index_by_node_id=load_index_by_node_id,
            gen_index_by_node_id=gen_index_by_node_id,
            sgen_index_by_node_id=sgen_index_by_node_id,
            motor_index_by_node_id=motor_index_by_node_id,
            shunt_index_by_node_id=shunt_index_by_node_id,
            storage_index_by_node_id=storage_index_by_node_id,
            line_index_by_edge_id=line_index_by_node_id,
            trafo_index_by_node_id=trafo_index_by_node_id,
            trafo3w_index_by_node_id=trafo3w_index_by_node_id,
        )
        results = _sanitize_json_floats(results)

        network_payload = export_network(net, mode=request.settings.return_network)

        # Build response
        return SimulateResponse(
            summary=Summary(
                converged=converged,
                runtime_ms=runtime_ms,
                slack_bus_id=slack_bus_id,
            ),
            bus_by_id=bus_by_id,
            res_bus=res_bus,
            warnings=warnings,
            errors=errors,
            element_status=element_status,
            results=results,
            network=network_payload,
        )

    except Exception as e:  # noqa: BLE001
        # Xử lý lỗi tổng quát
        runtime_ms = int((time.time() - start_time) * 1000)
        errors.setdefault("network", []).append(
            ValidationError(
                element_id="",
                element_type="network",
                field="",
                message=f"Lỗi khi tạo network: {str(e)}",
            )
        )
        return _build_error_response(start_time, errors, element_status, warnings, slack_bus_id)


def _build_error_response(
    start_time: float,
    errors: Dict[str, List[ValidationError]],
    element_status: Dict[str, CreationStatus],
    warnings: List[str],
    slack_bus_id: str,
) -> SimulateResponse:
    """Helper function để build error response."""
    runtime_ms = int((time.time() - start_time) * 1000)
    return SimulateResponse(
        summary=Summary(converged=False, runtime_ms=runtime_ms, slack_bus_id=slack_bus_id),
        bus_by_id={},
        res_bus=[],
        warnings=warnings,
        errors=errors,
        element_status=element_status,
        results={},
    )

