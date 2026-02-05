from __future__ import annotations

from typing import Any, Dict, Optional

import pandapower as pp  # type: ignore[import-not-found]

from app.helper.elements.base import ElementContext, NodeDict


class TrafoHandler:
    """
    Transformer 2-winding (trafo).

    ReactFlow type hiện tại là "transformer".

    Input contract (node.data):
    - hvBusId: str (required)
    - lvBusId: str (required)
    - std_type: str (required)  # dùng standard type library
    - name: str (optional)
    - in_service: bool (optional, default True)
    """

    element_type = "transformer"

    def validate(self, ctx: ElementContext, node: NodeDict) -> bool:
        node_id = str(node.get("id") or "")
        data: Dict[str, Any] = node.get("data") or {}

        hv_id = str(data.get("hvBusId") or "").strip()
        lv_id = str(data.get("lvBusId") or "").strip()
        if not hv_id:
            ctx.add_error(element_id=node_id, element_type=self.element_type, field="hvBusId", message="Thiếu hvBusId.")
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="missing hvBusId")
            return False
        if not lv_id:
            ctx.add_error(element_id=node_id, element_type=self.element_type, field="lvBusId", message="Thiếu lvBusId.")
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="missing lvBusId")
            return False
        if hv_id == lv_id:
            ctx.add_error(
                element_id=node_id,
                element_type=self.element_type,
                message="hvBusId và lvBusId không được trùng nhau.",
            )
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="hv==lv")
            return False
        if hv_id not in ctx.bus_by_id or lv_id not in ctx.bus_by_id:
            ctx.add_error(element_id=node_id, element_type=self.element_type, message="hvBusId/lvBusId không tồn tại.")
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
        lv_id = str(data.get("lvBusId") or "").strip()
        std_type = str(data.get("std_type") or "").strip()
        name = str(data.get("name") or "Transformer")
        in_service = bool(data.get("in_service", True))

        try:
            idx = pp.create_transformer(
                ctx.net,
                hv_bus=ctx.bus_by_id[hv_id],
                lv_bus=ctx.bus_by_id[lv_id],
                std_type=std_type,
                name=name,
                in_service=in_service,
            )
            ctx.trafo_by_id[node_id] = int(idx)
            ctx.set_status_ok(element_id=node_id, element_type=self.element_type)
            return int(idx)
        except Exception as e:  # noqa: BLE001
            ctx.add_error(element_id=node_id, element_type=self.element_type, message=f"Lỗi tạo transformer: {e}")
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error=str(e))
            return None


