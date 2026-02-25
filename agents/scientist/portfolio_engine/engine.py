from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict

import pandas as pd

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


def run_portfolio_pipeline(
    strategy_name: str,
    mode: str,
    publish: bool = False,
    output_dataset_path: str | None = None,
):
    """Explicit orchestration skeleton for template -> strategy -> weights -> returns.

    This function intentionally reuses existing backtest flow and math.
    """
    from engine.backtest import (
        _config_path,
        _load_portfolio,
        _load_validated_prices,
        _simulate_strategy,
        run_backtest,
    )
    from portfolio_engine.modules.results import PortfolioResult
    from portfolio_engine.strategies.beta.strategy import BetaStrategy

    # 1) Load config
    config_path = _config_path(mode)
    engine = PortfolioEngine.from_yaml(str(config_path))

    # 2) Load template (portfolio definition)
    portfolio_template, _portfolio_path = _load_portfolio(strategy_name, mode=mode)

    # 3) Build strategy wrapper
    strategy = BetaStrategy(name=str(portfolio_template["name"]), template=portfolio_template)

    # 4) Generate weights (skeleton step; execution math still comes from existing engine)
    template_weights = strategy.generate_weights()

    # 5) Generate returns via existing simulation utilities
    tickers = list(portfolio_template["tickers"].keys())
    prices_daily, _stats = _load_validated_prices(tickers)
    prices = prices_daily.groupby(prices_daily.index.to_period("M")).tail(1).copy()
    simulated_df, _weights_df, _turnover = _simulate_strategy(engine, portfolio_template, prices)
    returns = list(pd.Series(simulated_df["monthly_return"]).astype(float).tolist())

    # 6) Wrap result
    result = PortfolioResult(
        name=strategy.name,
        weights=template_weights,
        returns=returns,
    )

    # 7) Optionally publish through existing backtest path
    run_backtest(
        strategy=strategy_name,
        publish=publish,
        output_dataset_path=output_dataset_path,
        mode=mode,
    )

    return result
