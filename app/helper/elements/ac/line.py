from __future__ import annotations

from typing import Any, Dict, Optional

import pandapower as pp

from app.helper.elements.base import ElementContext, NodeDict


class LineHandler:
    """
    Line (AC).

    Input contract (node.data) có 2 đường:
    - Std type:
      - fromBusId: str (required)
      - toBusId: str (required)
      - length_km: float (required)
      - std_type: str (required)
    - From parameters:
      - fromBusId, toBusId, length_km (required)
      - r_ohm_per_km, x_ohm_per_km, c_nf_per_km, max_i_ka (required)

    Optional: name, in_service, parallel, df
    """

    element_type = "line"

    def validate(self, ctx: ElementContext, node: NodeDict) -> bool:
        node_id = str(node.get("id") or "")
        data: Dict[str, Any] = node.get("data") or {}

        from_bus_id = str(data.get("fromBusId") or "").strip()
        to_bus_id = str(data.get("toBusId") or "").strip()
        if not from_bus_id:
            ctx.add_error(
                element_id=node_id, element_type=self.element_type, field="fromBusId", message="Thiếu fromBusId."
            )
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="missing fromBusId")
            return False
        if not to_bus_id:
            ctx.add_error(
                element_id=node_id, element_type=self.element_type, field="toBusId", message="Thiếu toBusId."
            )
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="missing toBusId")
            return False
        if from_bus_id == to_bus_id:
            ctx.add_error(
                element_id=node_id,
                element_type=self.element_type,
                message="fromBusId và toBusId không được trùng nhau.",
            )
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="from==to")
            return False
        if from_bus_id not in ctx.bus_by_id or to_bus_id not in ctx.bus_by_id:
            ctx.add_error(
                element_id=node_id,
                element_type=self.element_type,
                message="fromBusId/toBusId không tồn tại.",
            )
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="bus not found")
            return False

        # Kiểm tra mức điện áp giữa hai bus: line chỉ nên nối các bus cùng cấp điện áp
        from_idx = ctx.bus_by_id[from_bus_id]
        to_idx = ctx.bus_by_id[to_bus_id]
        try:
            vn_from = float(ctx.net.bus.at[from_idx, "vn_kv"])  # type: ignore[attr-defined]
            vn_to = float(ctx.net.bus.at[to_idx, "vn_kv"])      # type: ignore[attr-defined]
            # Nếu chênh lệch điện áp danh định quá lớn (ví dụ > 1 kV) thì coi là khác cấp điện áp
            if abs(vn_from - vn_to) > 1.0:
                ctx.add_error(
                    element_id=node_id,
                    element_type=self.element_type,
                    message=f"Bus {from_bus_id} ({vn_from} kV) và {to_bus_id} ({vn_to} kV) khác cấp điện áp, "
                    "hãy dùng transformer thay vì line.",
                )
                ctx.set_status_fail(
                    element_id=node_id,
                    element_type=self.element_type,
                    error="voltage level mismatch",
                )
                return False
        except Exception:  # noqa: BLE001
            # Nếu vì lý do nào đó không đọc được vn_kv, bỏ qua check này để không chặn sai
            pass

        if data.get("length_km") is None:
            ctx.add_error(
                element_id=node_id, element_type=self.element_type, field="length_km", message="Thiếu length_km."
            )
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="missing length_km")
            return False
        try:
            length_km = float(data.get("length_km"))
        except (TypeError, ValueError):
            ctx.add_error(
                element_id=node_id, element_type=self.element_type, field="length_km", message="length_km phải là số."
            )
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="invalid length_km")
            return False
        if length_km <= 0:
            ctx.add_error(
                element_id=node_id, element_type=self.element_type, field="length_km", message="length_km phải > 0."
            )
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error="length_km must be > 0")
            return False

        std_type = str(data.get("std_type") or "").strip()
        if std_type:
            return True

        # from_parameters requires these fields
        required = ("r_ohm_per_km", "x_ohm_per_km", "c_nf_per_km", "max_i_ka")
        for f in required:
            if data.get(f) is None:
                ctx.add_error(
                    element_id=node_id, element_type=self.element_type, field=f, message=f"Thiếu {f}."
                )
                ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error=f"missing {f}")
                return False
            try:
                float(data.get(f))
            except (TypeError, ValueError):
                ctx.add_error(
                    element_id=node_id, element_type=self.element_type, field=f, message=f"{f} phải là số."
                )
                ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error=f"invalid {f}")
                return False

        return True

    def create(self, ctx: ElementContext, node: NodeDict) -> Optional[int]:
        node_id = str(node.get("id") or "")
        data: Dict[str, Any] = node.get("data") or {}

        from_bus_id = str(data.get("fromBusId") or "").strip()
        to_bus_id = str(data.get("toBusId") or "").strip()
        from_bus = ctx.bus_by_id[from_bus_id]
        to_bus = ctx.bus_by_id[to_bus_id]

        name_val = data.get("name")
        name = str(name_val) if name_val is not None and str(name_val).strip() else None
        length_km = float(data.get("length_km"))
        in_service = bool(data.get("in_service", True))
        parallel = int(data.get("parallel", 1)) if data.get("parallel") is not None else 1
        df = float(data.get("df", 1.0)) if data.get("df") is not None else 1.0

        std_type = str(data.get("std_type") or "").strip()
        try:
            if std_type:
                idx = pp.create_line(
                    ctx.net,
                    from_bus=from_bus,
                    to_bus=to_bus,
                    length_km=length_km,
                    std_type=std_type,
                    name=name,
                    in_service=in_service,
                    parallel=parallel,
                    df=df,
                )
            else:
                idx = pp.create_line_from_parameters(
                    ctx.net,
                    from_bus=from_bus,
                    to_bus=to_bus,
                    length_km=length_km,
                    r_ohm_per_km=float(data.get("r_ohm_per_km")),
                    x_ohm_per_km=float(data.get("x_ohm_per_km")),
                    c_nf_per_km=float(data.get("c_nf_per_km")),
                    max_i_ka=float(data.get("max_i_ka")),
                    name=name,
                    in_service=in_service,
                    parallel=parallel,
                    df=df,
                )

            ctx.line_by_id[node_id] = int(idx)
            ctx.set_status_ok(element_id=node_id, element_type=self.element_type)
            return int(idx)
        except Exception as e:  # noqa: BLE001
            ctx.add_error(element_id=node_id, element_type=self.element_type, message=f"Lỗi tạo line: {e}")
            ctx.set_status_fail(element_id=node_id, element_type=self.element_type, error=str(e))
            return None


