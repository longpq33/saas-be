from __future__ import annotations

import time
from typing import Any, Dict, List

from app.helper.builders import ACNetworkBuilder, DCNetworkBuilder
from app.helper.net_export import export_network
from app.helper.simulate_utils import _parse_edges, _parse_nodes_by_type
from app.models.schemas import (
    BusResult,
    CreationStatus,
    SimulateRequest,
    SimulateResponse,
    Summary,
    ValidationError,
)


def simulate_from_reactflow(request: SimulateRequest) -> SimulateResponse:
    """
    Tạo grid power từ ReactFlow nodes/edges và chạy power flow simulation theo pandapower.

    Luồng xử lý:
    1. Chuẩn hoá và tách nodes/edges theo type
    2. Tạo AC và DC networks
    3. Validate và thêm elements
    4. Chạy power flow
    5. Gom kết quả và trả về SimulateResponse
    """
    start_time = time.time()

    nodes_dict = [node.model_dump() for node in request.nodes]
    edges_dict = _parse_edges(request)
    nodes_by_type = _parse_nodes_by_type(nodes_dict)

    element_status: Dict[str, CreationStatus] = {}
    errors: Dict[str, List[ValidationError]] = {}
    warnings: List[str] = []

    converged = False
    slack_bus_id = ""

    try:
        ac_builder = ACNetworkBuilder(nodes_by_type, edges_dict, request.settings)
        if ac_builder.has_ac_nodes():
            if not ac_builder.build_and_validate(nodes_dict):
                element_status.update(ac_builder.element_status)
                errors.update(ac_builder.errors)
                warnings.extend(ac_builder.warnings)
                return _build_error_response(
                    start_time, errors, element_status, warnings, ac_builder.slack_bus_id
                )

            ac_builder.add_all_elements()
            ac_builder.run_powerflow()
            ac_builder.check_violations()

            element_status.update(ac_builder.element_status)
            errors.update(ac_builder.errors)
            warnings.extend(ac_builder.warnings)

            converged = ac_builder.converged
            slack_bus_id = ac_builder.slack_bus_id

        dc_builder = DCNetworkBuilder(nodes_by_type, request.settings)
        if dc_builder.has_dc_nodes():
            ok = dc_builder.build_network()
            # Always merge errors/status even if creation failed, to avoid silent failures.
            element_status.update(dc_builder.element_status)
            errors.update(dc_builder.errors)

            if ok:
                dc_builder.add_all_elements()
                dc_builder.run_powerflow()

                element_status.update(dc_builder.element_status)
                errors.update(dc_builder.errors)

                if not ac_builder.has_ac_nodes():
                    converged = dc_builder.converged
                elif ac_builder.converged and dc_builder.converged:
                    converged = True
                else:
                    converged = False

        runtime_ms = int((time.time() - start_time) * 1000)

        bus_by_id: Dict[str, BusResult] = {}
        res_bus: List[Dict[str, Any]] = []
        results: Dict[str, Any] = {}

        if ac_builder.has_ac_nodes():
            bus_by_id, res_bus = ac_builder.collect_bus_results()
            results = ac_builder.collect_other_results()

        if dc_builder.has_dc_nodes() and dc_builder.converged:
            dc_results = dc_builder.collect_results()
            if dc_results:
                results.update(dc_results)

        network_payload = None
        if ac_builder.has_ac_nodes() and ac_builder.net is not None:
            network_payload = export_network(ac_builder.net, mode=request.settings.return_network)

        if dc_builder.has_dc_nodes() and dc_builder.dc_net is not None:
            dc_network_payload = export_network(dc_builder.dc_net, mode=request.settings.return_network)
            if dc_network_payload:
                if network_payload:
                    if "tables" in network_payload and "tables" in dc_network_payload:
                        network_payload["tables"].update(dc_network_payload["tables"])
                    if "results" in network_payload and "results" in dc_network_payload:
                        network_payload["results"].update(dc_network_payload["results"])
                    if "meta" in dc_network_payload:
                        if "meta" not in network_payload:
                            network_payload["meta"] = {}
                        network_payload["meta"]["dc_converged"] = dc_builder.converged
                        if "counts" in dc_network_payload["meta"]:
                            if "counts" not in network_payload["meta"]:
                                network_payload["meta"]["counts"] = {}
                            network_payload["meta"]["counts"].update(dc_network_payload["meta"]["counts"])
                else:
                    network_payload = dc_network_payload
                    if "meta" in network_payload:
                        network_payload["meta"]["dc_converged"] = dc_builder.converged

        # Gắn cờ hội tụ tổng thể vào meta nếu có network payload
        if network_payload is not None:
            meta = network_payload.setdefault("meta", {})
            meta["converged"] = converged

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
