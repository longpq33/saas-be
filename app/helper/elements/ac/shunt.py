from __future__ import annotations

from typing import Any, Dict, Optional

import pandapower as pp  # type: ignore[import-not-found]

from app.helper.elements.base import ElementContext, NodeDict


class ShuntHandler:
    """
    Shunt.

    Input contract (node.data):
    - busId: str (required)
    - p_mw: float (optional, default 0.0)
    - q_mvar: float (optional, default 0.0)
    - vn_kv: float (optional)
    - step: int|float (optional)
    - max_step: int|float (optional)
    - name: str (optional)
    - in_service: bool (optional, default True)
    """

    element_type = "shunt"

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

        for f in ("p_mw", "q_mvar", "vn_kv", "step", "max_step"):
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
        name = str(data.get("name") or "Shunt")
        in_service = bool(data.get("in_service", True))

        step = data.get("step")
        max_step = data.get("max_step")
        step_val = float(step) if step is not None else None
        max_step_val = float(max_step) if max_step is not None else None

        vn_kv = data.get("vn_kv")
        vn_kv_val = float(vn_kv) if vn_kv is not None else None

        try:
            idx = pp.create_shunt(
                ctx.net,
                bus=ctx.bus_by_id[bus_id],
                p_mw=float(data.get("p_mw", 0.0)),
                q_mvar=float(data.get("q_mvar", 0.0)),
                vn_kv=vn_kv_val if vn_kv_val is not None else float(ctx.net.bus.loc[ctx.bus_by_id[bus_id], "vn_kv"]),
                step=step_val,
                max_step=max_step_val,
                name=name,
                in_service=in_service,
            )
            ctx.set_status_ok(element_id=node_id, element_type=self.element_type)
            return int(idx)
        except Exception as e:  # noqa: BLE001
            ctx.add_error(element_id=node_id, element_type=self.element_type, message=f"Lỗi tạo shunt: {e}")
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error=str(e))
            return None


