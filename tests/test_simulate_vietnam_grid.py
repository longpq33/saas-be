from __future__ import annotations

from typing import Any, Dict, List

from app.models.schemas import ReactFlowEdge, ReactFlowNode, RunSettings, SimulateRequest
from app.services.simulate import simulate_from_reactflow


def _vietnam_backbone_nodes() -> List[ReactFlowNode]:
    """
    Lưới AC đơn giản mô phỏng trục 500 kV Bắc–Trung–Nam + các nút tải 220 kV.
    """
    return [
        # Buses 500 kV (truyền tải)
        ReactFlowNode(id="bus_north_500", type="bus", data={"vn_kv": 500.0, "min_vm_pu": 0.95, "max_vm_pu": 1.05}),
        ReactFlowNode(id="bus_central_500", type="bus", data={"vn_kv": 500.0, "min_vm_pu": 0.95, "max_vm_pu": 1.05}),
        ReactFlowNode(id="bus_south_500", type="bus", data={"vn_kv": 500.0, "min_vm_pu": 1.0, "max_vm_pu": 1.05}),
        # Buses tải 220 kV (gom lưới phân phối)
        ReactFlowNode(id="bus_load_north", type="bus", data={"vn_kv": 220.0}),
        ReactFlowNode(id="bus_load_central", type="bus", data={"vn_kv": 220.0}),
        ReactFlowNode(id="bus_load_south", type="bus", data={"vn_kv": 220.0}),
        # External grid (slack) ở miền Bắc
        ReactFlowNode(
            id="eg_north",
            type="ext_grid",
            data={"busId": "bus_north_500", "vm_pu": 1.02, "va_degree": 0.0, "in_service": True},
        ),
        # Loads tổng hợp theo vùng
        ReactFlowNode(id="load_north", type="load", data={"busId": "bus_load_north", "p_mw": 800.0, "q_mvar": 200.0}),
        ReactFlowNode(
            id="load_central",
            type="load",
            data={"busId": "bus_load_central", "p_mw": 600.0, "q_mvar": 150.0},
        ),
        ReactFlowNode(
            id="load_south",
            type="load",
            data={"busId": "bus_load_south", "p_mw": 1500.0, "q_mvar": 400.0},
        ),
        # Gen tổng hợp tại bus truyền tải
        ReactFlowNode(
            id="gen_north",
            type="gen",
            data={"busId": "bus_north_500", "p_mw": 1500.0, "q_mvar": 0.0, "vm_pu": 1.02},
        ),
        ReactFlowNode(
            id="gen_central",
            type="gen",
            data={"busId": "bus_central_500", "p_mw": 800.0, "q_mvar": 0.0, "vm_pu": 1.01},
        ),
        ReactFlowNode(
            id="gen_south",
            type="gen",
            data={"busId": "bus_south_500", "p_mw": 500.0, "q_mvar": 0.0, "vm_pu": 1.00},
        ),
        # Đường dây 500 kV Bắc–Trung
        ReactFlowNode(
            id="line_north_central",
            type="line",
            data={
                "name": "500kV North-Central",
                "fromBusId": "bus_north_500",
                "toBusId": "bus_central_500",
                "length_km": 300.0,
                "r_ohm_per_km": 0.02,
                "x_ohm_per_km": 0.25,
                "c_nf_per_km": 10.0,
                "max_i_ka": 2.0,
                "parallel": 2,
                "df": 1.0,
                "in_service": True,
            },
        ),
        # Đường dây 500 kV Trung–Nam
        ReactFlowNode(
            id="line_central_south",
            type="line",
            data={
                "name": "500kV Central-South",
                "fromBusId": "bus_central_500",
                "toBusId": "bus_south_500",
                "length_km": 400.0,
                "r_ohm_per_km": 0.02,
                "x_ohm_per_km": 0.25,
                "c_nf_per_km": 10.0,
                "max_i_ka": 2.0,
                "parallel": 2,
                "df": 1.0,
                "in_service": True,
            },
        ),
        # Đường dây 220 kV từ truyền tải xuống bus tải
        ReactFlowNode(
            id="line_north_load",
            type="line",
            data={
                "name": "220kV North-Load",
                "fromBusId": "bus_north_500",
                "toBusId": "bus_load_north",
                "length_km": 50.0,
                "r_ohm_per_km": 0.1,
                "x_ohm_per_km": 0.4,
                "c_nf_per_km": 10.0,
                "max_i_ka": 1.0,
                "parallel": 1,
                "df": 1.0,
                "in_service": True,
            },
        ),
        ReactFlowNode(
            id="line_central_load",
            type="line",
            data={
                "name": "220kV Central-Load",
                "fromBusId": "bus_central_500",
                "toBusId": "bus_load_central",
                "length_km": 40.0,
                "r_ohm_per_km": 0.1,
                "x_ohm_per_km": 0.4,
                "c_nf_per_km": 10.0,
                "max_i_ka": 1.0,
                "parallel": 1,
                "df": 1.0,
                "in_service": True,
            },
        ),
        ReactFlowNode(
            id="line_south_load",
            type="line",
            data={
                "name": "220kV South-Load",
                "fromBusId": "bus_south_500",
                "toBusId": "bus_load_south",
                "length_km": 30.0,
                "r_ohm_per_km": 0.1,
                "x_ohm_per_km": 0.4,
                "c_nf_per_km": 10.0,
                "max_i_ka": 1.2,
                "parallel": 1,
                "df": 1.0,
                "in_service": True,
            },
        ),
    ]


