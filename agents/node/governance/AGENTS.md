This file is subordinate to control/*. In case of conflict, control/ prevails.

# Node Governance Commands

## Bounded orchestration command

- Command: `run portfolio <portfolio_id> <mode>`
- Purpose: trigger a Scientist portfolio run from Node with strict validation and controlled execution.

### Validation gates (must all pass)
1. `portfolio_id` must exist in `inputs/portfolios/portfolio_templates.csv`.
2. `mode` must be one of: `capital`, `research`.
3. `data/market/prices_master.parquet` must exist.

### On validation failure
- Return a clear error message.
- Do **not** run Scientist subprocess execution.

### On validation success
- Execute only:
  - `cd agents/scientist`
  - `.venv/bin/python cli/backtest.py --strategy <portfolio_id> --mode <mode>`
- Capture and return:
  - exit code
  - stdout
  - stderr
  - parsed metrics from stdout when present (`total_return`, `cagr`, `vol`, `sharpe`, `max_drawdown`, `turnover`)

### Required response shape
- `RUN SUMMARY`
- `Portfolio:`
- `Mode:`
- `Exit status:`
- `Metrics:`
- `Output path:`
- `Timestamp:`

### Hard constraints
Node must not modify:
- CSV portfolio files
- `systems/config.yaml`
- `data/`
- weighting logic

Node must not auto-commit changes.
