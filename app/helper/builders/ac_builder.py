from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import pandapower as pp  # type: ignore[import-not-found]

from app.helper.elements.ac.registry import build_ac_registry
from app.helper.elements.base import ElementContext
from app.models.schemas import BusResult, CreationStatus, RunSettings, ValidationError


class ACNetworkBuilder:
    def __init__(
        self,
        nodes_by_type: Dict[str, List[Dict[str, Any]]],
        edges: List[Dict[str, Any]],
        settings: RunSettings,
    ) -> None:
        self.nodes_by_type = nodes_by_type
        self.edges = edges
        self.settings = settings

        self.net: Optional[pp.pandapowerNet] = None
        self.converged: bool = False
        self.slack_bus_id: str = ""

        self.element_status: Dict[str, CreationStatus] = {}
        self.errors: Dict[str, List[ValidationError]] = {}
        self.warnings: List[str] = []

        self._registry = build_ac_registry()
        self._ctx: Optional[ElementContext] = None

    def has_ac_nodes(self) -> bool:
        for t in ("bus", "line", "load", "ext_grid", "gen", "sgen", "transformer", "trafo3w", "switch", "motor", "shunt", "storage", "ward"):
            if self.nodes_by_type.get(t):
                return True
        return False

    def build_and_validate(self, all_nodes: List[Dict[str, Any]]) -> bool:
        # Tạo net rỗng
        self.net = pp.create_empty_network()
        self._ctx = ElementContext(net=self.net)

        # Thứ tự phụ thuộc
        order = [
            "bus",
            "ext_grid",
            "line",
            "transformer",
            "trafo3w",
            "load",
            "gen",
            "sgen",
            "motor",
            "storage",
            "shunt",
            "ward",
            "switch",
        ]

        for t in order:
            for node in self.nodes_by_type.get(t, []):
                self._registry.validate_and_create(self._ctx, node)

        self.element_status = dict(self._ctx.element_status)
        self.errors = dict(self._ctx.errors)

        # slack bus id: lấy bus đầu tiên nếu có
        buses = self.nodes_by_type.get("bus") or []
        if buses:
            self.slack_bus_id = str(buses[0].get("id") or "")

        # Nếu có bất kỳ lỗi nào => fail
        return len(self.errors) == 0

    def add_all_elements(self) -> None:
        # Elements đã được tạo trong build_and_validate
        return

    def run_powerflow(self) -> None:
        if self.net is None:
            return
        try:
            pp.runpp(
                self.net,
                algorithm=self.settings.algorithm,
                max_iteration=self.settings.max_iter,
                tolerance_mva=self.settings.tolerance_mva,
            )
            self.converged = bool(getattr(self.net, "converged", False))
        except Exception as e:  # noqa: BLE001
            self.converged = False
            self.errors.setdefault("powerflow", []).append(
                ValidationError(
                    element_id="",
                    element_type="powerflow",
                    message=f"Lỗi runpp: {e}",
                )
            )

    def check_violations(self) -> None:
        # Placeholder: có thể thêm check min/max vm_pu sau
        return

    def collect_bus_results(self) -> Tuple[Dict[str, BusResult], List[Dict[str, Any]]]:
        if self.net is None or self._ctx is None:
            return {}, []
        if not hasattr(self.net, "res_bus"):
            return {}, []

        res_bus = self.net.res_bus
        bus_by_id: Dict[str, BusResult] = {}

        # map theo ctx.bus_by_id
        inv = {idx: node_id for node_id, idx in self._ctx.bus_by_id.items()}
        for idx, row in res_bus.iterrows():
            node_id = inv.get(int(idx))
            if not node_id:
                continue
            # Clean NaN values: replace với 0.0 hoặc None
            vm_pu_val = row.get("vm_pu", 0.0)
            va_degree_val = row.get("va_degree", 0.0)
            p_mw_val = row.get("p_mw", 0.0)
            q_mvar_val = row.get("q_mvar", 0.0)
            
            bus_by_id[node_id] = BusResult(
                vm_pu=_clean_float(vm_pu_val),
                va_degree=_clean_float(va_degree_val),
                p_mw=_clean_float(p_mw_val),
                q_mvar=_clean_float(q_mvar_val),
            )

        # cũng trả list raw cho frontend đang dùng res_bus
        # Clean NaN để JSON serialize được
        res_bus_list = _clean_nan_records(res_bus.reset_index().replace({float("nan"): None}).to_dict(orient="records"))
        return bus_by_id, res_bus_list

    def collect_other_results(self) -> Dict[str, Dict[str, Any]]:
        if self.net is None:
            return {}
        out: Dict[str, Dict[str, Any]] = {}
        for tbl in ("res_line", "res_load", "res_gen", "res_sgen", "res_trafo", "res_trafo3w", "res_shunt", "res_storage", "res_motor"):
            if hasattr(self.net, tbl):
                try:
                    df = getattr(self.net, tbl)
                    # Clean NaN để JSON serialize được
                    records = _clean_nan_records(df.reset_index().replace({float("nan"): None}).to_dict(orient="records"))
                    out[tbl] = records  # type: ignore[assignment]
                except Exception:  # noqa: BLE001
                    pass
        return out


def _clean_float(val: Any) -> float:
    """Clean một giá trị float, replace NaN/inf với 0.0."""
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return 0.0
        return val
    try:
        fval = float(val)
        if math.isnan(fval) or math.isinf(fval):
            return 0.0
        return fval
    except (ValueError, TypeError):
        return 0.0


def _clean_nan_records(records: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """
    Clean NaN values trong list các dict records để JSON serialize được.
    Replace NaN, inf, -inf với None (sẽ thành null trong JSON).
    """
    cleaned = []
    for rec in records:
        cleaned_rec: Dict[str, Any] = {}
        for k, v in rec.items():
            if isinstance(v, float):
                if math.isnan(v) or math.isinf(v):
                    cleaned_rec[k] = None
                else:
                    cleaned_rec[k] = v
            else:
                cleaned_rec[k] = v
        cleaned.append(cleaned_rec)
    return cleaned


