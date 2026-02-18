from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict

import yaml

from .compat import normalize_legacy_config
from .config_schema import EngineConfig, parse_engine_config
from .factory import build_pipeline


@dataclass
class PortfolioEngine:
    config: EngineConfig

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> "PortfolioEngine":
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        normalized = normalize_legacy_config(raw)
        config = parse_engine_config(normalized)
        return cls(config=config)

    def run(
        self,
        as_of_date: date,
        prices: Dict[str, float],
        portfolio_value: float,
        current_positions: Dict[str, float],
        last_rebalance_date: date | None,
    ) -> Dict[str, Any]:
        pipeline = build_pipeline(self.config)
        context: Dict[str, Any] = {
            "constraints": {
                "leverage": self.config.constraints.leverage,
            }
        }

        weights = pipeline.allocation_model.target_weights(
            as_of_date=as_of_date,
            context=context,
        )

        for overlay in pipeline.overlays:
            weights = overlay.apply(
                weights=weights,
                as_of_date=as_of_date,
                context=context,
            )

        should_rebalance = pipeline.rebalancer.should_rebalance(
            as_of_date=as_of_date,
            last_rebalance_date=last_rebalance_date,
            context=context,
        )

        allocations = pipeline.allocator.allocate(
            weights=weights,
            portfolio_value=portfolio_value,
            prices=prices,
            context=context,
        )

        target_positions = {
            symbol: alloc["target_units"] for symbol, alloc in allocations.items()
        }

        trades: Dict[str, float] = {}
        if should_rebalance:
            trades = pipeline.rebalancer.generate_trades(
                current_positions=current_positions,
                target_positions=target_positions,
                context=context,
            )

        return {
            "as_of_date": as_of_date.isoformat(),
            "weights": weights,
            "allocations": allocations,
            "should_rebalance": should_rebalance,
            "trades": trades,
        }
