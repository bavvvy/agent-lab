from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


def normalize_legacy_config(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize v0.0 config into v0.1 schema without behavior change."""
    cfg = deepcopy(raw)

    if "allocation_model" in cfg:
        return cfg

    strategy = cfg.get("strategy", {})
    overlays = cfg.get("overlays", {})
    rebalancer = cfg.get("rebalancer", {})

    normalized = {
        "engine": cfg.get("engine", {"name": "portfolio_engine", "version": "0.1"}),
        "allocation_model": {
            "type": strategy.get("name", "beta_engine_60_40"),
            "params": {
                "weights": strategy.get("weights", {}),
            },
        },
        "overlays": [
            {"type": overlays.get("risk", "risk_overlay_none"), "params": {}},
            {"type": overlays.get("regime", "regime_overlay_none"), "params": {}},
        ],
        "rebalancer": {
            "type": rebalancer.get("type", "monthly"),
            "params": {},
        },
        "allocator": {
            "type": "capital_allocator",
            "params": {},
        },
        "constraints": cfg.get("constraints", {"leverage": False}),
    }

    return normalized
