from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class BusData(BaseModel):
    name: str = "Bus"
    vn_kv: float = 22
    type: Optional[str] = None
    min_vm_pu: Optional[float] = None
    max_vm_pu: Optional[float] = None
    geodata: Optional[Dict[str, float]] = None
    in_service: bool = True


class LoadData(BaseModel):
    name: str = "Load"
    busId: str = ""
    p_mw: float = 1
    q_mvar: float = 0
    scaling: float = 1
    in_service: bool = True
    type: str = ""
    controllable: bool = False


class ReactFlowNode(BaseModel):
    id: str
    type: Literal[
        "bus",
        "load",
        "transformer",
        "ext_grid",
        "gen",
        "sgen",
        "switch",
        "motor",
        "shunt",
        "storage",
        "trafo3w",
    ]
    data: Dict[str, Any]


class ReactFlowEdge(BaseModel):
    id: Optional[str] = None
    source: str
    target: str
    data: Optional[Dict[str, Any]] = None


class RunSettings(BaseModel):
    algorithm: str = "nr"
    max_iter: int = 20
    tolerance_mva: float = 1e-6


class SimulateRequest(BaseModel):
    nodes: List[ReactFlowNode]
    edges: List[ReactFlowEdge] = Field(default_factory=list)
    settings: RunSettings = Field(default_factory=RunSettings)


class BusResult(BaseModel):
    vm_pu: float
    va_degree: float
    p_mw: float
    q_mvar: float


class ValidationError(BaseModel):
    element_id: str
    element_type: str
    field: Optional[str] = None
    message: str


class CreationStatus(BaseModel):
    element_id: str
    element_type: str
    success: bool
    error: Optional[str] = None


class LoadResult(BaseModel):
    p_mw: float
    q_mvar: float


class GenResult(BaseModel):
    p_mw: float
    q_mvar: float
    vm_pu: float


class SGenResult(BaseModel):
    p_mw: float
    q_mvar: float


class MotorResult(BaseModel):
    p_mw: float
    q_mvar: float


class ShuntResult(BaseModel):
    p_mw: float
    q_mvar: float


class StorageResult(BaseModel):
    p_mw: float
    q_mvar: float


class LineResult(BaseModel):
    p_from_mw: float
    q_from_mvar: float
    p_to_mw: float
    q_to_mvar: float
    i_from_ka: float
    i_to_ka: float
    loading_percent: float


class TrafoResult(BaseModel):
    p_hv_mw: float
    q_hv_mvar: float
    p_lv_mw: float
    q_lv_mvar: float
    i_hv_ka: float
    i_lv_ka: float
    loading_percent: float


class Trafo3WResult(BaseModel):
    p_hv_mw: float
    q_hv_mvar: float
    p_mv_mw: float
    q_mv_mvar: float
    p_lv_mw: float
    q_lv_mvar: float
    i_hv_ka: float
    i_mv_ka: float
    i_lv_ka: float
    loading_percent: float


class Summary(BaseModel):
    converged: bool
    runtime_ms: int
    slack_bus_id: str


class SimulateResponse(BaseModel):
    summary: Summary
    bus_by_id: Dict[str, BusResult]
    res_bus: List[Dict[str, Any]]
    warnings: List[str] = Field(default_factory=list)
    errors: Dict[str, List[ValidationError]] = Field(default_factory=dict)
    element_status: Dict[str, CreationStatus] = Field(default_factory=dict)
    results: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

