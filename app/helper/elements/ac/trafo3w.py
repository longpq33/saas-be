from __future__ import annotations

from typing import Any, Dict, Optional

import pandapower as pp  # type: ignore[import-not-found]

from app.helper.elements.base import ElementContext, NodeDict


class Trafo3WHandler:
    """
    Three-winding transformer (trafo3w).

    Input contract (node.data):
    - hvBusId: str (required)
    - mvBusId: str (required)
    - lvBusId: str (required)
    - std_type: str (required)
    - name: str (optional)
    - in_service: bool (optional, default True)
    """

    element_type = "trafo3w"

    def validate(self, ctx: ElementContext, node: NodeDict) -> bool:
        node_id = str(node.get("id") or "")
        data: Dict[str, Any] = node.get("data") or {}

        hv_id = str(data.get("hvBusId") or "").strip()
        mv_id = str(data.get("mvBusId") or "").strip()
        lv_id = str(data.get("lvBusId") or "").strip()
        if not hv_id or not mv_id or not lv_id:
            ctx.add_error(
                element_id=node_id,
                element_type=self.element_type,
                message="Thiếu hvBusId/mvBusId/lvBusId.",
            )
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="missing bus ids")
            return False

        if len({hv_id, mv_id, lv_id}) != 3:
            ctx.add_error(
                element_id=node_id,
                element_type=self.element_type,
                message="hvBusId/mvBusId/lvBusId phải khác nhau.",
            )
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="duplicate bus ids")
            return False

        for b in (hv_id, mv_id, lv_id):
            if b not in ctx.bus_by_id:
                ctx.add_error(element_id=node_id, element_type=self.element_type, message="Một hoặc nhiều busId không tồn tại.")
                ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="bus not found")
                return False

        std_type = str(data.get("std_type") or "").strip()
        if not std_type:
            ctx.add_error(element_id=node_id, element_type=self.element_type, field="std_type", message="Thiếu std_type.")
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="missing std_type")
            return False

        return True

    def create(self, ctx: ElementContext, node: NodeDict) -> Optional[int]:
        node_id = str(node.get("id") or "")
        data: Dict[str, Any] = node.get("data") or {}

        hv_id = str(data.get("hvBusId") or "").strip()
        mv_id = str(data.get("mvBusId") or "").strip()
        lv_id = str(data.get("lvBusId") or "").strip()
        std_type = str(data.get("std_type") or "").strip()
        name = str(data.get("name") or "Trafo3W")
        in_service = bool(data.get("in_service", True))

        try:
            idx = pp.create_trafo3w(
                ctx.net,
                hv_bus=ctx.bus_by_id[hv_id],
                mv_bus=ctx.bus_by_id[mv_id],
                lv_bus=ctx.bus_by_id[lv_id],
                std_type=std_type,
                name=name,
                in_service=in_service,
            )
            ctx.trafo3w_by_id[node_id] = int(idx)
            ctx.set_status_ok(element_id=node_id, element_type=self.element_type)
            return int(idx)
        except Exception as e:  # noqa: BLE001
            ctx.add_error(element_id=node_id, element_type=self.element_type, message=f"Lỗi tạo trafo3w: {e}")
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error=str(e))
            return None