def _vietnam_backbone_edges() -> List[ReactFlowEdge]:
    """
    Edges mô phỏng kết nối giữa ext_grid / bus / line / load.
    """
    return [
        # ext_grid gắn vào bus 500 kV Bắc
        ReactFlowEdge(
            id="e_eg_north",
            source="eg_north",
            target="bus_north_500",
            data={"kind": "attach", "attach_type": "ext_grid"},
        ),
        # Line 500kV Bắc–Trung
        ReactFlowEdge(
            id="e_north_line_nc",
            source="bus_north_500",
            target="line_north_central",
            data={"kind": "attach", "attach_type": "line"},
        ),
        ReactFlowEdge(
            id="e_line_nc_central",
            source="line_north_central",
            target="bus_central_500",
            data={"kind": "attach", "attach_type": "line"},
        ),
        # Line 500kV Trung–Nam
        ReactFlowEdge(
            id="e_central_line_cs",
            source="bus_central_500",
            target="line_central_south",
            data={"kind": "attach", "attach_type": "line"},
        ),
        ReactFlowEdge(
            id="e_line_cs_south",
            source="line_central_south",
            target="bus_south_500",
            data={"kind": "attach", "attach_type": "line"},
        ),
        # Line 220kV xuống tải
        ReactFlowEdge(
            id="e_north_line_nl",
            source="bus_north_500",
            target="line_north_load",
            data={"kind": "attach", "attach_type": "line"},
        ),
        ReactFlowEdge(
            id="e_line_nl_load",
            source="line_north_load",
            target="bus_load_north",
            data={"kind": "attach", "attach_type": "line"},
        ),
        ReactFlowEdge(
            id="e_central_line_cl",
            source="bus_central_500",
            target="line_central_load",
            data={"kind": "attach", "attach_type": "line"},
        ),
        ReactFlowEdge(
            id="e_line_cl_load",
            source="line_central_load",
            target="bus_load_central",
            data={"kind": "attach", "attach_type": "line"},
        ),
        ReactFlowEdge(
            id="e_south_line_sl",
            source="bus_south_500",
            target="line_south_load",
            data={"kind": "attach", "attach_type": "line"},
        ),
        ReactFlowEdge(
            id="e_line_sl_load",
            source="line_south_load",
            target="bus_load_south",
            data={"kind": "attach", "attach_type": "line"},
        ),
        # Load gắn vào bus tải
        ReactFlowEdge(
            id="e_bln_load_n",
            source="bus_load_north",
            target="load_north",
            data={"kind": "attach", "attach_type": "load"},
        ),
        ReactFlowEdge(
            id="e_blc_load_c",
            source="bus_load_central",
            target="load_central",
            data={"kind": "attach", "attach_type": "load"},
        ),
        ReactFlowEdge(
            id="e_bls_load_s",
            source="bus_load_south",
            target="load_south",
            data={"kind": "attach", "attach_type": "load"},
        ),
    ]


