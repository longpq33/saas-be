from __future__ import annotations

from typing import Any, Dict, Optional

from .base import ElementContext, ElementHandler, NodeDict


class ElementsRegistry:
    def __init__(self) -> None:
        self._handlers: Dict[str, ElementHandler] = {}

    def register(self, handler: ElementHandler) -> None:
        self._handlers[handler.element_type] = handler

    def get(self, element_type: str) -> Optional[ElementHandler]:
        return self._handlers.get(element_type)

    def validate_and_create(self, ctx: ElementContext, node: NodeDict) -> Optional[int]:
        element_type = str(node.get("type") or "")
        handler = self.get(element_type)
        if handler is None:
            # Unknown type: ignore silently for now (builder sẽ quyết định strictness)
            return None

        ok = handler.validate(ctx, node)
        if not ok:
            return None

        return handler.create(ctx, node)


