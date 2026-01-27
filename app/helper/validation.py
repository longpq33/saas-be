from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from app.models.schemas import ValidationError


def _validate_network(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    bus_index_by_node_id: Dict[str, int],
) -> List[ValidationError]:
    """Validate network before creating elements. Returns list of validation errors."""
    errors: List[ValidationError] = []

    # Helper
    def _as_str(v: Any) -> str:
        return "" if v is None else str(v)

    def _as_float(v: Any) -> float | None:
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return f

    # Build set of open (disconnected) elements by switch state
    open_line_ids: Set[str] = set()
    open_trafo_ids: Set[str] = set()
    for n in nodes:
        if n.get("type") != "switch":
            continue
        data = n.get("data") or {}
        if bool(data.get("closed", True)):
            continue
        et = _as_str(data.get("elementType", "line"))
        eid = _as_str(data.get("elementId", ""))
        if not eid:
            continue
        if et == "line":
            open_line_ids.add(eid)
        elif et == "trafo":
            open_trafo_ids.add(eid)

    def _islanding_errors() -> List[ValidationError]:
        # Build adjacency list for buses (using only in-service connections)
        bus_ids = [n.get("id", "") for n in nodes if n.get("type") == "bus" and n.get("id")]
        adj: Dict[str, Set[str]] = {bid: set() for bid in bus_ids}

        # Lines from edges
        for e in edges:
            edge_id = e.get("id", "") or ""
            if edge_id in open_line_ids:
                continue
            src = e.get("source")
            tgt = e.get("target")
            if not src or not tgt:
                continue
            if src not in adj or tgt not in adj:
                continue
            if src == tgt:
                continue
            adj[src].add(tgt)
            adj[tgt].add(src)

        # Transformers (2-winding)
        for n in nodes:
            if n.get("type") != "transformer":
                continue
            node_id = n.get("id", "") or ""
            if node_id in open_trafo_ids:
                continue
            data = n.get("data") or {}
            hv = _as_str(data.get("hvBusId", ""))
            lv = _as_str(data.get("lvBusId", ""))
            if hv in adj and lv in adj and hv != lv:
                adj[hv].add(lv)
                adj[lv].add(hv)

        # Transformers 3-winding
        for n in nodes:
            if n.get("type") != "trafo3w":
                continue
            data = n.get("data") or {}
            hv = _as_str(data.get("hvBusId", ""))
            mv = _as_str(data.get("mvBusId", ""))
            lv = _as_str(data.get("lvBusId", ""))
            pairs: List[Tuple[str, str]] = [(hv, mv), (mv, lv), (hv, lv)]
            for a, b in pairs:
                if a in adj and b in adj and a != b:
                    adj[a].add(b)
                    adj[b].add(a)

        # Ext grid buses
        ext_grid_bus_ids: Set[str] = set()
        for n in nodes:
            if n.get("type") != "ext_grid":
                continue
            data = n.get("data") or {}
            bid = _as_str(data.get("busId", ""))
            if bid:
                ext_grid_bus_ids.add(bid)

        # Find connected components and ensure each component has ext_grid
        visited: Set[str] = set()
        island_errs: List[ValidationError] = []
        for start in bus_ids:
            if start in visited:
                continue
            stack = [start]
            comp: Set[str] = set()
            visited.add(start)
            while stack:
                cur = stack.pop()
                comp.add(cur)
                for nei in adj.get(cur, set()):
                    if nei not in visited:
                        visited.add(nei)
                        stack.append(nei)

            if not (comp & ext_grid_bus_ids):
                # FATAL: island without ext_grid
                island_errs.append(
                    ValidationError(
                        element_id="",
                        element_type="network",
                        field="islanding",
                        message="Island detected without ext_grid (slack). Add ext_grid to each island or connect islands.",
                    )
                )
                # Optionally add one bus-specific error to help UI point to a place
                some_bus = next(iter(comp)) if comp else ""
                if some_bus:
                    island_errs.append(
                        ValidationError(
                            element_id=some_bus,
                            element_type="bus",
                            field="islanding",
                            message="This bus is in an island without ext_grid",
                        )
                    )
                break

        return island_errs

    # Collect all node IDs by type
    bus_node_ids = {n["id"] for n in nodes if n.get("type") == "bus"}
    ext_grid_nodes = [n for n in nodes if n.get("type") == "ext_grid"]
    load_nodes = [n for n in nodes if n.get("type") == "load"]
    gen_nodes = [n for n in nodes if n.get("type") == "gen"]
    sgen_nodes = [n for n in nodes if n.get("type") == "sgen"]
    motor_nodes = [n for n in nodes if n.get("type") == "motor"]
    shunt_nodes = [n for n in nodes if n.get("type") == "shunt"]
    storage_nodes = [n for n in nodes if n.get("type") == "storage"]
    transformer_nodes = [n for n in nodes if n.get("type") == "transformer"]
    trafo3w_nodes = [n for n in nodes if n.get("type") == "trafo3w"]
    switch_nodes = [n for n in nodes if n.get("type") == "switch"]

    # Validate buses
    for node in nodes:
        if node.get("type") != "bus":
            continue
        node_id = node.get("id", "")
        data = node.get("data") or {}
        vn_kv = _as_float(data.get("vn_kv", None))
        if vn_kv is None:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="bus",
                    field="vn_kv",
                    message="vn_kv must be a number",
                )
            )
        elif vn_kv <= 0:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="bus",
                    field="vn_kv",
                    message="vn_kv must be > 0",
                )
            )

    # Validate bus-bound elements (load, gen, ext_grid, motor, shunt, storage)
    for node in load_nodes + gen_nodes + sgen_nodes + motor_nodes + shunt_nodes + storage_nodes + ext_grid_nodes:
        node_id = node.get("id", "")
        node_type = node.get("type", "")
        data = node.get("data") or {}
        bus_id = _as_str(data.get("busId", ""))

        if not bus_id:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type=node_type,
                    field="busId",
                    message="busId is required",
                )
            )
        elif bus_id not in bus_index_by_node_id:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type=node_type,
                    field="busId",
                    message=f"busId '{bus_id}' does not exist",
                )
            )

        # Basic numeric checks
        if node_type in {"load", "gen", "sgen"}:
            p_mw = _as_float(data.get("p_mw", None))
            if p_mw is None:
                errors.append(
                    ValidationError(
                        element_id=node_id,
                        element_type=node_type,
                        field="p_mw",
                        message="p_mw must be a number",
                    )
                )

    # Validate transformers
    for node in transformer_nodes:
        node_id = node.get("id", "")
        data = node.get("data") or {}
        hv_bus_id = str(data.get("hvBusId", ""))
        lv_bus_id = str(data.get("lvBusId", ""))

        if not hv_bus_id:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="transformer",
                    field="hvBusId",
                    message="hvBusId is required",
                )
            )
        elif hv_bus_id not in bus_index_by_node_id:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="transformer",
                    field="hvBusId",
                    message=f"hvBusId '{hv_bus_id}' does not exist",
                )
            )

        if not lv_bus_id:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="transformer",
                    field="lvBusId",
                    message="lvBusId is required",
                )
            )
        elif lv_bus_id not in bus_index_by_node_id:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="transformer",
                    field="lvBusId",
                    message=f"lvBusId '{lv_bus_id}' does not exist",
                )
            )

        std_type = str(data.get("std_type", ""))
        if not std_type:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="transformer",
                    field="std_type",
                    message="std_type is required",
                )
            )

    # Validate trafo3w
    for node in trafo3w_nodes:
        node_id = node.get("id", "")
        data = node.get("data") or {}
        hv_bus_id = str(data.get("hvBusId", ""))
        mv_bus_id = str(data.get("mvBusId", ""))
        lv_bus_id = str(data.get("lvBusId", ""))

        if not hv_bus_id:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="trafo3w",
                    field="hvBusId",
                    message="hvBusId is required",
                )
            )
        elif hv_bus_id not in bus_index_by_node_id:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="trafo3w",
                    field="hvBusId",
                    message=f"hvBusId '{hv_bus_id}' does not exist",
                )
            )

        if not mv_bus_id:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="trafo3w",
                    field="mvBusId",
                    message="mvBusId is required",
                )
            )
        elif mv_bus_id not in bus_index_by_node_id:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="trafo3w",
                    field="mvBusId",
                    message=f"mvBusId '{mv_bus_id}' does not exist",
                )
            )

        if not lv_bus_id:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="trafo3w",
                    field="lvBusId",
                    message="lvBusId is required",
                )
            )
        elif lv_bus_id not in bus_index_by_node_id:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="trafo3w",
                    field="lvBusId",
                    message=f"lvBusId '{lv_bus_id}' does not exist",
                )
            )

        std_type = str(data.get("std_type", ""))
        if not std_type:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="trafo3w",
                    field="std_type",
                    message="std_type is required",
                )
            )

    # Validate switches
    # Note: We can't fully validate switches here because we need line/trafo indices
    # which are created later. We'll validate what we can.
    for node in switch_nodes:
        node_id = node.get("id", "")
        data = node.get("data") or {}
        bus_id = str(data.get("busId", ""))
        element_id = str(data.get("elementId", ""))
        element_type = str(data.get("elementType", "line"))

        if not bus_id:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="switch",
                    field="busId",
                    message="busId is required",
                )
            )
        elif bus_id not in bus_index_by_node_id:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="switch",
                    field="busId",
                    message=f"busId '{bus_id}' does not exist",
                )
            )

        if not element_id:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="switch",
                    field="elementId",
                    message="elementId is required",
                )
            )

        if element_type not in ["line", "trafo", "bus"]:
            errors.append(
                ValidationError(
                    element_id=node_id,
                    element_type="switch",
                    field="elementType",
                    message=f"elementType must be 'line', 'trafo', or 'bus', got '{element_type}'",
                )
            )

    # Validate edges (lines)
    for edge in edges:
        edge_id = edge.get("id", "")
        edge_data = edge.get("data") or {}
        std_type = str(edge_data.get("std_type", ""))
        length_km = _as_float(edge_data.get("length_km", None))

        if not std_type:
            errors.append(
                ValidationError(
                    element_id=edge_id,
                    element_type="line",
                    field="std_type",
                    message="std_type is required",
                )
            )

        if length_km is None:
            errors.append(
                ValidationError(
                    element_id=edge_id,
                    element_type="line",
                    field="length_km",
                    message="length_km must be a number",
                )
            )
        elif length_km <= 0:
            errors.append(
                ValidationError(
                    element_id=edge_id,
                    element_type="line",
                    field="length_km",
                    message="length_km must be > 0",
                )
            )

    # Check for at least one ext_grid
    if not ext_grid_nodes:
        errors.append(
            ValidationError(
                element_id="",
                element_type="network",
                field="ext_grid",
                message="At least one ext_grid is required",
            )
        )

    # Check islanding (fatal)
    if not errors:
        errors.extend(_islanding_errors())

    return errors

