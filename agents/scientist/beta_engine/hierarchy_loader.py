from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = [
    "level1_asset_class",
    "level2_sub_asset_class",
    "level3_strategy_style",
    "level4_instrument",
    "instrument_type",
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

    if df["level1_asset_class"].isna().any() or (df["level1_asset_class"].astype(str).str.strip() == "").any():
        raise ValueError("Malformed hierarchy CSV: column 'level1_asset_class' contains blank values")

    if df["level4_instrument"].isna().any() or (df["level4_instrument"].astype(str).str.strip() == "").any():
        raise ValueError("Malformed hierarchy CSV: column 'level4_instrument' contains blank values")

    hierarchy: dict[str, Any] = {}

    for _, row in df.iterrows():
        l1 = str(row["level1_asset_class"]).strip()
        l2 = str(row["level2_sub_asset_class"]).strip()
        l3 = str(row["level3_strategy_style"]).strip()
        l4 = str(row["level4_instrument"]).strip()
        instrument_type = str(row["instrument_type"]).strip()

        hierarchy.setdefault(l1, {})
        hierarchy[l1].setdefault(l2, {})
        hierarchy[l1][l2].setdefault(l3, {})
        hierarchy[l1][l2][l3].setdefault(l4, [])
        hierarchy[l1][l2][l3][l4].append({"instrument_type": instrument_type})

    return hierarchy
