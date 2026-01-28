from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pandapower as pp

from app.models.schemas import CreationStatus


def _add_buses(net: pp.pandapowerNet, nodes: List[Dict[str, Any]]) -> Tuple[Dict[str, int], str]:
    bus_index_by_node_id: Dict[str, int] = {}
    slack_bus_id: str | None = None

    for n in nodes:
        node_id = n["id"]
        data = n.get("data") or {}

        vn_kv = float(data.get("vn_kv", 22))
        name = str(data.get("name", "Bus"))
        in_service = bool(data.get("in_service", True))

        idx = pp.create_bus(net, vn_kv=vn_kv, name=name, in_service=in_service)
        bus_index_by_node_id[node_id] = int(idx)

        if slack_bus_id is None:
            slack_bus_id = node_id

    if slack_bus_id is None:
        raise ValueError("No bus nodes provided")

    return bus_index_by_node_id, slack_bus_id


def _add_loads(
    net: pp.pandapowerNet, nodes: List[Dict[str, Any]], bus_index_by_node_id: Dict[str, int]
) -> Tuple[int, List[CreationStatus]]:
    """Add loads to network. Returns (success_count, failed_elements)."""
    failed: List[CreationStatus] = []
    success_count = 0

    for n in nodes:
        node_id = n.get("id", "")
        data = n.get("data") or {}
        bus_id = str(data.get("busId", ""))

        if not bus_id or bus_id not in bus_index_by_node_id:
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="load",
                    success=False,
                    error=f"busId '{bus_id}' not found or invalid",
                )
            )
            continue

        try:
            pp.create_load(
                net,
                bus=bus_index_by_node_id[bus_id],
                p_mw=float(data.get("p_mw", 1.0)),
                q_mvar=float(data.get("q_mvar", 0.0)),
                scaling=float(data.get("scaling", 1.0)),
                name=str(data.get("name", "Load")),
                in_service=bool(data.get("in_service", True)),
                controllable=bool(data.get("controllable", False)),
            )
            success_count += 1
        except Exception as e:  # noqa: BLE001
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="load",
                    success=False,
                    error=str(e),
                )
            )

    return success_count, failed


def _add_ext_grids(
    net: pp.pandapowerNet,
    nodes: List[Dict[str, Any]],
    bus_index_by_node_id: Dict[str, int],
    edges: List[Dict[str, Any]] | None = None,
) -> Tuple[int, List[CreationStatus]]:
    """Add ext_grids to network. Returns (success_count, failed_elements)."""
    failed: List[CreationStatus] = []
    success_count = 0

    attach_bus_by_ext_grid_id: Dict[str, str] = {}
    if edges:
        for e in edges:
            data = e.get("data") or {}
            if str(data.get("kind")) != "attach":
                continue
            if str(data.get("attach_type")) != "ext_grid":
                continue
            src = str(e.get("source") or "")
            tgt = str(e.get("target") or "")
            if not src or not tgt:
                continue
            # src=ext_grid, tgt=bus
            attach_bus_by_ext_grid_id[src] = tgt

    for n in nodes:
        node_id = n.get("id", "")
        data = n.get("data") or {}

        bus_id = str(data.get("busId", ""))
        if not bus_id:
            bus_id = str(attach_bus_by_ext_grid_id.get(node_id, ""))

        if not bus_id or bus_id not in bus_index_by_node_id:
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="ext_grid",
                    success=False,
                    error=f"busId '{bus_id}' not found or invalid",
                )
            )
            continue

        try:
            pp.create_ext_grid(
                net,
                bus=bus_index_by_node_id[bus_id],
                vm_pu=float(data.get("vm_pu", 1.0)),
                va_degree=float(data.get("va_degree", 0.0)),
                name=str(data.get("name", "Ext Grid")),
                in_service=bool(data.get("in_service", True)),
            )
            success_count += 1
        except Exception as e:  # noqa: BLE001
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="ext_grid",
                    success=False,
                    error=str(e),
                )
            )

    return success_count, failed


