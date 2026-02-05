from __future__ import annotations

from typing import Any, Dict, Optional

import pandapower as pp  # type: ignore[import-not-found]

from app.helper.elements.base import ElementContext, NodeDict


class SGenHandler:
    """
    Static Generator (sgen).

    Input contract (node.data):
    - busId: str (required)
    - p_mw: float (required)
    - q_mvar: float (optional, default 0.0)
    - controllable: bool (optional, default True)
    - name: str (optional)
    - in_service: bool (optional, default True)
    """

    element_type = "sgen"

    def validate(self, ctx: ElementContext, node: NodeDict) -> bool:
        node_id = str(node.get("id") or "")
        data: Dict[str, Any] = node.get("data") or {}

        bus_id = str(data.get("busId") or "").strip()
        if not bus_id:
            ctx.add_error(element_id=node_id, element_type=self.element_type, field="busId", message="Thiếu busId.")
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="missing busId")
            return False
        if bus_id not in ctx.bus_by_id:
            ctx.add_error(
                element_id=node_id, element_type=self.element_type, field="busId", message=f"busId '{bus_id}' không tồn tại."
            )
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="busId not found")
            return False

        if data.get("p_mw") is None:
            ctx.add_error(element_id=node_id, element_type=self.element_type, field="p_mw", message="Thiếu p_mw.")
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="missing p_mw")
            return False

        for f in ("p_mw", "q_mvar"):
            if data.get(f) is None:
                continue
            try:
                float(data.get(f))
            except (TypeError, ValueError):
                ctx.add_error(element_id=node_id, element_type=self.element_type, field=f, message=f"{f} phải là số.")
                ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error=f"invalid {f}")
                return False

        return True

    def create(self, ctx: ElementContext, node: NodeDict) -> Optional[int]:
        node_id = str(node.get("id") or "")
        data: Dict[str, Any] = node.get("data") or {}

        bus_id = str(data.get("busId") or "").strip()
        name = str(data.get("name") or "SGen")
        p_mw = float(data.get("p_mw"))
        q_mvar = float(data.get("q_mvar", 0.0))
        in_service = bool(data.get("in_service", True))
        controllable = bool(data.get("controllable", True))

        try:
            idx = pp.create_sgen(
                ctx.net,
                bus=ctx.bus_by_id[bus_id],
                p_mw=p_mw,
                q_mvar=q_mvar,
                name=name,
                in_service=in_service,
                controllable=controllable,
            )
            ctx.set_status_ok(element_id=node_id, element_type=self.element_type)
            return int(idx)
        except Exception as e:  # noqa: BLE001
            ctx.add_error(element_id=node_id, element_type=self.element_type, message=f"Lỗi tạo sgen: {e}")
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error=str(e))
            return None


