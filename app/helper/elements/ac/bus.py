from __future__ import annotations

from typing import Any, Dict, Optional

import pandapower as pp  # type: ignore[import-not-found]

from app.helper.elements.base import ElementContext, NodeDict


class BusHandler:
    """
    Bus (AC).

    Input contract (node.data):
    - vn_kv: float (required)
    - name: str (optional)
    - type: str (optional)
    - in_service: bool (optional, default True)
    """

    element_type = "bus"

    def validate(self, ctx: ElementContext, node: NodeDict) -> bool:
        node_id = str(node.get("id") or "")
        data: Dict[str, Any] = node.get("data") or {}

        vn_kv = data.get("vn_kv")
        if vn_kv is None:
            ctx.add_error(
                element_id=node_id,
                element_type=self.element_type,
                field="vn_kv",
                message="Thiếu vn_kv (điện áp danh định, kV).",
            )
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="missing vn_kv")
            return False
        try:
            vn = float(vn_kv)
        except (TypeError, ValueError):
            ctx.add_error(
                element_id=node_id,
                element_type=self.element_type,
                field="vn_kv",
                message="vn_kv phải là số.",
            )
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="invalid vn_kv")
            return False
        if vn <= 0:
            ctx.add_error(
                element_id=node_id,
                element_type=self.element_type,
                field="vn_kv",
                message="vn_kv phải > 0.",
            )
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="vn_kv must be > 0")
            return False

        return True

    def create(self, ctx: ElementContext, node: NodeDict) -> Optional[int]:
        node_id = str(node.get("id") or "")
        data: Dict[str, Any] = node.get("data") or {}

        name = str(data.get("name") or "Bus")
        vn_kv = float(data.get("vn_kv"))
        in_service = bool(data.get("in_service", True))
        type_val = data.get("type")
        type_str = str(type_val) if type_val is not None and str(type_val).strip() else None

        try:
            idx = pp.create_bus(
                ctx.net,
                vn_kv=vn_kv,
                name=name,
                type=type_str,
                in_service=in_service,
            )
            ctx.bus_by_id[node_id] = int(idx)
            ctx.set_status_ok(element_id=node_id, element_type=self.element_type)
            return int(idx)
        except Exception as e:  # noqa: BLE001
            ctx.add_error(
                element_id=node_id,
                element_type=self.element_type,
                message=f"Lỗi tạo bus: {e}",
            )
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error=str(e))
            return None


