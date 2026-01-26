from __future__ import annotations

from typing import Any, Dict, List

from app.models.schemas import ValidationError


def _validate_network(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    bus_index_by_node_id: Dict[str, int],
) -> List[ValidationError]:
    """Validate network before creating elements. Returns list of validation errors."""
    errors: List[ValidationError] = []

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

    # Validate bus-bound elements (load, gen, ext_grid, motor, shunt, storage)
    for node in load_nodes + gen_nodes + sgen_nodes + motor_nodes + shunt_nodes + storage_nodes + ext_grid_nodes:
        node_id = node.get("id", "")
        node_type = node.get("type", "")
        data = node.get("data") or {}
        bus_id = str(data.get("busId", ""))

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

        # std_type is optional for lines (has default), but we can validate if provided
        # We'll skip std_type validation here as pandapower will handle it

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

    return errors

