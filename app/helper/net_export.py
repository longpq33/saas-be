from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

import math


def _sanitize_json_floats(obj: Any) -> Any:
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, list):
        return [_sanitize_json_floats(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _sanitize_json_floats(v) for k, v in obj.items()}
    return obj


def _df_to_records(df: Any) -> list[dict[str, Any]]:
    # pandapower uses pandas DataFrames; keep this helper loose-typed
    try:
        records = df.reset_index().to_dict("records")
    except Exception:  # noqa: BLE001
        try:
            records = df.to_dict("records")
        except Exception:  # noqa: BLE001
            return []
    return _sanitize_json_floats(records)


def export_network(net: Any, mode: str = "none") -> Optional[Dict[str, Any]]:
    if mode == "none":
        return None

    meta: Dict[str, Any] = {
        "converged": bool(getattr(net, "converged", False)),
        "sn_mva": getattr(net, "sn_mva", None),
        "f_hz": getattr(net, "f_hz", None),
    }

    if mode == "summary":
        counts: Dict[str, int] = {}
        for name in (
            "bus",
            "line",
            "trafo",
            "trafo3w",
            "load",
            "gen",
            "sgen",
            "ext_grid",
            "switch",
            "shunt",
            "motor",
            "storage",
        ):
            try:
                tbl = getattr(net, name)
                counts[name] = int(len(tbl))
            except Exception:  # noqa: BLE001
                counts[name] = 0

        meta["counts"] = counts
        return {"meta": _sanitize_json_floats(meta)}

    # mode == "tables"
    tables: Dict[str, Any] = {}
    res_tables: Dict[str, Any] = {}

    element_table_names: Iterable[str] = (
        "bus",
        "line",
        "trafo",
        "trafo3w",
        "load",
        "gen",
        "sgen",
        "ext_grid",
        "switch",
        "shunt",
        "motor",
        "storage",
    )
    result_table_names: Iterable[str] = (
        "res_bus",
        "res_line",
        "res_trafo",
        "res_trafo3w",
        "res_load",
        "res_gen",
        "res_sgen",
        "res_ext_grid",
        "res_switch",
        "res_shunt",
        "res_motor",
        "res_storage",
    )

    for name in element_table_names:
        try:
            df = getattr(net, name)
            tables[name] = _df_to_records(df)
        except Exception:  # noqa: BLE001
            pass

    for name in result_table_names:
        try:
            df = getattr(net, name)
            # res_* might not exist if not converged or element not present
            if df is None:
                continue
            res_tables[name] = _df_to_records(df)
        except Exception:  # noqa: BLE001
            pass

    meta["counts"] = {k: len(v) for k, v in tables.items() if isinstance(v, list)}

    return {
        "meta": _sanitize_json_floats(meta),
        "tables": tables,
        "results": res_tables,
    }

