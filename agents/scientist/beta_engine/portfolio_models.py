from __future__ import annotations

from pathlib import Path

import pandas as pd

from weighting_logic import weight_within_group


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_portfolio_definitions() -> pd.DataFrame:
    path = _repo_root() / "inputs" / "portfolio_definitions.csv"
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


def derive_node_weights(portfolio_df: pd.DataFrame) -> tuple[dict[str, float], str]:
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

    node_ids = [str(x) for x in portfolio_df["node_id"].tolist()]
    w = weight_within_group(node_ids)
    out = {node_id: float(w.get(str(i), 0.0)) for i, node_id in enumerate(node_ids)}
    return out, "rule_based_stub"