def _add_gens(
    net: pp.pandapowerNet, nodes: List[Dict[str, Any]], bus_index_by_node_id: Dict[str, int]
) -> Tuple[int, List[CreationStatus]]:
    """Add gens to network. Returns (success_count, failed_elements)."""
    failed: List[CreationStatus] = []
    success_count = 0

    for n in nodes:
        node_id = n.get("id", "")
        data = n.get("data") or {}
        bus_id = str(data.get("busId", ""))

        if not bus_id or bus_id not in bus_index_by_node_id:
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="gen",
                    success=False,
                    error=f"busId '{bus_id}' not found or invalid",
                )
            )
            continue

        try:
            pp.create_gen(
                net,
                bus=bus_index_by_node_id[bus_id],
                p_mw=float(data.get("p_mw", 1.0)),
                vm_pu=float(data.get("vm_pu", 1.0)),
                min_q_mvar=float(data.get("min_q_mvar", -10.0)) if data.get("min_q_mvar") is not None else None,
                max_q_mvar=float(data.get("max_q_mvar", 10.0)) if data.get("max_q_mvar") is not None else None,
                name=str(data.get("name", "Gen")),
                in_service=bool(data.get("in_service", True)),
                controllable=bool(data.get("controllable", True)),
            )
            success_count += 1
        except Exception as e:  # noqa: BLE001
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="gen",
                    success=False,
                    error=str(e),
                )
            )

    return success_count, failed


def _add_sgens(
    net: pp.pandapowerNet, nodes: List[Dict[str, Any]], bus_index_by_node_id: Dict[str, int]
) -> Tuple[int, List[CreationStatus]]:
    """Add sgens to network. Returns (success_count, failed_elements)."""
    failed: List[CreationStatus] = []
    success_count = 0

    for n in nodes:
        node_id = n.get("id", "")
        data = n.get("data") or {}
        bus_id = str(data.get("busId", ""))

        if not bus_id or bus_id not in bus_index_by_node_id:
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="sgen",
                    success=False,
                    error=f"busId '{bus_id}' not found or invalid",
                )
            )
            continue

        try:
            pp.create_sgen(
                net,
                bus=bus_index_by_node_id[bus_id],
                p_mw=float(data.get("p_mw", 1.0)),
                q_mvar=float(data.get("q_mvar", 0.0)),
                name=str(data.get("name", "SGen")),
                in_service=bool(data.get("in_service", True)),
                controllable=bool(data.get("controllable", True)),
            )
            success_count += 1
        except Exception as e:  # noqa: BLE001
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="sgen",
                    success=False,
                    error=str(e),
                )
            )

    return success_count, failed


def _add_motors(
    net: pp.pandapowerNet, nodes: List[Dict[str, Any]], bus_index_by_node_id: Dict[str, int]
) -> Tuple[int, List[CreationStatus]]:
    """Add motors to network. Returns (success_count, failed_elements)."""
    failed: List[CreationStatus] = []
    success_count = 0

    for n in nodes:
        node_id = n.get("id", "")
        data = n.get("data") or {}
        bus_id = str(data.get("busId", ""))

        if not bus_id or bus_id not in bus_index_by_node_id:
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="motor",
                    success=False,
                    error=f"busId '{bus_id}' not found or invalid",
                )
            )
            continue

        try:
            pp.create_motor(
                net,
                bus=bus_index_by_node_id[bus_id],
                pn_mech_mw=float(data.get("pn_mech_mw", 1.0)),
                cos_phi=float(data.get("cos_phi", 0.85)),
                efficiency=float(data.get("efficiency", 0.9)),
                loading_percent=float(data.get("loading_percent", 100.0)),
                name=str(data.get("name", "Motor")),
                in_service=bool(data.get("in_service", True)),
            )
            success_count += 1
        except Exception as e:  # noqa: BLE001
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="motor",
                    success=False,
                    error=str(e),
                )
            )

    return success_count, failed


def _add_shunts(
    net: pp.pandapowerNet, nodes: List[Dict[str, Any]], bus_index_by_node_id: Dict[str, int]
) -> Tuple[int, List[CreationStatus]]:
    """Add shunts to network. Returns (success_count, failed_elements)."""
    failed: List[CreationStatus] = []
    success_count = 0

    for n in nodes:
        node_id = n.get("id", "")
        data = n.get("data") or {}
        bus_id = str(data.get("busId", ""))

        if not bus_id or bus_id not in bus_index_by_node_id:
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="shunt",
                    success=False,
                    error=f"busId '{bus_id}' not found or invalid",
                )
            )
            continue

        try:
            pp.create_shunt(
                net,
                bus=bus_index_by_node_id[bus_id],
                p_mw=float(data.get("p_mw", 0.0)),
                q_mvar=float(data.get("q_mvar", 0.0)),
                vn_kv=float(data.get("vn_kv", 22.0)),
                step=float(data.get("step", 1.0)) if data.get("step") is not None else None,
                max_step=float(data.get("max_step", 1.0)) if data.get("max_step") is not None else None,
                name=str(data.get("name", "Shunt")),
                in_service=bool(data.get("in_service", True)),
            )
            success_count += 1
        except Exception as e:  # noqa: BLE001
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="shunt",
                    success=False,
                    error=str(e),
                )
            )

    return success_count, failed


