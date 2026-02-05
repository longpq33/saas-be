from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandapower as pp  # type: ignore[import-not-found]

from app.models.schemas import CreationStatus, RunSettings, ValidationError


class DCNetworkBuilder:
    """
    DC builder placeholder.
    Hiện tại focus AC; builder này giữ để simulate.py không lỗi import.
    """

    def __init__(self, nodes_by_type: Dict[str, List[Dict[str, Any]]], settings: RunSettings) -> None:
        self.nodes_by_type = nodes_by_type
        self.settings = settings

        self.dc_net: Optional[pp.pandapowerNet] = None
        self.converged: bool = False

        self.element_status: Dict[str, CreationStatus] = {}
        self.errors: Dict[str, List[ValidationError]] = {}

    def has_dc_nodes(self) -> bool:
        for t in ("dc_bus", "dcline", "dc_load", "dc_source"):
            if self.nodes_by_type.get(t):
                return True
        return False

    def build_network(self) -> bool:
        # TODO: implement DC phase sau
        self.dc_net = None
        self.converged = False
        return False

    def add_all_elements(self) -> None:
        return

    def run_powerflow(self) -> None:
        return

    def collect_results(self) -> Dict[str, Any]:
        return {}


