from __future__ import annotations

import math
from typing import Any, Dict, List

import pandapower as pp


def _to_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _collect_simulation_results(
    net: pp.pandapowerNet,
    converged: bool,
    load_node_ids: List[str],
    gen_node_ids: List[str],
    sgen_node_ids: List[str],
    motor_node_ids: List[str],
    shunt_node_ids: List[str],
    storage_node_ids: List[str],
    line_edge_ids: List[str],  # line-node ids in the new model
    trafo_node_ids: List[str],
    trafo3w_node_ids: List[str],
    load_index_by_node_id: Dict[str, int],
    gen_index_by_node_id: Dict[str, int],
    sgen_index_by_node_id: Dict[str, int],
    motor_index_by_node_id: Dict[str, int],
    shunt_index_by_node_id: Dict[str, int],
    storage_index_by_node_id: Dict[str, int],
    line_index_by_edge_id: Dict[str, int],  # line-node id -> pandapower line index in the new model
    trafo_index_by_node_id: Dict[str, int],
    trafo3w_index_by_node_id: Dict[str, int],
) -> Dict[str, Dict[str, Any]]:
    """Collect simulation results for all element types."""
    results: Dict[str, Dict[str, Any]] = {
        "loads": {},
        "gens": {},
        "sgens": {},
        "motors": {},
        "shunts": {},
        "storages": {},
        "lines": {},
        "trafos": {},
        "trafo3ws": {},
    }

    if not converged:
        return results

    # Collect load results
    if hasattr(net, "res_load") and len(net.res_load) > 0:
        for node_id in load_node_ids:
            if node_id not in load_index_by_node_id:
                continue
            idx = load_index_by_node_id[node_id]
            if idx not in net.res_load.index:
                continue
            row = net.res_load.loc[idx]
            results["loads"][node_id] = {
                "p_mw": _to_optional_float(row.get("p_mw", 0.0)),
                "q_mvar": _to_optional_float(row.get("q_mvar", 0.0)),
            }

    # Collect gen results
    if hasattr(net, "res_gen") and len(net.res_gen) > 0:
        for node_id in gen_node_ids:
            if node_id not in gen_index_by_node_id:
                continue
            idx = gen_index_by_node_id[node_id]
            if idx not in net.res_gen.index:
                continue
            row = net.res_gen.loc[idx]
            results["gens"][node_id] = {
                "p_mw": _to_optional_float(row.get("p_mw", 0.0)),
                "q_mvar": _to_optional_float(row.get("q_mvar", 0.0)),
                "vm_pu": _to_optional_float(row.get("vm_pu", 1.0)),
            }

    # Collect sgen results
    if hasattr(net, "res_sgen") and len(net.res_sgen) > 0:
        for node_id in sgen_node_ids:
            if node_id not in sgen_index_by_node_id:
                continue
            idx = sgen_index_by_node_id[node_id]
            if idx not in net.res_sgen.index:
                continue
            row = net.res_sgen.loc[idx]
            results["sgens"][node_id] = {
                "p_mw": _to_optional_float(row.get("p_mw", 0.0)),
                "q_mvar": _to_optional_float(row.get("q_mvar", 0.0)),
            }

    # Collect motor results
    if hasattr(net, "res_motor") and len(net.res_motor) > 0:
        for node_id in motor_node_ids:
            if node_id not in motor_index_by_node_id:
                continue
            idx = motor_index_by_node_id[node_id]
            if idx not in net.res_motor.index:
                continue
            row = net.res_motor.loc[idx]
            results["motors"][node_id] = {
                "p_mw": _to_optional_float(row.get("p_mw", 0.0)),
                "q_mvar": _to_optional_float(row.get("q_mvar", 0.0)),
            }

    # Collect shunt results
    if hasattr(net, "res_shunt") and len(net.res_shunt) > 0:
        for node_id in shunt_node_ids:
            if node_id not in shunt_index_by_node_id:
                continue
            idx = shunt_index_by_node_id[node_id]
            if idx not in net.res_shunt.index:
                continue
            row = net.res_shunt.loc[idx]
            results["shunts"][node_id] = {
                "p_mw": _to_optional_float(row.get("p_mw", 0.0)),
                "q_mvar": _to_optional_float(row.get("q_mvar", 0.0)),
            }

    # Collect storage results
    if hasattr(net, "res_storage") and len(net.res_storage) > 0:
        for node_id in storage_node_ids:
            if node_id not in storage_index_by_node_id:
                continue
            idx = storage_index_by_node_id[node_id]
            if idx not in net.res_storage.index:
                continue
            row = net.res_storage.loc[idx]
            results["storages"][node_id] = {
                "p_mw": _to_optional_float(row.get("p_mw", 0.0)),
                "q_mvar": _to_optional_float(row.get("q_mvar", 0.0)),
            }

    # Collect line results
    if hasattr(net, "res_line") and len(net.res_line) > 0:
        for edge_id in line_edge_ids:
            if edge_id not in line_index_by_edge_id:
                continue
            idx = line_index_by_edge_id[edge_id]
            if idx not in net.res_line.index:
                continue
            row = net.res_line.loc[idx]
            results["lines"][edge_id] = {
                "p_from_mw": _to_optional_float(row.get("p_from_mw", 0.0)),
                "q_from_mvar": _to_optional_float(row.get("q_from_mvar", 0.0)),
                "p_to_mw": _to_optional_float(row.get("p_to_mw", 0.0)),
                "q_to_mvar": _to_optional_float(row.get("q_to_mvar", 0.0)),
                "i_from_ka": _to_optional_float(row.get("i_from_ka", 0.0)),
                "i_to_ka": _to_optional_float(row.get("i_to_ka", 0.0)),
                "loading_percent": _to_optional_float(row.get("loading_percent", 0.0)),
            }

    # Collect trafo results
    if hasattr(net, "res_trafo") and len(net.res_trafo) > 0:
        for node_id in trafo_node_ids:
            if node_id not in trafo_index_by_node_id:
                continue
            idx = trafo_index_by_node_id[node_id]
            if idx not in net.res_trafo.index:
                continue
            row = net.res_trafo.loc[idx]
            results["trafos"][node_id] = {
                "p_hv_mw": _to_optional_float(row.get("p_hv_mw", 0.0)),
                "q_hv_mvar": _to_optional_float(row.get("q_hv_mvar", 0.0)),
                "p_lv_mw": _to_optional_float(row.get("p_lv_mw", 0.0)),
                "q_lv_mvar": _to_optional_float(row.get("q_lv_mvar", 0.0)),
                "i_hv_ka": _to_optional_float(row.get("i_hv_ka", 0.0)),
                "i_lv_ka": _to_optional_float(row.get("i_lv_ka", 0.0)),
                "loading_percent": _to_optional_float(row.get("loading_percent", 0.0)),
            }

    # Collect trafo3w results
    if hasattr(net, "res_trafo3w") and len(net.res_trafo3w) > 0:
        for node_id in trafo3w_node_ids:
            if node_id not in trafo3w_index_by_node_id:
                continue
            idx = trafo3w_index_by_node_id[node_id]
            if idx not in net.res_trafo3w.index:
                continue
            row = net.res_trafo3w.loc[idx]
            results["trafo3ws"][node_id] = {
                "p_hv_mw": _to_optional_float(row.get("p_hv_mw", 0.0)),
                "q_hv_mvar": _to_optional_float(row.get("q_hv_mvar", 0.0)),
                "p_mv_mw": _to_optional_float(row.get("p_mv_mw", 0.0)),
                "q_mv_mvar": _to_optional_float(row.get("q_mv_mvar", 0.0)),
                "p_lv_mw": _to_optional_float(row.get("p_lv_mw", 0.0)),
                "q_lv_mvar": _to_optional_float(row.get("q_lv_mvar", 0.0)),
                "i_hv_ka": _to_optional_float(row.get("i_hv_ka", 0.0)),
                "i_mv_ka": _to_optional_float(row.get("i_mv_ka", 0.0)),
                "i_lv_ka": _to_optional_float(row.get("i_lv_ka", 0.0)),
                "loading_percent": _to_optional_float(row.get("loading_percent", 0.0)),
            }

    return results