def _add_storages(
    net: pp.pandapowerNet, nodes: List[Dict[str, Any]], bus_index_by_node_id: Dict[str, int]
) -> Tuple[int, List[CreationStatus]]:
    """Add storages to network. Returns (success_count, failed_elements)."""
    failed: List[CreationStatus] = []
    success_count = 0

    for n in nodes:
        node_id = n.get("id", "")
        data = n.get("data") or {}
        bus_id = str(data.get("busId", ""))

        if not bus_id or bus_id not in bus_index_by_node_id:
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="storage",
                    success=False,
                    error=f"busId '{bus_id}' not found or invalid",
                )
            )
            continue

        try:
            pp.create_storage(
                net,
                bus=bus_index_by_node_id[bus_id],
                p_mw=float(data.get("p_mw", 0.0)),
                q_mvar=float(data.get("q_mvar", 0.0)),
                max_e_mwh=float(data.get("max_e_mwh", 10.0)),
                min_e_mwh=float(data.get("min_e_mwh", 0.0)),
                max_p_mw=float(data.get("max_p_mw", 5.0)),
                min_p_mw=float(data.get("min_p_mw", -5.0)),
                soc_percent=float(data.get("soc_percent", 50.0)),
                name=str(data.get("name", "Storage")),
                in_service=bool(data.get("in_service", True)),
            )
            success_count += 1
        except Exception as e:  # noqa: BLE001
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="storage",
                    success=False,
                    error=str(e),
                )
            )

    return success_count, failed


def _add_transformers(
    net: pp.pandapowerNet,
    nodes: List[Dict[str, Any]],
    bus_index_by_node_id: Dict[str, int],
) -> Tuple[List[Tuple[int, str, Dict[str, Any]]], List[CreationStatus]]:
    """Create transformers from nodes. Returns (trafo_edges, failed_elements)."""
    trafo_edges: List[Tuple[int, str, Dict[str, Any]]] = []
    failed: List[CreationStatus] = []

    for n in nodes:
        node_id = n.get("id", "")
        data = n.get("data") or {}
        hv_bus_id = str(data.get("hvBusId", ""))
        lv_bus_id = str(data.get("lvBusId", ""))

        if not hv_bus_id or not lv_bus_id:
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="transformer",
                    success=False,
                    error="hvBusId or lvBusId missing",
                )
            )
            continue

        if hv_bus_id not in bus_index_by_node_id or lv_bus_id not in bus_index_by_node_id:
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="transformer",
                    success=False,
                    error=f"hvBusId '{hv_bus_id}' or lvBusId '{lv_bus_id}' not found",
                )
            )
            continue

        std_type = str(data.get("std_type", ""))
        if not std_type:
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="transformer",
                    success=False,
                    error="std_type is required",
                )
            )
            continue

        try:
            trafo_idx = pp.create_transformer(
                net,
                hv_bus=bus_index_by_node_id[hv_bus_id],
                lv_bus=bus_index_by_node_id[lv_bus_id],
                std_type=std_type,
                name=str(data.get("name", "Transformer")),
                in_service=bool(data.get("in_service", True)),
            )
            trafo_edges.append((int(trafo_idx), node_id, data))
        except Exception as e:  # noqa: BLE001
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="transformer",
                    success=False,
                    error=str(e),
                )
            )

    return trafo_edges, failed