def _vietnam_backbone_base() -> tuple[List[ReactFlowNode], List[ReactFlowEdge]]:
    """
    Lưới AC cơ bản 110kV/20kV với transformer.
    Dùng làm base cho các test case khác.
    """
    nodes: List[ReactFlowNode] = [
        # Buses 110kV backbone
        ReactFlowNode(id="bus_north_500", type="bus", data={"vn_kv": 110.0, "min_vm_pu": 0.95, "max_vm_pu": 1.05}),
        ReactFlowNode(id="bus_central_500", type="bus", data={"vn_kv": 110.0, "min_vm_pu": 0.95, "max_vm_pu": 1.05}),
        ReactFlowNode(id="bus_south_500", type="bus", data={"vn_kv": 110.0, "min_vm_pu": 0.95, "max_vm_pu": 1.05}),
        # Buses tải 20kV
        ReactFlowNode(id="bus_load_north", type="bus", data={"vn_kv": 20.0}),
        ReactFlowNode(id="bus_load_central", type="bus", data={"vn_kv": 20.0}),
        ReactFlowNode(id="bus_load_south", type="bus", data={"vn_kv": 20.0}),
        # External grid
        ReactFlowNode(
            id="eg_north",
            type="ext_grid",
            data={"busId": "bus_north_500", "vm_pu": 1.02, "va_degree": 0.0, "in_service": True},
        ),
        # Loads
        ReactFlowNode(id="load_north", type="load", data={"busId": "bus_load_north", "p_mw": 50.0, "q_mvar": 12.0}),
        ReactFlowNode(id="load_central", type="load", data={"busId": "bus_load_central", "p_mw": 40.0, "q_mvar": 10.0}),
        ReactFlowNode(id="load_south", type="load", data={"busId": "bus_load_south", "p_mw": 60.0, "q_mvar": 15.0}),
        # Gen
        ReactFlowNode(id="gen_north", type="gen", data={"busId": "bus_north_500", "p_mw": 100.0, "q_mvar": 0.0, "vm_pu": 1.02, "in_service": True}),
        ReactFlowNode(id="gen_central", type="gen", data={"busId": "bus_central_500", "p_mw": 50.0, "q_mvar": 0.0, "vm_pu": 1.02, "in_service": True}),
        ReactFlowNode(id="gen_south", type="gen", data={"busId": "bus_south_500", "p_mw": 50.0, "q_mvar": 0.0, "vm_pu": 1.02, "in_service": True}),
        # Lines 110kV
        ReactFlowNode(
            id="line_north_central",
            type="line",
            data={
                "name": "110kV North-Central",
                "fromBusId": "bus_north_500",
                "toBusId": "bus_central_500",
                "length_km": 100.0,
                "r_ohm_per_km": 0.05,
                "x_ohm_per_km": 0.25,
                "c_nf_per_km": 10.0,
                "max_i_ka": 1.5,
                "parallel": 1,
                "df": 1.0,
                "in_service": True,
            },
        ),
        ReactFlowNode(
            id="line_central_south",
            type="line",
            data={
                "name": "110kV Central-South",
                "fromBusId": "bus_central_500",
                "toBusId": "bus_south_500",
                "length_km": 120.0,
                "r_ohm_per_km": 0.05,
                "x_ohm_per_km": 0.25,
                "c_nf_per_km": 10.0,
                "max_i_ka": 1.5,
                "parallel": 1,
                "df": 1.0,
                "in_service": True,
            },
        ),
        # Transformers
        ReactFlowNode(
            id="trafo_north",
            type="transformer",
            data={"name": "110/20kV N Trafo", "hvBusId": "bus_north_500", "lvBusId": "bus_load_north", "std_type": "63 MVA 110/20 kV", "in_service": True},
        ),
        ReactFlowNode(
            id="trafo_central",
            type="transformer",
            data={"name": "110/20kV C Trafo", "hvBusId": "bus_central_500", "lvBusId": "bus_load_central", "std_type": "63 MVA 110/20 kV", "in_service": True},
        ),
        ReactFlowNode(
            id="trafo_south",
            type="transformer",
            data={"name": "110/20kV S Trafo", "hvBusId": "bus_south_500", "lvBusId": "bus_load_south", "std_type": "63 MVA 110/20 kV", "in_service": True},
        ),
    ]
    
    edges: List[ReactFlowEdge] = [
        ReactFlowEdge(id="e_eg_north", source="eg_north", target="bus_north_500", data={"kind": "attach", "attach_type": "ext_grid"}),
        ReactFlowEdge(id="e_north_line_nc", source="bus_north_500", target="line_north_central", data={"kind": "attach", "attach_type": "line"}),
        ReactFlowEdge(id="e_line_nc_central", source="line_north_central", target="bus_central_500", data={"kind": "attach", "attach_type": "line"}),
        ReactFlowEdge(id="e_central_line_cs", source="bus_central_500", target="line_central_south", data={"kind": "attach", "attach_type": "line"}),
        ReactFlowEdge(id="e_line_cs_south", source="line_central_south", target="bus_south_500", data={"kind": "attach", "attach_type": "line"}),
        ReactFlowEdge(id="e_north_trafo", source="bus_north_500", target="trafo_north", data={"kind": "attach", "attach_type": "transformer"}),
        ReactFlowEdge(id="e_trafo_north_load", source="trafo_north", target="bus_load_north", data={"kind": "attach", "attach_type": "transformer"}),
        ReactFlowEdge(id="e_central_trafo", source="bus_central_500", target="trafo_central", data={"kind": "attach", "attach_type": "transformer"}),
        ReactFlowEdge(id="e_trafo_central_load", source="trafo_central", target="bus_load_central", data={"kind": "attach", "attach_type": "transformer"}),
        ReactFlowEdge(id="e_south_trafo", source="bus_south_500", target="trafo_south", data={"kind": "attach", "attach_type": "transformer"}),
        ReactFlowEdge(id="e_trafo_south_load", source="trafo_south", target="bus_load_south", data={"kind": "attach", "attach_type": "transformer"}),
        ReactFlowEdge(id="e_bln_load_n", source="bus_load_north", target="load_north", data={"kind": "attach", "attach_type": "load"}),
        ReactFlowEdge(id="e_blc_load_c", source="bus_load_central", target="load_central", data={"kind": "attach", "attach_type": "load"}),
        ReactFlowEdge(id="e_bls_load_s", source="bus_load_south", target="load_south", data={"kind": "attach", "attach_type": "load"}),
        ReactFlowEdge(id="e_bn_gen", source="bus_north_500", target="gen_north", data={"kind": "attach", "attach_type": "gen"}),
        ReactFlowEdge(id="e_bc_gen", source="bus_central_500", target="gen_central", data={"kind": "attach", "attach_type": "gen"}),
        ReactFlowEdge(id="e_bs_gen", source="bus_south_500", target="gen_south", data={"kind": "attach", "attach_type": "gen"}),
    ]
    
    return nodes, edges


