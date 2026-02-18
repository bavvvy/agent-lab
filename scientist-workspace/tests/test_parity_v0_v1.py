from datetime import date

from portfolio_engine.engine import PortfolioEngine


class _V0ReferenceEngine:
    def __init__(self, config: dict):
        self.config = config

    def run(
        self,
        as_of_date: date,
        prices: dict[str, float],
        portfolio_value: float,
        current_positions: dict[str, float],
        last_rebalance_date: date | None,
    ) -> dict:
        weights = self.config["strategy"]["weights"]
        total = sum(weights.values())
        if total <= 0:
            raise ValueError("Configured weights must sum to a positive value")
        weights = {symbol: weight / total for symbol, weight in weights.items()}

        if last_rebalance_date is None:
            should_rebalance = True
        else:
            should_rebalance = (as_of_date.year, as_of_date.month) != (
                last_rebalance_date.year,
                last_rebalance_date.month,
            )

        allocations: dict[str, dict[str, float]] = {}
        for symbol, weight in weights.items():
            px = prices[symbol]
            target_notional = portfolio_value * weight
            target_units = target_notional / px
            allocations[symbol] = {
                "weight": weight,
                "target_notional": target_notional,
                "target_units": target_units,
            }

        target_positions = {
            symbol: alloc["target_units"] for symbol, alloc in allocations.items()
        }

        trades: dict[str, float] = {}
        if should_rebalance:
            symbols = set(current_positions) | set(target_positions)
            trades = {
                symbol: target_positions.get(symbol, 0.0) - current_positions.get(symbol, 0.0)
                for symbol in sorted(symbols)
            }

        return {
            "as_of_date": as_of_date.isoformat(),
            "weights": weights,
            "allocations": allocations,
            "should_rebalance": should_rebalance,
            "trades": trades,
        }


def test_v0_v1_parity_on_fixture():
    v0_config = {
        "engine": {"name": "portfolio_engine", "version": "0.0"},
        "strategy": {"name": "beta_engine_60_40", "weights": {"SPY": 0.6, "TLT": 0.4}},
        "overlays": {"risk": "risk_overlay_none", "regime": "regime_overlay_none"},
        "rebalancer": {"type": "monthly"},
        "constraints": {"leverage": False},
    }
    v0 = _V0ReferenceEngine(v0_config)
    v1 = PortfolioEngine.from_yaml("config.yaml")

    fixture = {
        "as_of_date": date(2026, 3, 2),
        "prices": {"SPY": 100.0, "TLT": 100.0},
        "portfolio_value": 1000.0,
        "current_positions": {"SPY": 5.0, "TLT": 5.0},
        "last_rebalance_date": date(2026, 2, 2),
    }

    out_v0 = v0.run(**fixture)
    out_v1 = v1.run(**fixture)

    assert out_v1 == out_v0
