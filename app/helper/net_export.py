from __future__ import annotations

import math
from typing import Any, Dict, Literal, Optional


def export_network(net: Any, mode: Literal["none", "summary", "tables"] = "none") -> Optional[Dict[str, Any]]:
    """
    Export pandapower network theo mức độ.
    - none: không trả
    - summary: meta + counts
    - tables: thêm element tables + results (nếu có)
    """
    if mode == "none":
        return None

    payload: Dict[str, Any] = {"meta": {"counts": {}}}
    # Đếm sơ bộ các bảng phổ biến nếu tồn tại
    for tbl in (
        "bus",
        "line",
        "load",
        "ext_grid",
        "gen",
        "sgen",
        "trafo",
        "trafo3w",
        "switch",
        "shunt",
        "motor",
        "storage",
    ):
        if hasattr(net, tbl):
            try:
                payload["meta"]["counts"][tbl] = int(len(getattr(net, tbl)))
            except Exception:  # noqa: BLE001
                pass

    if mode == "summary":
        return payload

    # mode == "tables"
    # Trả về dạng list các bản ghi (records) để frontend dễ render bảng
    tables: Dict[str, Any] = {}
    results: Dict[str, Any] = {}
    for tbl in (
        "bus",
        "line",
        "load",
        "ext_grid",
        "gen",
        "sgen",
        "trafo",
        "trafo3w",
        "switch",
        "shunt",
        "motor",
        "storage",
    ):
        if hasattr(net, tbl):
            try:
                df = getattr(net, tbl)
                # Reset index để có cột index/id rõ ràng cho frontend
                # Replace NaN với None để JSON serialize được (NaN không hợp lệ trong JSON)
                records = df.reset_index().replace({float("nan"): None}).to_dict(orient="records")
                tables[tbl] = _clean_nan_records(records)
            except Exception:  # noqa: BLE001
                pass

    for res_tbl in ("res_bus", "res_line", "res_load", "res_gen", "res_sgen", "res_trafo", "res_trafo3w"):
        if hasattr(net, res_tbl):
            try:
                df = getattr(net, res_tbl)
                # Replace NaN với None để JSON serialize được
                records = df.reset_index().replace({float("nan"): None}).to_dict(orient="records")
                results[res_tbl] = _clean_nan_records(records)
            except Exception:  # noqa: BLE001
                pass

    payload["tables"] = tables
    payload["results"] = results
    return payload


def _clean_nan_records(records: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """
    Clean NaN values trong list các dict records để JSON serialize được.
    Replace NaN, inf, -inf với None (sẽ thành null trong JSON).
    """
    cleaned = []
    for rec in records:
        cleaned_rec: Dict[str, Any] = {}
        for k, v in rec.items():
            if isinstance(v, float):
                if math.isnan(v) or math.isinf(v):
                    cleaned_rec[k] = None
                else:
                    cleaned_rec[k] = v
            else:
                cleaned_rec[k] = v
        cleaned.append(cleaned_rec)
    return cleaned