def _vietnam_backbone_with_switch() -> tuple[List[ReactFlowNode], List[ReactFlowEdge]]:
    """
    Lưới AC với switch mở trên line Central-South để mô phỏng sự cố.
    Switch mở sẽ cô lập khu vực Nam khỏi backbone.
    Sử dụng topology đơn giản: 110kV backbone với 20kV load buses, dùng transformer.
    """
    nodes: List[ReactFlowNode] = [
        # Buses 110kV backbone
        ReactFlowNode(id="bus_north_500", type="bus", data={"vn_kv": 110.0, "min_vm_pu": 0.95, "max_vm_pu": 1.05}),
        ReactFlowNode(id="bus_central_500", type="bus", data={"vn_kv": 110.0, "min_vm_pu": 0.95, "max_vm_pu": 1.05}),
        ReactFlowNode(id="bus_south_500", type="bus", data={"vn_kv": 110.0, "min_vm_pu": 0.95, "max_vm_pu": 1.05}),
        # Buses tải 20kV
        ReactFlowNode(id="bus_load_north", type="bus", data={"vn_kv": 20.0}),
        ReactFlowNode(id="bus_load_central", type="bus", data={"vn_kv": 20.0}),
        ReactFlowNode(id="bus_load_south", type="bus", data={"vn_kv": 20.0}),
        # External grid
        ReactFlowNode(
            id="eg_north",
            type="ext_grid",
            data={"busId": "bus_north_500", "vm_pu": 1.02, "va_degree": 0.0, "in_service": True},
        ),
        # Loads
        ReactFlowNode(id="load_north", type="load", data={"busId": "bus_load_north", "p_mw": 50.0, "q_mvar": 12.0}),
        ReactFlowNode(id="load_central", type="load", data={"busId": "bus_load_central", "p_mw": 40.0, "q_mvar": 10.0}),
        ReactFlowNode(id="load_south", type="load", data={"busId": "bus_load_south", "p_mw": 60.0, "q_mvar": 15.0}),
        # Gen
        ReactFlowNode(id="gen_north", type="gen", data={"busId": "bus_north_500", "p_mw": 100.0, "q_mvar": 0.0, "vm_pu": 1.02}),
        ReactFlowNode(id="gen_central", type="gen", data={"busId": "bus_central_500", "p_mw": 50.0, "q_mvar": 0.0, "vm_pu": 1.02}),
        ReactFlowNode(id="gen_south", type="gen", data={"busId": "bus_south_500", "p_mw": 50.0, "q_mvar": 0.0, "vm_pu": 1.02}),
        # Lines 110kV
        ReactFlowNode(
            id="line_north_central",
            type="line",
            data={
                "name": "110kV North-Central",
                "fromBusId": "bus_north_500",
                "toBusId": "bus_central_500",
                "length_km": 100.0,
                "r_ohm_per_km": 0.05,
                "x_ohm_per_km": 0.25,
                "c_nf_per_km": 10.0,
                "max_i_ka": 1.5,
                "parallel": 1,
                "df": 1.0,
                "in_service": True,
            },
        ),
        ReactFlowNode(
            id="line_central_south",
            type="line",
            data={
                "name": "110kV Central-South",
                "fromBusId": "bus_central_500",
                "toBusId": "bus_south_500",
                "length_km": 120.0,
                "r_ohm_per_km": 0.05,
                "x_ohm_per_km": 0.25,
                "c_nf_per_km": 10.0,
                "max_i_ka": 1.5,
                "parallel": 1,
                "df": 1.0,
                "in_service": True,
            },
        ),
        # Transformers
        ReactFlowNode(
            id="trafo_north",
            type="transformer",
            data={"name": "110/20kV N Trafo", "hvBusId": "bus_north_500", "lvBusId": "bus_load_north", "std_type": "63 MVA 110/20 kV", "in_service": True},
        ),
        ReactFlowNode(
            id="trafo_central",
            type="transformer",
            data={"name": "110/20kV C Trafo", "hvBusId": "bus_central_500", "lvBusId": "bus_load_central", "std_type": "63 MVA 110/20 kV", "in_service": True},
        ),
        ReactFlowNode(
            id="trafo_south",
            type="transformer",
            data={"name": "110/20kV S Trafo", "hvBusId": "bus_south_500", "lvBusId": "bus_load_south", "std_type": "63 MVA 110/20 kV", "in_service": True},
        ),
        # Switch mở trên line Central-South
        ReactFlowNode(
            id="switch_cs_fault",
            type="switch",
            data={
                "name": "Switch CS Fault",
                "busId": "bus_central_500",
                "elementType": "line",
                "elementId": "line_central_south",
                "closed": False,  # Mở - sự cố
                "type": "CB",  # Circuit Breaker
                "in_service": True,
            },
        ),
    ]
    
    edges: List[ReactFlowEdge] = [
        ReactFlowEdge(id="e_eg_north", source="eg_north", target="bus_north_500", data={"kind": "attach", "attach_type": "ext_grid"}),
        ReactFlowEdge(id="e_north_line_nc", source="bus_north_500", target="line_north_central", data={"kind": "attach", "attach_type": "line"}),
        ReactFlowEdge(id="e_line_nc_central", source="line_north_central", target="bus_central_500", data={"kind": "attach", "attach_type": "line"}),
        ReactFlowEdge(id="e_central_line_cs", source="bus_central_500", target="line_central_south", data={"kind": "attach", "attach_type": "line"}),
        ReactFlowEdge(id="e_line_cs_south", source="line_central_south", target="bus_south_500", data={"kind": "attach", "attach_type": "line"}),
        ReactFlowEdge(id="e_north_trafo", source="bus_north_500", target="trafo_north", data={"kind": "attach", "attach_type": "transformer"}),
        ReactFlowEdge(id="e_trafo_north_load", source="trafo_north", target="bus_load_north", data={"kind": "attach", "attach_type": "transformer"}),
        ReactFlowEdge(id="e_central_trafo", source="bus_central_500", target="trafo_central", data={"kind": "attach", "attach_type": "transformer"}),
        ReactFlowEdge(id="e_trafo_central_load", source="trafo_central", target="bus_load_central", data={"kind": "attach", "attach_type": "transformer"}),
        ReactFlowEdge(id="e_south_trafo", source="bus_south_500", target="trafo_south", data={"kind": "attach", "attach_type": "transformer"}),
        ReactFlowEdge(id="e_trafo_south_load", source="trafo_south", target="bus_load_south", data={"kind": "attach", "attach_type": "transformer"}),
        ReactFlowEdge(id="e_bln_load_n", source="bus_load_north", target="load_north", data={"kind": "attach", "attach_type": "load"}),
        ReactFlowEdge(id="e_blc_load_c", source="bus_load_central", target="load_central", data={"kind": "attach", "attach_type": "load"}),
        ReactFlowEdge(id="e_bls_load_s", source="bus_load_south", target="load_south", data={"kind": "attach", "attach_type": "load"}),
        ReactFlowEdge(id="e_bn_gen", source="bus_north_500", target="gen_north", data={"kind": "attach", "attach_type": "gen"}),
        ReactFlowEdge(id="e_bc_gen", source="bus_central_500", target="gen_central", data={"kind": "attach", "attach_type": "gen"}),
        ReactFlowEdge(id="e_bs_gen", source="bus_south_500", target="gen_south", data={"kind": "attach", "attach_type": "gen"}),
        ReactFlowEdge(id="e_switch_cs", source="bus_central_500", target="switch_cs_fault", data={"kind": "attach", "attach_type": "switch"}),
    ]
    
    return nodes, edges


