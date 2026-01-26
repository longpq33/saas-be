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
    vm_pu: Optional[float] = None
    va_degree: Optional[float] = None
    p_mw: Optional[float] = None
    q_mvar: Optional[float] = None


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
    p_mw: Optional[float] = None
    q_mvar: Optional[float] = None


class GenResult(BaseModel):
    p_mw: Optional[float] = None
    q_mvar: Optional[float] = None
    vm_pu: Optional[float] = None


class SGenResult(BaseModel):
    p_mw: Optional[float] = None
    q_mvar: Optional[float] = None


class MotorResult(BaseModel):
    p_mw: Optional[float] = None
    q_mvar: Optional[float] = None


class ShuntResult(BaseModel):
    p_mw: Optional[float] = None
    q_mvar: Optional[float] = None


class StorageResult(BaseModel):
    p_mw: Optional[float] = None
    q_mvar: Optional[float] = None


class LineResult(BaseModel):
    p_from_mw: Optional[float] = None
    q_from_mvar: Optional[float] = None
    p_to_mw: Optional[float] = None
    q_to_mvar: Optional[float] = None
    i_from_ka: Optional[float] = None
    i_to_ka: Optional[float] = None
    loading_percent: Optional[float] = None


class TrafoResult(BaseModel):
    p_hv_mw: Optional[float] = None
    q_hv_mvar: Optional[float] = None
    p_lv_mw: Optional[float] = None
    q_lv_mvar: Optional[float] = None
    i_hv_ka: Optional[float] = None
    i_lv_ka: Optional[float] = None
    loading_percent: Optional[float] = None


class Trafo3WResult(BaseModel):
    p_hv_mw: Optional[float] = None
    q_hv_mvar: Optional[float] = None
    p_mv_mw: Optional[float] = None
    q_mv_mvar: Optional[float] = None
    p_lv_mw: Optional[float] = None
    q_lv_mvar: Optional[float] = None
    i_hv_ka: Optional[float] = None
    i_mv_ka: Optional[float] = None
    i_lv_ka: Optional[float] = None
    loading_percent: Optional[float] = None


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

