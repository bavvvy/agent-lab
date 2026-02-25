from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hierarchy_loader import load_hierarchy
from instrument_mapping import load_instrument_mapping
from portfolio_models import derive_node_weights, load_portfolio_definitions
from io_guard import assert_not_forbidden_identity_root_file, assert_root_write_allowed


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _mode_config_path(mode: str) -> Path:
    """Return systems-level config path for the selected mode.

    Research beta knobs are system-scoped under `systems/<mode>/config.yaml`.
    Capital remains deterministic unless explicitly configured.
    """
    return _repo_root() / "systems" / mode / "config.yaml"


def _load_mode_beta_engine_config(mode: str) -> dict:
    """Load optional beta_engine config for allocator method selection.

    If mode config or `beta_engine` section is absent, return empty mapping
    so existing deterministic defaults are preserved.
    """
    p = _mode_config_path(mode)
    if not p.exists():
        return {}
    payload = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    beta_cfg = payload.get("beta_engine", {})
    return beta_cfg if isinstance(beta_cfg, dict) else {}


def _dispatch_weighting_method(defs: pd.DataFrame, beta_cfg: dict) -> tuple[dict[str, float], str]:
    """Dispatch weighting method from config while preserving existing math.

    Current phase only scaffolds selection; all methods route to existing
    `derive_node_weights` implementation (no allocation math changes).
    """
    method = str(beta_cfg.get("weighting_method", "default")).strip().lower()

    if method in {"default", "equal_risk", "risk_parity", "hierarchical_risk_parity"}:
        return derive_node_weights(defs)

    # Unknown methods fall back to existing deterministic behavior.
    return derive_node_weights(defs)


def _flatten_node_ids(hierarchy: dict) -> set[str]:
    node_ids: set[str] = set()
    for l1_node in hierarchy.values():
        for l2_node in l1_node.values():
            for l3_node in l2_node.values():
                for l4_node in l3_node.values():
                    for node_id in l4_node.keys():
                        node_ids.add(str(node_id))
    return node_ids


def run_allocator(portfolio_name: str, mode: str = "capital") -> Path:
    """Build instrument targets for a portfolio with mode-scoped config selection.

    Research beta knobs are read from `systems/<mode>/config.yaml`.
    Capital behavior stays deterministic unless a `beta_engine` section is
    explicitly configured.
    """
    hierarchy = load_hierarchy()
    valid_node_ids = _flatten_node_ids(hierarchy)

    mapping_df = load_instrument_mapping()
    defs_df = load_portfolio_definitions()

    defs = defs_df[defs_df["portfolio_name"] == portfolio_name].copy()
    if defs.empty:
        raise ValueError(f"Portfolio definition not found: {portfolio_name}")

    unknown_nodes = sorted(set(defs[~defs["node_id"].isin(valid_node_ids)]["node_id"].astype(str)))
    if unknown_nodes:
        raise ValueError(f"Portfolio references unknown node_id values: {unknown_nodes}")

    # Top-down allocation logic is isolated in portfolio_models.
    # Bottom-up implementation mapping remains in instrument_mapping and allocator routing.
    beta_cfg = _load_mode_beta_engine_config(mode)
    node_weights, allocation_mode = _dispatch_weighting_method(defs, beta_cfg)

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

    out_dir = _repo_root() / "outputs" / mode / "runtime"
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
    parser.add_argument("--mode", choices=["capital", "research"], default="capital")
    args = parser.parse_args()

    path = run_allocator(portfolio_name=args.portfolio_name, mode=args.mode)
    print(path)
