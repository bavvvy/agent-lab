# SYSTEM.md

## Purpose of Agent Lab
Agent Lab is a deterministic local research and reporting workspace for portfolio strategy development, validation, and publication to static web reports.

## Current architecture overview
- Core engine lives in `scientist-workspace/portfolio_engine/`.
- Backtest/report rendering lives in `scientist-workspace/backtest.py`.
- Publication orchestration is centralized in `scientist-workspace/publish.py`.
- Published artifacts are served from repository-root `reports/`.

## Directory structure summary
- `scientist-workspace/` — strategy code, backtest, publish workflow, tests.
- `reports/` — public HTML reports + `index.html` dashboard.
- `reports/archive/` — immutable timestamped report snapshots.
- `archive/` — local internal archive (not publication target).

## Report publication workflow
`scientist-workspace/publish.py` is the sole publication mechanism:
1. Runs deterministic `backtest.py` for a supported strategy.
2. Ensures report is written to `reports/<strategy>.html`.
3. Creates immutable timestamped version in `reports/`.
4. Regenerates `reports/index.html`.
5. Stages, commits, pushes to `origin/main`.
6. Verifies local/remote HEAD match.

## Report versioning rule
Timestamped report filenames must follow:
`YYYY-MM-DD_HH-MM_<strategy>.html` (UTC minute precision).

## Index rule
`reports/index.html` uses filename timestamp prefix as source of truth for:
- Published (UTC) display
- Sort order (newest first)
Non-conforming names are treated as `Legacy`.

## Public URL structure
- Dashboard: `https://bavvvy.github.io/agent-lab/reports/`
- Report page: `https://bavvvy.github.io/agent-lab/reports/<filename>.html`

## Guardrails (modifiable vs protected paths)
Modifiable:
- `scientist-workspace/`
- `reports/`

Protected / handle with care:
- `.git/`
- `archive/`

## High-level evolution roadmap
1. Add multi-strategy support in `publish.py` with explicit strategy registry.
2. Add deterministic data adapters (local snapshots) for non-synthetic backtests.
3. Expand report schema (factor attribution, exposures, rolling risk).
4. Add CI validation for report generation and index integrity.
5. Introduce strict config/version contracts across backtest and publish layers.