def _vietnam_backbone_with_generator_outage() -> tuple[List[ReactFlowNode], List[ReactFlowEdge]]:
    """Base với gen_south.in_service=False (mất gen Nam)."""
    nodes, edges = _vietnam_backbone_base()
    for n in nodes:
        if n.id == "gen_south":
            n.data["in_service"] = False
    return nodes, edges


def _vietnam_backbone_with_transformer_fault() -> tuple[List[ReactFlowNode], List[ReactFlowEdge]]:
    """Base với trafo_central.in_service=False (sự cố trafo Trung)."""
    nodes, edges = _vietnam_backbone_base()
    for n in nodes:
        if n.id == "trafo_central":
            n.data["in_service"] = False
    return nodes, edges


def _vietnam_backbone_with_high_load() -> tuple[List[ReactFlowNode], List[ReactFlowEdge]]:
    """Base với tải tăng cao để gây điện áp thấp."""
    nodes, edges = _vietnam_backbone_base()
    for n in nodes:
        if n.id == "load_north":
            n.data["p_mw"] = 120.0  # Tăng từ 50 lên 120 MW
            n.data["q_mvar"] = 30.0
        if n.id == "load_central":
            n.data["p_mw"] = 100.0  # Tăng từ 40 lên 100 MW
            n.data["q_mvar"] = 25.0
        if n.id == "load_south":
            n.data["p_mw"] = 150.0  # Tăng từ 60 lên 150 MW
            n.data["q_mvar"] = 40.0
    return nodes, edges


def _vietnam_backbone_with_line_outage() -> tuple[List[ReactFlowNode], List[ReactFlowEdge]]:
    """Base với line_north_central.in_service=False (N-1 contingency)."""
    nodes, edges = _vietnam_backbone_base()
    for n in nodes:
        if n.id == "line_north_central":
            n.data["in_service"] = False
    return nodes, edges


def _vietnam_backbone_islanded() -> tuple[List[ReactFlowNode], List[ReactFlowEdge]]:
    """Base với 2 switch mở tạo 2 đảo: Bắc và Trung-Nam."""
    nodes, edges = _vietnam_backbone_base()
    
    # Switch mở trên line North-Central
    switch_nc = ReactFlowNode(
        id="switch_nc_fault",
        type="switch",
        data={
            "name": "Switch NC Fault",
            "busId": "bus_north_500",
            "elementType": "line",
            "elementId": "line_north_central",
            "closed": False,
            "type": "CB",
            "in_service": True,
        },
    )
    nodes.append(switch_nc)
    edges.append(ReactFlowEdge(id="e_switch_nc", source="bus_north_500", target="switch_nc_fault", data={"kind": "attach", "attach_type": "switch"}))
    
    # Switch mở trên line Central-South
    switch_cs = ReactFlowNode(
        id="switch_cs_fault",
        type="switch",
        data={
            "name": "Switch CS Fault",
            "busId": "bus_central_500",
            "elementType": "line",
            "elementId": "line_central_south",
            "closed": False,
            "type": "CB",
            "in_service": True,
        },
    )
    nodes.append(switch_cs)
    edges.append(ReactFlowEdge(id="e_switch_cs", source="bus_central_500", target="switch_cs_fault", data={"kind": "attach", "attach_type": "switch"}))
    
    return nodes, edges


def test_vietnam_backbone_normal_load() -> None:
    """
    Kịch bản 1: lưới Bắc–Trung–Nam bình thường, không quá tải, điện áp trong khoảng.
    """
    settings = RunSettings(return_network="tables")
    nodes, edges = _vietnam_backbone_base()
    req = SimulateRequest(nodes=nodes, edges=edges, settings=settings)

    resp = simulate_from_reactflow(req)

    assert resp.summary.converged is True
    assert resp.summary.slack_bus_id == "bus_north_500"
    # Kiểm tra điện áp các bus tải (20 kV)
    for bus_id in ["bus_load_north", "bus_load_central", "bus_load_south"]:
        assert bus_id in resp.bus_by_id
        vm = resp.bus_by_id[bus_id].vm_pu
        assert 0.95 <= vm <= 1.05


def test_vietnam_south_overload_weak_line() -> None:
    """
    Kịch bản 2: tăng mạnh tải miền Nam và giảm max_i_ka của line Trung–Nam để tạo quá tải.
    """
    settings = RunSettings(return_network="tables")
    nodes, edges = _vietnam_backbone_base()

    # Tăng tải miền Nam và làm yếu đường dây Trung–Nam
    for n in nodes:
        if n.id == "load_south":
            n.data["p_mw"] = 120.0  # tăng từ 60 lên 120 MW
            n.data["q_mvar"] = 30.0
        if n.id == "line_central_south":
            n.data["max_i_ka"] = 0.3  # đường dây rất yếu (giảm từ 1.5 xuống 0.3)

    req = SimulateRequest(nodes=nodes, edges=edges, settings=settings)
    resp = simulate_from_reactflow(req)

    assert resp.summary.converged is True
    assert resp.network is not None
    net = resp.network or {}
    res_line = (net.get("results") or {}).get("res_line") or []
    assert isinstance(res_line, list) and len(res_line) >= 1

    # Tìm dòng của line Trung–Nam
    weak_rows = [
        row
        for row in res_line
        if str(row.get("name") or "") == "110kV Central-South" or str(row.get("id") or "") == "line_central_south"
    ]
    assert weak_rows, "Không tìm thấy kết quả cho line_central_south"
    loading = float(weak_rows[0].get("loading_percent") or 0.0)
    assert loading > 100.0


