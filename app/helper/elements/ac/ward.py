from __future__ import annotations

from typing import Any, Dict, Optional

import pandapower as pp  # type: ignore[import-not-found]

from app.helper.elements.base import ElementContext, NodeDict


class WardHandler:
    """
    Ward element.

    Input contract (node.data):
    - busId: str (required)
    - pz_mw: float (optional, default 0.0)
    - qz_mvar: float (optional, default 0.0)
    - ps_mw: float (optional, default 0.0)
    - qs_mvar: float (optional, default 0.0)
    - name: str (optional)
    - in_service: bool (optional, default True)

    Ghi chú: frontend hiện chưa khai báo type 'ward' trong schemas; handler để sẵn cho phase UI/API sau.
    """

    element_type = "ward"

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

        for f in ("pz_mw", "qz_mvar", "ps_mw", "qs_mvar"):
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
        name = str(data.get("name") or "Ward")
        in_service = bool(data.get("in_service", True))

        try:
            idx = pp.create_ward(
                ctx.net,
                bus=ctx.bus_by_id[bus_id],
                pz_mw=float(data.get("pz_mw", 0.0)),
                qz_mvar=float(data.get("qz_mvar", 0.0)),
                ps_mw=float(data.get("ps_mw", 0.0)),
                qs_mvar=float(data.get("qs_mvar", 0.0)),
                name=name,
                in_service=in_service,
            )
            ctx.set_status_ok(element_id=node_id, element_type=self.element_type)
            return int(idx)
        except Exception as e:  # noqa: BLE001
            ctx.add_error(element_id=node_id, element_type=self.element_type, message=f"Lỗi tạo ward: {e}")
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error=str(e))
            return None


