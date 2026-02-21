# Backtest Review Pack

This backtest is deterministic and reproducible via:

```bash
PYTHONPATH=. python3 backtest.py
```

## Scope
- Engine: existing `portfolio_engine` (no architecture/allocation logic changes)
- Portfolio: static 60/40 SPY/TLT from `config.yaml`
- Rebalance: monthly, using engine rebalancer (`month-change` rule)
- Costs: transaction costs = 0 bps, slippage = 0 bps

## Data and assumptions
- Data source: deterministic synthetic monthly prices generated in `backtest.py`
- Frequency: monthly
- Calendar assumption: month-end proxy at day 28 each month
- Timezone: Australia/Brisbane
- Return method: simple close-to-close return (`P_t / P_{t-1} - 1`)
- Risk-free rate for Sharpe: 0

## Outputs generated in `outputs/`
- `run_manifest.json`: full run assumptions/metadata
- `prices.csv`: aligned price panel used by the run
- `returns.csv`: per-asset return series derived from prices
- `weights.csv`: target weights output by engine through time
- `portfolio_returns.csv`: portfolio monthly returns and equity
- `summary.json`: CAGR, vol, Sharpe, max drawdown, best/worst month, % positive months
- `equity_curve.png`: equity plot with title/subtitle metrics
- `drawdown.png`: drawdown time series

## Determinism
- No random sampling is used.
- Inputs are generated from fixed formulas.
- Running the command above recreates all output files deterministically.