def _add_trafo3w(
    net: pp.pandapowerNet,
    nodes: List[Dict[str, Any]],
    bus_index_by_node_id: Dict[str, int],
) -> Tuple[int, List[CreationStatus]]:
    """Add trafo3w to network. Returns (success_count, failed_elements)."""
    failed: List[CreationStatus] = []
    success_count = 0

    for n in nodes:
        node_id = n.get("id", "")
        data = n.get("data") or {}
        hv_bus_id = str(data.get("hvBusId", ""))
        mv_bus_id = str(data.get("mvBusId", ""))
        lv_bus_id = str(data.get("lvBusId", ""))

        if not hv_bus_id or not mv_bus_id or not lv_bus_id:
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="trafo3w",
                    success=False,
                    error="hvBusId, mvBusId, or lvBusId missing",
                )
            )
            continue

        if (
            hv_bus_id not in bus_index_by_node_id
            or mv_bus_id not in bus_index_by_node_id
            or lv_bus_id not in bus_index_by_node_id
        ):
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="trafo3w",
                    success=False,
                    error=f"One or more bus IDs not found",
                )
            )
            continue

        std_type = str(data.get("std_type", ""))
        if not std_type:
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="trafo3w",
                    success=False,
                    error="std_type is required",
                )
            )
            continue

        try:
            pp.create_trafo3w(
                net,
                hv_bus=bus_index_by_node_id[hv_bus_id],
                mv_bus=bus_index_by_node_id[mv_bus_id],
                lv_bus=bus_index_by_node_id[lv_bus_id],
                std_type=std_type,
                name=str(data.get("name", "Trafo3W")),
                in_service=bool(data.get("in_service", True)),
            )
            success_count += 1
        except Exception as e:  # noqa: BLE001
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="trafo3w",
                    success=False,
                    error=str(e),
                )
            )

    return success_count, failed


def _add_switches(
    net: pp.pandapowerNet,
    nodes: List[Dict[str, Any]],
    bus_index_by_node_id: Dict[str, int],
    line_index_by_edge_id: Dict[str, int],
    trafo_index_by_node_id: Dict[str, int],
) -> Tuple[int, List[CreationStatus]]:
    """Add switches to network. Returns (success_count, failed_elements)."""
    failed: List[CreationStatus] = []
    success_count = 0

    for n in nodes:
        node_id = n.get("id", "")
        data = n.get("data") or {}
        bus_id = str(data.get("busId", ""))
        element_id = str(data.get("elementId", ""))
        element_type = str(data.get("elementType", "line"))

        if not bus_id or bus_id not in bus_index_by_node_id:
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="switch",
                    success=False,
                    error=f"busId '{bus_id}' not found or invalid",
                )
            )
            continue

        bus_idx = bus_index_by_node_id[bus_id]
        element_idx: int | None = None
        et: str | None = None

        if element_type == "line":
            if element_id not in line_index_by_edge_id:
                failed.append(
                    CreationStatus(
                        element_id=node_id,
                        element_type="switch",
                        success=False,
                        error=f"elementId '{element_id}' (line) not found",
                    )
                )
                continue
            element_idx = line_index_by_edge_id[element_id]
            et = "l"
        elif element_type == "trafo":
            if element_id not in trafo_index_by_node_id:
                failed.append(
                    CreationStatus(
                        element_id=node_id,
                        element_type="switch",
                        success=False,
                        error=f"elementId '{element_id}' (trafo) not found",
                    )
                )
                continue
            element_idx = trafo_index_by_node_id[element_id]
            et = "t"
        elif element_type == "bus":
            if element_id not in bus_index_by_node_id:
                failed.append(
                    CreationStatus(
                        element_id=node_id,
                        element_type="switch",
                        success=False,
                        error=f"elementId '{element_id}' (bus) not found",
                    )
                )
                continue
            element_idx = bus_index_by_node_id[element_id]
            et = "b"
        else:
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="switch",
                    success=False,
                    error=f"Invalid elementType '{element_type}'",
                )
            )
            continue

        if element_idx is None or et is None:
            continue

        try:
            pp.create_switch(
                net,
                bus=bus_idx,
                element=element_idx,
                et=et,
                closed=bool(data.get("closed", True)),
                type=str(data.get("type", "")) if data.get("type") else None,
                z_ohm=float(data.get("z_ohm", 0.0)) if data.get("z_ohm") is not None else None,
                name=str(data.get("name", "Switch")),
                in_service=bool(data.get("in_service", True)),
            )
            success_count += 1
        except Exception as e:  # noqa: BLE001
            failed.append(
                CreationStatus(
                    element_id=node_id,
                    element_type="switch",
                    success=False,
                    error=str(e),
                )
            )

    return success_count, failed


def _ensure_slack(net: pp.pandapowerNet) -> None:
    if len(net.ext_grid) == 0:
        raise ValueError("No ext_grid found. At least one ext_grid is required.")


