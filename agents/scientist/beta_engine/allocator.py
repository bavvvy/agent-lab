from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hierarchy_loader import load_hierarchy
from weighting_logic import weight_within_group
from io_guard import assert_not_forbidden_identity_root_file, assert_root_write_allowed


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _inputs_dir() -> Path:
    return _repo_root() / "inputs"


def _flatten_node_ids(hierarchy: dict) -> set[str]:
    node_ids: set[str] = set()
    for l1_node in hierarchy.values():
        for l2_node in l1_node.values():
            for l3_node in l2_node.values():
                for l4_node in l3_node.values():
                    for node_id in l4_node.keys():
                        node_ids.add(str(node_id))
    return node_ids


def _load_instrument_mapping() -> pd.DataFrame:
    path = _inputs_dir() / "instrument_mapping.csv"
    if not path.exists():
        raise FileNotFoundError(f"Instrument mapping not found: {path}")

    df = pd.read_csv(path)
    required = ["node_id", "instrument_id", "instrument_type", "data_source"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Malformed instrument mapping: missing required columns: {missing}")

    if df.empty:
        raise ValueError("Malformed instrument mapping: file contains no rows")

    for c in required:
        if df[c].isna().any() or (df[c].astype(str).str.strip() == "").any():
            raise ValueError(f"Malformed instrument mapping: column '{c}' contains blank values")

    return df.copy()


def _load_portfolio_definitions() -> pd.DataFrame:
    path = _inputs_dir() / "portfolio_definitions.csv"
    if not path.exists():
        raise FileNotFoundError(f"Portfolio definitions not found: {path}")

    df = pd.read_csv(path)
    required = ["portfolio_name", "node_id", "weight", "weight_type"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Malformed portfolio definitions: missing required columns: {missing}")

    if df.empty:
        raise ValueError("Malformed portfolio definitions: file contains no rows")

    for c in ["portfolio_name", "node_id", "weight_type"]:
        if df[c].isna().any() or (df[c].astype(str).str.strip() == "").any():
            raise ValueError(f"Malformed portfolio definitions: column '{c}' contains blank values")

    bad_weight_type = sorted(set(df[~df["weight_type"].isin(["static", "rule_based"])]["weight_type"].astype(str)))
    if bad_weight_type:
        raise ValueError(f"Invalid weight_type values: {bad_weight_type}")

    dupes = df[df.duplicated(subset=["portfolio_name", "node_id"], keep=False)]
    if not dupes.empty:
        pairs = sorted(set(zip(dupes["portfolio_name"].astype(str), dupes["node_id"].astype(str))))
        raise ValueError(f"Duplicate (portfolio_name, node_id) entries found: {pairs}")

    return df.copy()


def _derive_node_weights(portfolio_df: pd.DataFrame) -> tuple[dict[str, float], str]:
    weight_type_values = set(portfolio_df["weight_type"].astype(str))
    if len(weight_type_values) != 1:
        raise ValueError("Portfolio contains mixed weight_type values; expected one mode per portfolio")

    weight_type = next(iter(weight_type_values))

    if weight_type == "static":
        numeric = pd.to_numeric(portfolio_df["weight"], errors="coerce")
        if numeric.isna().any():
            raise ValueError("Static portfolio requires numeric weight for every row")

        total = float(numeric.sum())
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"Static portfolio weights must sum to 1.0 (got {total})")

        out = {str(node_id): float(w) for node_id, w in zip(portfolio_df["node_id"], numeric)}
        return out, "static"

    # rule_based stub: equal weights across selected node_ids
    node_ids = [str(x) for x in portfolio_df["node_id"].tolist()]
    w = weight_within_group(node_ids)
    out = {node_id: float(w.get(str(i), 0.0)) for i, node_id in enumerate(node_ids)}
    return out, "rule_based_stub"


def run_allocator(portfolio_name: str) -> Path:
    hierarchy = load_hierarchy()
    valid_node_ids = _flatten_node_ids(hierarchy)

    mapping_df = _load_instrument_mapping()
    defs_df = _load_portfolio_definitions()

    defs = defs_df[defs_df["portfolio_name"] == portfolio_name].copy()
    if defs.empty:
        raise ValueError(f"Portfolio definition not found: {portfolio_name}")

    unknown_nodes = sorted(set(defs[~defs["node_id"].isin(valid_node_ids)]["node_id"].astype(str)))
    if unknown_nodes:
        raise ValueError(f"Portfolio references unknown node_id values: {unknown_nodes}")

    node_weights, allocation_mode = _derive_node_weights(defs)

    mapping_for_nodes = mapping_df[mapping_df["node_id"].isin(node_weights.keys())].copy()
    if mapping_for_nodes.empty:
        raise ValueError("No instrument mappings found for selected node_ids")

    rows: list[dict[str, float | str]] = []
    for node_id, node_weight in node_weights.items():
        node_map = mapping_for_nodes[mapping_for_nodes["node_id"] == node_id]
        if node_map.empty:
            raise ValueError(f"No instrument mapping found for node_id: {node_id}")

        per_instrument = float(node_weight) / len(node_map)
        for _, r in node_map.iterrows():
            rows.append(
                {
                    "portfolio_name": portfolio_name,
                    "node_id": str(r["node_id"]),
                    "instrument_id": str(r["instrument_id"]),
                    "instrument_type": str(r["instrument_type"]),
                    "target_weight": per_instrument,
                    "allocation_mode": allocation_mode,
                }
            )

    out_dir = _repo_root() / "outputs" / "runtime"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "portfolio_targets.csv"

    df = pd.DataFrame(rows)
    df = df.groupby(
        ["portfolio_name", "node_id", "instrument_id", "instrument_type", "allocation_mode"],
        as_index=False,
    )["target_weight"].sum()

    assert_root_write_allowed(out_path)
    assert_not_forbidden_identity_root_file(out_path)
    df.to_csv(out_path, index=False)
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio-name", required=True)
    args = parser.parse_args()

    path = run_allocator(portfolio_name=args.portfolio_name)
    print(path)