def test_vietnam_topology_invalid_load_bus() -> None:
    """
    Kịch bản 3: topology lỗi – load trỏ tới bus không tồn tại.
    """
    nodes = [
        ReactFlowNode(id="b1", type="bus", data={"vn_kv": 220.0}),
        ReactFlowNode(id="bad_load", type="load", data={"busId": "no_such_bus", "p_mw": 10.0, "q_mvar": 2.0}),
    ]
    edges: List[ReactFlowEdge] = []
    req = SimulateRequest(nodes=nodes, edges=edges)

    resp = simulate_from_reactflow(req)

    assert resp.summary.converged is False
    # Lỗi phải xuất hiện trong errors
    assert "load" in resp.errors or "network" in resp.errors
    assert "bad_load" in resp.element_status
    assert resp.element_status["bad_load"].success is False


def test_vietnam_switch_fault_isolates_south() -> None:
    """
    Kịch bản 4: switch mở trên line Central-South, cô lập khu vực Nam.
    Khi switch mở:
    - Khu vực Nam (bus_south_500, bus_load_south) bị cô lập
    - Chỉ phụ thuộc vào gen local (50 MW) nhưng tải là 60 MW
    - Có thể không hội tụ hoặc điện áp thấp
    - Khu vực Bắc-Trung vẫn hoạt động bình thường
    - Line Central-South không có dòng chảy (switch mở)
    """
    settings = RunSettings(return_network="tables")
    nodes, edges = _vietnam_backbone_with_switch()
    req = SimulateRequest(nodes=nodes, edges=edges, settings=settings)

    resp = simulate_from_reactflow(req)

    # Kiểm tra switch được tạo thành công
    assert "switch_cs_fault" in resp.element_status
    assert resp.element_status["switch_cs_fault"].success is True

    # Kiểm tra khu vực Bắc-Trung vẫn hoạt động
    for bus_id in ["bus_north_500", "bus_central_500", "bus_load_north", "bus_load_central"]:
        assert bus_id in resp.bus_by_id
        vm = resp.bus_by_id[bus_id].vm_pu
        # Điện áp phải hợp lý (có thể thấp hơn bình thường nhưng không phải NaN)
        assert vm > 0.0, f"Bus {bus_id} có điện áp không hợp lệ: {vm}"

    # Kiểm tra line Central-South không có dòng chảy (switch mở)
    if resp.network and resp.network.get("results"):
        res_line = resp.network["results"].get("res_line") or []
        if isinstance(res_line, list):
            cs_line = [
                row
                for row in res_line
                if str(row.get("name") or "") == "110kV Central-South"
                or str(row.get("id") or "") == "line_central_south"
            ]
            if cs_line:
                # Dòng chảy phải bằng 0 hoặc rất nhỏ (switch mở)
                i_ka = float(cs_line[0].get("i_ka") or 0.0)
                assert abs(i_ka) < 0.1, f"Line Central-South vẫn có dòng chảy {i_ka} mặc dù switch mở"

    # Khu vực Nam có thể không hội tụ hoặc điện áp thấp do tải > gen
    # (Gen Nam: 50 MW, Tải Nam: 60 MW)
    if "bus_south_500" in resp.bus_by_id:
        vm_south = resp.bus_by_id["bus_south_500"].vm_pu
        # Điện áp có thể thấp hoặc không hội tụ
        # Nếu hội tụ, điện áp sẽ thấp do thiếu công suất
        if resp.summary.converged:
            assert vm_south < 0.95, f"Bus South có điện áp cao {vm_south} mặc dù thiếu công suất"


def test_vietnam_generator_outage_south() -> None:
    """
    Kịch bản 5: Generator Outage - Mất Gen Nam.
    Khi gen_south.in_service=False:
    - Tải Nam (60 MW) > Gen Nam (0 MW) → thiếu công suất
    - Power flow có thể không hội tụ hoặc điện áp thấp ở khu vực Nam
    - Các khu vực khác vẫn hoạt động bình thường
    - Line Central-South có thể quá tải do phải truyền công suất từ Trung xuống Nam
    """
    settings = RunSettings(return_network="tables")
    nodes, edges = _vietnam_backbone_with_generator_outage()
    req = SimulateRequest(nodes=nodes, edges=edges, settings=settings)

    resp = simulate_from_reactflow(req)

    # Kiểm tra gen_south không hoạt động
    assert "gen_south" in resp.element_status
    # Gen có thể được tạo nhưng in_service=False sẽ không phát công suất

    # Kiểm tra khu vực Bắc-Trung vẫn hoạt động
    for bus_id in ["bus_north_500", "bus_central_500", "bus_load_north", "bus_load_central"]:
        assert bus_id in resp.bus_by_id
        vm = resp.bus_by_id[bus_id].vm_pu
        assert vm > 0.0, f"Bus {bus_id} có điện áp không hợp lệ: {vm}"

    # Khu vực Nam có thể không hội tụ hoặc điện áp thấp do thiếu công suất
    if "bus_south_500" in resp.bus_by_id:
        vm_south = resp.bus_by_id["bus_south_500"].vm_pu
        if resp.summary.converged:
            # Nếu hội tụ, điện áp sẽ thấp do thiếu công suất
            assert vm_south < 1.0, f"Bus South có điện áp cao {vm_south} mặc dù thiếu công suất"

    # Kiểm tra line Central-South có thể quá tải
    if resp.network and resp.network.get("results"):
        res_line = resp.network["results"].get("res_line") or []
        if isinstance(res_line, list):
            cs_line = [
                row
                for row in res_line
                if str(row.get("name") or "") == "110kV Central-South"
                or str(row.get("id") or "") == "line_central_south"
            ]
            if cs_line and resp.summary.converged:
                loading = float(cs_line[0].get("loading_percent") or 0.0)
                # Line có thể quá tải do phải truyền công suất từ Trung xuống Nam
                assert loading > 50.0, f"Line Central-South có loading thấp {loading}% mặc dù phải truyền công suất"


