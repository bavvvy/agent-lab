from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = [
    "level1",
    "level2",
    "level3",
    "level4",
    "node_id",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_hierarchy(csv_path: Path | None = None) -> dict[str, Any]:
    path = csv_path or (_repo_root() / "inputs" / "asset_class_hierarchy.csv")
    if not path.exists():
        raise FileNotFoundError(f"Hierarchy file not found: {path}")

    df = pd.read_csv(path)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Malformed hierarchy CSV: missing required columns: {missing}")

    if df.empty:
        raise ValueError("Malformed hierarchy CSV: file contains no rows")

    for col in REQUIRED_COLUMNS:
        if df[col].isna().any() or (df[col].astype(str).str.strip() == "").any():
            raise ValueError(f"Malformed hierarchy CSV: column '{col}' contains blank values")

    if df["node_id"].duplicated().any():
        duplicates = sorted(df.loc[df["node_id"].duplicated(), "node_id"].astype(str).unique().tolist())
        raise ValueError(f"Malformed hierarchy CSV: node_id must be unique; duplicates: {duplicates}")

    hierarchy: dict[str, Any] = {}

    for _, row in df.iterrows():
        l1 = str(row["level1"]).strip()
        l2 = str(row["level2"]).strip()
        l3 = str(row["level3"]).strip()
        l4 = str(row["level4"]).strip()
        node_id = str(row["node_id"]).strip()

        hierarchy.setdefault(l1, {})
        hierarchy[l1].setdefault(l2, {})
        hierarchy[l1][l2].setdefault(l3, {})
        hierarchy[l1][l2][l3].setdefault(l4, {})
        hierarchy[l1][l2][l3][l4][node_id] = {"node_id": node_id}

    return hierarchy
