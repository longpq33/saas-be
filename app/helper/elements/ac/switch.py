from __future__ import annotations

from typing import Any, Dict, Optional

import pandapower as pp  # type: ignore[import-not-found]

from app.helper.elements.base import ElementContext, NodeDict


class SwitchHandler:
    """
    Switch (adv).

    Input contract (node.data):
    - busId: str (required)
    - elementType: str (required)  # "bus" | "line" | "trafo"
    - elementId: str (required)    # reactflow node id của element target
    - closed: bool (optional, default True)
    - type: str (optional)         # switch type (CB/DS/...)
    - z_ohm: float (optional)
    - name: str (optional)
    - in_service: bool (optional, default True)
    """

    element_type = "switch"

    def validate(self, ctx: ElementContext, node: NodeDict) -> bool:
        node_id = str(node.get("id") or "")
        data: Dict[str, Any] = node.get("data") or {}

        bus_id = str(data.get("busId") or "").strip()
        if not bus_id:
            ctx.add_error(element_id=node_id, element_type=self.element_type, field="busId", message="Thiếu busId.")
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="missing busId")
            return False
        if bus_id not in ctx.bus_by_id:
            ctx.add_error(element_id=node_id, element_type=self.element_type, field="busId", message=f"busId '{bus_id}' không tồn tại.")
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="busId not found")
            return False

        element_type = str(data.get("elementType") or "").strip()
        element_id = str(data.get("elementId") or "").strip()
        if not element_type:
            ctx.add_error(element_id=node_id, element_type=self.element_type, field="elementType", message="Thiếu elementType.")
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="missing elementType")
            return False
        if not element_id:
            ctx.add_error(element_id=node_id, element_type=self.element_type, field="elementId", message="Thiếu elementId.")
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="missing elementId")
            return False

        if element_type == "line":
            if element_id not in ctx.line_by_id:
                ctx.add_error(
                    element_id=node_id,
                    element_type=self.element_type,
                    message=f"elementId '{element_id}' (line) không tồn tại.",
                )
                ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="line not found")
                return False
        elif element_type == "trafo":
            if element_id not in ctx.trafo_by_id:
                ctx.add_error(
                    element_id=node_id,
                    element_type=self.element_type,
                    message=f"elementId '{element_id}' (trafo) không tồn tại.",
                )
                ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="trafo not found")
                return False
        elif element_type == "bus":
            if element_id not in ctx.bus_by_id:
                ctx.add_error(
                    element_id=node_id,
                    element_type=self.element_type,
                    message=f"elementId '{element_id}' (bus) không tồn tại.",
                )
                ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="bus not found")
                return False
        else:
            ctx.add_error(
                element_id=node_id,
                element_type=self.element_type,
                field="elementType",
                message=f"elementType '{element_type}' không hợp lệ (chỉ bus/line/trafo).",
            )
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="invalid elementType")
            return False

        if data.get("z_ohm") is not None:
            try:
                float(data.get("z_ohm"))
            except (TypeError, ValueError):
                ctx.add_error(element_id=node_id, element_type=self.element_type, field="z_ohm", message="z_ohm phải là số.")
                ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="invalid z_ohm")
                return False

        return True

    def create(self, ctx: ElementContext, node: NodeDict) -> Optional[int]:
        node_id = str(node.get("id") or "")
        data: Dict[str, Any] = node.get("data") or {}

        bus_id = str(data.get("busId") or "").strip()
        element_type = str(data.get("elementType") or "").strip()
        element_id = str(data.get("elementId") or "").strip()

        et: str
        element_idx: int
        if element_type == "line":
            et = "l"
            element_idx = ctx.line_by_id[element_id]
        elif element_type == "trafo":
            et = "t"
            element_idx = ctx.trafo_by_id[element_id]
        else:
            et = "b"
            element_idx = ctx.bus_by_id[element_id]

        name = str(data.get("name") or "Switch")
        closed = bool(data.get("closed", True))
        in_service = bool(data.get("in_service", True))
        sw_type_raw = data.get("type")
        sw_type = str(sw_type_raw) if sw_type_raw is not None and str(sw_type_raw).strip() else None
        z_ohm_raw = data.get("z_ohm")
        z_ohm = float(z_ohm_raw) if z_ohm_raw is not None else None

        try:
            idx = pp.create_switch(
                ctx.net,
                bus=ctx.bus_by_id[bus_id],
                element=element_idx,
                et=et,
                closed=closed,
                type=sw_type,
                z_ohm=z_ohm,
                name=name,
                in_service=in_service,
            )
            ctx.set_status_ok(element_id=node_id, element_type=self.element_type)
            return int(idx)
        except Exception as e:  # noqa: BLE001
            ctx.add_error(element_id=node_id, element_type=self.element_type, message=f"Lỗi tạo switch: {e}")
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error=str(e))
            return None