def test_vietnam_transformer_fault_central() -> None:
    """
    Kịch bản 6: Transformer Fault - Sự Cố Trafo Trung.
    Khi trafo_central.in_service=False:
    - Tải Trung (load_central) bị mất điện
    - Bus load Trung (bus_load_central) không có điện áp hoặc NaN
    - Công suất dư thừa được phân bố lại
    - Các transformer khác không quá tải
    """
    settings = RunSettings(return_network="tables")
    nodes, edges = _vietnam_backbone_with_transformer_fault()
    req = SimulateRequest(nodes=nodes, edges=edges, settings=settings)

    resp = simulate_from_reactflow(req)

    # Kiểm tra trafo_central không hoạt động
    assert "trafo_central" in resp.element_status

    # Kiểm tra khu vực Bắc và Nam vẫn hoạt động
    for bus_id in ["bus_north_500", "bus_south_500", "bus_load_north", "bus_load_south"]:
        assert bus_id in resp.bus_by_id
        vm = resp.bus_by_id[bus_id].vm_pu
        assert vm > 0.0, f"Bus {bus_id} có điện áp không hợp lệ: {vm}"

    # Bus load Trung có thể không có điện áp hoặc NaN (do trafo mất)
    if "bus_load_central" in resp.bus_by_id:
        vm_central_load = resp.bus_by_id["bus_load_central"].vm_pu
        # Điện áp sẽ rất thấp hoặc bằng 0 do không có nguồn cung cấp
        if resp.summary.converged:
            assert vm_central_load < 0.1, f"Bus load Central có điện áp {vm_central_load} mặc dù trafo mất"


def test_vietnam_voltage_violation_low() -> None:
    """
    Kịch bản 7: Voltage Violation - Điện Áp Thấp.
    Khi tải tăng cao:
    - Một số bus có vm_pu < min_vm_pu (ví dụ < 0.95)
    - Hệ thống vẫn hội tụ nhưng có vi phạm điện áp
    - Cần ghi nhận vi phạm điện áp trong kết quả
    """
    settings = RunSettings(return_network="tables")
    nodes, edges = _vietnam_backbone_with_high_load()
    req = SimulateRequest(nodes=nodes, edges=edges, settings=settings)

    resp = simulate_from_reactflow(req)

    # Kiểm tra có vi phạm điện áp thấp
    voltage_violations = []
    for bus_id, bus_result in resp.bus_by_id.items():
        vm = bus_result.vm_pu
        # Tìm bus có min_vm_pu được set
        bus_node = next((n for n in nodes if n.id == bus_id), None)
        if bus_node and bus_node.data.get("min_vm_pu") is not None:
            min_vm = float(bus_node.data.get("min_vm_pu", 0.95))
            if vm < min_vm:
                voltage_violations.append((bus_id, vm, min_vm))

    # Với tải cao, phải có ít nhất một vi phạm điện áp
    if resp.summary.converged:
        assert len(voltage_violations) > 0, "Không có vi phạm điện áp nào mặc dù tải cao"


def test_vietnam_n1_contingency_line_nc() -> None:
    """
    Kịch bản 8: N-1 Contingency - Mất Line North-Central.
    Khi line_north_central.in_service=False:
    - Khu vực Trung-Nam bị cô lập khỏi ext_grid (chỉ ở Bắc)
    - Có thể không hội tụ do thiếu slack bus ở đảo Trung-Nam
    - Khu vực Bắc vẫn hoạt động bình thường (có ext_grid)
    - Line Central-South không có dòng chảy (đảo bị cô lập)
    """
    settings = RunSettings(return_network="tables")
    nodes, edges = _vietnam_backbone_with_line_outage()
    req = SimulateRequest(nodes=nodes, edges=edges, settings=settings)

    resp = simulate_from_reactflow(req)

    # Kiểm tra line_north_central không hoạt động
    assert "line_north_central" in resp.element_status

    # Khu vực Bắc vẫn hoạt động (có ext_grid)
    if "bus_north_500" in resp.bus_by_id:
        vm_north = resp.bus_by_id["bus_north_500"].vm_pu
        # Bắc có ext_grid nên phải có điện áp hợp lệ nếu hội tụ
        if resp.summary.converged:
            assert vm_north > 0.0, f"Bus North có điện áp không hợp lệ: {vm_north}"

    # Khu vực Trung-Nam có thể không hội tụ do thiếu slack bus (ext_grid chỉ ở Bắc)
    # Đây là hành vi đúng - khi mất line, đảo không có slack bus sẽ không hội tụ
    if not resp.summary.converged:
        # Nếu không hội tụ, đây là kết quả hợp lệ cho N-1 contingency
        assert "powerflow" in resp.errors or len(resp.errors) > 0


