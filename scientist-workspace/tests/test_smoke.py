from datetime import date

from portfolio_engine.engine import PortfolioEngine


def _load_engine() -> PortfolioEngine:
    return PortfolioEngine.from_yaml("config.yaml")


def test_returns_config_weights_60_40():
    engine = _load_engine()

    out = engine.run(
        as_of_date=date(2026, 2, 2),
        prices={"SPY": 100.0, "TLT": 100.0},
        portfolio_value=1000.0,
        current_positions={"SPY": 6.0, "TLT": 4.0},
        last_rebalance_date=date(2026, 1, 2),
    )

    assert out["weights"] == {"SPY": 0.6, "TLT": 0.4}


def test_no_trades_on_non_rebalance_date():
    engine = _load_engine()

    out = engine.run(
        as_of_date=date(2026, 2, 15),
        prices={"SPY": 100.0, "TLT": 100.0},
        portfolio_value=1000.0,
        current_positions={"SPY": 6.0, "TLT": 4.0},
        last_rebalance_date=date(2026, 2, 2),
    )

    assert out["should_rebalance"] is False
    assert out["trades"] == {}


def test_correct_trades_on_rebalance_date():
    engine = _load_engine()

    out = engine.run(
        as_of_date=date(2026, 3, 2),
        prices={"SPY": 100.0, "TLT": 100.0},
        portfolio_value=1000.0,
        current_positions={"SPY": 5.0, "TLT": 5.0},
        last_rebalance_date=date(2026, 2, 2),
    )

    assert out["should_rebalance"] is True
    assert out["trades"] == {"SPY": 1.0, "TLT": -1.0}
