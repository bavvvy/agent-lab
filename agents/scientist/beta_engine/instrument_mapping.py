from __future__ import annotations

from pathlib import Path

import pandas as pd


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_instrument_mapping() -> pd.DataFrame:
    path = _repo_root() / "inputs" / "instrument_mapping.csv"
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