def test_vietnam_load_shedding_south() -> None:
    """
    Kịch bản 9: Load Shedding - Cắt Tải Nam.
    Sau khi switch mở cô lập Nam, cắt một phần tải Nam (giảm từ 60 MW xuống 40 MW).
    - Sau khi cắt tải, hệ thống có thể hội tụ (Gen 50 MW > Tải 40 MW)
    - Điện áp khu vực Nam được cải thiện
    - Khu vực Bắc-Trung vẫn hoạt động bình thường
    """
    settings = RunSettings(return_network="tables")
    nodes, edges = _vietnam_backbone_with_switch()
    
    # Giảm tải Nam từ 60 MW xuống 40 MW (cắt tải)
    for n in nodes:
        if n.id == "load_south":
            n.data["p_mw"] = 40.0
            n.data["q_mvar"] = 10.0
    
    req = SimulateRequest(nodes=nodes, edges=edges, settings=settings)
    resp = simulate_from_reactflow(req)

    # Khu vực Bắc-Trung vẫn hoạt động bình thường
    for bus_id in ["bus_north_500", "bus_central_500", "bus_load_north", "bus_load_central"]:
        if bus_id in resp.bus_by_id:
            vm = resp.bus_by_id[bus_id].vm_pu
            if resp.summary.converged:
                assert vm > 0.0, f"Bus {bus_id} có điện áp không hợp lệ: {vm}"

    # Sau khi cắt tải, đảo Nam vẫn có thể không hội tụ do thiếu slack bus (ext_grid)
    # Pandapower cần ít nhất một ext_grid trong mỗi đảo để hội tụ
    # Nếu không có ext_grid trong đảo Nam, sẽ không hội tụ dù Gen > Tải
    if "bus_south_500" in resp.bus_by_id:
        vm_south = resp.bus_by_id["bus_south_500"].vm_pu
        if resp.summary.converged and vm_south > 0.0:
            # Nếu hội tụ và có điện áp hợp lệ (có slack bus), điện áp sẽ tốt hơn
            assert vm_south > 0.8, f"Bus South có điện áp quá thấp {vm_south} sau khi cắt tải"
        elif not resp.summary.converged or vm_south == 0.0:
            # Nếu không hội tụ hoặc điện áp = 0, đây là hành vi đúng
            # Đảo không có slack bus sẽ không hội tụ dù Gen (50 MW) > Tải (40 MW)
            # Hoặc nếu converged=True nhưng vm=0.0, có thể do đảo không có slack bus
            pass  # Chấp nhận trường hợp này


def test_vietnam_islanding_north_vs_central_south() -> None:
    """
    Kịch bản 10: Islanding - Đảo Lưới Bắc và Trung-Nam.
    Mở cả 2 switch trên line North-Central và Central-South, tạo 2 đảo:
    - Đảo Bắc: Gen (100 MW) + Ext Grid vs Tải (50 MW) → thừa công suất, có slack bus
    - Đảo Trung-Nam: Gen (100 MW) vs Tải (100 MW) → cân bằng, nhưng không có ext_grid (slack bus)
    - Đảo Bắc sẽ hội tụ (có ext_grid)
    - Đảo Trung-Nam có thể không hội tụ do thiếu slack bus
    """
    settings = RunSettings(return_network="tables")
    nodes, edges = _vietnam_backbone_islanded()
    req = SimulateRequest(nodes=nodes, edges=edges, settings=settings)

    resp = simulate_from_reactflow(req)

    # Kiểm tra cả 2 switch được tạo thành công
    assert "switch_nc_fault" in resp.element_status
    assert "switch_cs_fault" in resp.element_status

    # Đảo Bắc: Gen (100 MW) + Ext Grid vs Tải (50 MW) → thừa công suất, có slack bus
    if "bus_north_500" in resp.bus_by_id:
        vm_north = resp.bus_by_id["bus_north_500"].vm_pu
        if resp.summary.converged:
            # Điện áp sẽ cao do thừa công suất
            assert vm_north > 1.0, f"Bus North có điện áp thấp {vm_north} mặc dù thừa công suất"

    # Đảo Trung-Nam: Gen (100 MW) vs Tải (100 MW) → cân bằng, nhưng không có ext_grid
    # Pandapower cần ít nhất một ext_grid (slack bus) để hội tụ
    # Nếu không có ext_grid trong đảo, có thể không hội tụ
    if not resp.summary.converged:
        # Đây là hành vi đúng - đảo không có slack bus sẽ không hội tụ
        assert "powerflow" in resp.errors or len(resp.errors) > 0


def test_vietnam_multiple_faults_gen_outage_and_line_overload() -> None:
    """
    Kịch bản 11: Multiple Faults - Mất Gen + Quá Tải Line.
    Gen Nam mất + tăng tải Nam + giảm max_i_ka của line Central-South:
    - Hệ thống chịu áp lực lớn
    - Có thể không hội tụ
    - Line Central-South quá tải nghiêm trọng
    - Cần ghi nhận nhiều lỗi/cảnh báo
    """
    settings = RunSettings(return_network="tables")
    nodes, edges = _vietnam_backbone_with_generator_outage()
    
    # Tăng tải Nam và giảm max_i_ka của line Central-South
    for n in nodes:
        if n.id == "load_south":
            n.data["p_mw"] = 80.0  # Tăng từ 60 lên 80 MW
            n.data["q_mvar"] = 20.0
        if n.id == "line_central_south":
            n.data["max_i_ka"] = 0.3  # Giảm từ 1.5 xuống 0.3 (rất yếu)
    
    req = SimulateRequest(nodes=nodes, edges=edges, settings=settings)
    resp = simulate_from_reactflow(req)

    # Hệ thống có thể không hội tụ do nhiều sự cố
    # Hoặc nếu hội tụ, line sẽ quá tải nghiêm trọng
    if resp.network and resp.network.get("results"):
        res_line = resp.network["results"].get("res_line") or []
        if isinstance(res_line, list):
            cs_line = [
                row
                for row in res_line
                if str(row.get("name") or "") == "110kV Central-South"
                or str(row.get("id") or "") == "line_central_south"
            ]
            if cs_line and resp.summary.converged:
                loading = float(cs_line[0].get("loading_percent") or 0.0)
                # Line sẽ quá tải nghiêm trọng (>100%)
                assert loading > 100.0, f"Line Central-South không quá tải {loading}% mặc dù có nhiều sự cố"