def _add_lines_from_edges(
    net: pp.pandapowerNet,
    edges: List[Dict[str, Any]],
    bus_index_by_node_id: Dict[str, int],
) -> Tuple[List[Tuple[int, str, Dict[str, Any]]], List[CreationStatus]]:
    """Create lines from edges. Returns (line_edges, failed_elements)."""
    line_edges: List[Tuple[int, str, Dict[str, Any]]] = []
    failed: List[CreationStatus] = []

    def _to_int(v: Any, default: int) -> int:
        try:
            i = int(v)
        except (TypeError, ValueError):
            return default
        return i

    def _to_float(v: Any, default: float) -> float:
        try:
            f = float(v)
        except (TypeError, ValueError):
            return default
        return f

    def _is_line_edge(edge_data: Dict[str, Any], src: str, tgt: str) -> bool:
        # Strict contract: only explicit kind='line' is treated as a pandapower line
        return str(edge_data.get("kind")) == "line"

    for e in edges:
        edge_id = e.get("id", "")
        src = e.get("source")
        tgt = e.get("target")

        if not src or not tgt:
            failed.append(
                CreationStatus(
                    element_id=edge_id,
                    element_type="line",
                    success=False,
                    error="source or target missing",
                )
            )
            continue

        edge_data = e.get("data") or {}

        # Skip non-line edges (e.g. attachment edges)
        if not _is_line_edge(edge_data, src, tgt):
            continue

        if src not in bus_index_by_node_id or tgt not in bus_index_by_node_id:
            failed.append(
                CreationStatus(
                    element_id=edge_id,
                    element_type="line",
                    success=False,
                    error=f"source '{src}' or target '{tgt}' bus not found",
                )
            )
            continue

        if src == tgt:
            failed.append(
                CreationStatus(
                    element_id=edge_id,
                    element_type="line",
                    success=False,
                    error="source and target cannot be the same",
                )
            )
            continue

        # Common line fields
        name = str(edge_data.get("name", "")) or None
        length_km = _to_float(edge_data.get("length_km"), 1.0)
        in_service = bool(edge_data.get("in_service", True))
        parallel = _to_int(edge_data.get("parallel"), 1)
        df = _to_float(edge_data.get("df"), 1.0)

        if length_km <= 0:
            failed.append(
                CreationStatus(
                    element_id=edge_id,
                    element_type="line",
                    success=False,
                    error="length_km must be > 0",
                )
            )
            continue

        from_bus = bus_index_by_node_id[src]
        to_bus = bus_index_by_node_id[tgt]

        std_type_raw = edge_data.get("std_type")
        std_type = str(std_type_raw).strip() if std_type_raw is not None else ""

        try:
            if std_type:
                line_idx = pp.create_line(
                    net,
                    from_bus=from_bus,
                    to_bus=to_bus,
                    length_km=length_km,
                    std_type=std_type,
                    name=name,
                    parallel=parallel,
                    df=df,
                    in_service=in_service,
                )
            else:
                # Custom parameters path
                r_ohm_per_km = edge_data.get("r_ohm_per_km")
                x_ohm_per_km = edge_data.get("x_ohm_per_km")
                c_nf_per_km = edge_data.get("c_nf_per_km")
                max_i_ka = edge_data.get("max_i_ka")

                missing_fields = [
                    f
                    for f, v in (
                        ("r_ohm_per_km", r_ohm_per_km),
                        ("x_ohm_per_km", x_ohm_per_km),
                        ("c_nf_per_km", c_nf_per_km),
                        ("max_i_ka", max_i_ka),
                    )
                    if v is None
                ]
                if missing_fields:
                    failed.append(
                        CreationStatus(
                            element_id=edge_id,
                            element_type="line",
                            success=False,
                            error=f"Missing line parameters: {', '.join(missing_fields)}",
                        )
                    )
                    continue

                line_idx = pp.create_line_from_parameters(
                    net,
                    from_bus=from_bus,
                    to_bus=to_bus,
                    length_km=length_km,
                    r_ohm_per_km=_to_float(r_ohm_per_km, 0.0),
                    x_ohm_per_km=_to_float(x_ohm_per_km, 0.0),
                    c_nf_per_km=_to_float(c_nf_per_km, 0.0),
                    max_i_ka=_to_float(max_i_ka, 0.0),
                    name=name,
                    parallel=parallel,
                    df=df,
                    in_service=in_service,
                )

            line_edges.append((int(line_idx), edge_id, edge_data))
        except Exception as e:  # noqa: BLE001
            failed.append(
                CreationStatus(
                    element_id=edge_id,
                    element_type="line",
                    success=False,
                    error=str(e),
                )
            )

    return line_edges, failed

