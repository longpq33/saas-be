from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

import pandapower as pp  # type: ignore[import-not-found]

from app.models.schemas import CreationStatus, ValidationError


NodeDict = Dict[str, Any]


@dataclass
class ElementContext:
    """
    Context dùng chung khi tạo elements trong pandapowerNet.

    - net: pandapower network
    - maps: ánh xạ reactflow node_id -> pandapower index theo từng bảng element
    - errors/element_status: gom lỗi theo kiểu backend hiện tại
    """

    net: pp.pandapowerNet
    bus_by_id: Dict[str, int] = field(default_factory=dict)
    line_by_id: Dict[str, int] = field(default_factory=dict)
    trafo_by_id: Dict[str, int] = field(default_factory=dict)
    trafo3w_by_id: Dict[str, int] = field(default_factory=dict)

    errors: Dict[str, List[ValidationError]] = field(default_factory=dict)
    element_status: Dict[str, CreationStatus] = field(default_factory=dict)

    def add_error(
        self,
        *,
        element_id: str,
        element_type: str,
        message: str,
        field: Optional[str] = None,
        element_name: Optional[str] = None,
        bucket: Optional[str] = None,
    ) -> None:
        key = bucket or element_type
        self.errors.setdefault(key, []).append(
            ValidationError(
                element_id=element_id,
                element_type=element_type,
                element_name=element_name,
                field=field,
                message=message,
            )
        )

    def set_status_ok(self, *, element_id: str, element_type: str) -> None:
        self.element_status[element_id] = CreationStatus(
            element_id=element_id, element_type=element_type, success=True
        )

    def set_status_fail(self, *, element_id: str, element_type: str, error: str) -> None:
        self.element_status[element_id] = CreationStatus(
            element_id=element_id, element_type=element_type, success=False, error=error
        )


class ElementHandler(Protocol):
    element_type: str

    def validate(self, ctx: ElementContext, node: NodeDict) -> bool: ...
    def create(self, ctx: ElementContext, node: NodeDict) -> Optional[int]: ...


