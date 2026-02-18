from datetime import date

from portfolio_engine.engine import PortfolioEngine


def run() -> None:
    engine = PortfolioEngine.from_yaml("config.yaml")

    out_weights = engine.run(
        as_of_date=date(2026, 2, 2),
        prices={"SPY": 100.0, "TLT": 100.0},
        portfolio_value=1000.0,
        current_positions={"SPY": 6.0, "TLT": 4.0},
        last_rebalance_date=date(2026, 1, 2),
    )
    assert out_weights["weights"] == {"SPY": 0.6, "TLT": 0.4}

    out_no_rebalance = engine.run(
        as_of_date=date(2026, 2, 15),
        prices={"SPY": 100.0, "TLT": 100.0},
        portfolio_value=1000.0,
        current_positions={"SPY": 6.0, "TLT": 4.0},
        last_rebalance_date=date(2026, 2, 2),
    )
    assert out_no_rebalance["should_rebalance"] is False
    assert out_no_rebalance["trades"] == {}

    out_rebalance = engine.run(
        as_of_date=date(2026, 3, 2),
        prices={"SPY": 100.0, "TLT": 100.0},
        portfolio_value=1000.0,
        current_positions={"SPY": 5.0, "TLT": 5.0},
        last_rebalance_date=date(2026, 2, 2),
    )
    assert out_rebalance["should_rebalance"] is True
    assert out_rebalance["trades"] == {"SPY": 1.0, "TLT": -1.0}

    print("smoke_test: PASS")


if __name__ == "__main__":
    run()
