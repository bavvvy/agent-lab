# CONTEXT_BOOTSTRAP.md

## Architecture version
- 1.0

## System purpose
- Deterministic portfolio research/backtest reporting pipeline.
- Publish static reports to `reports/` for GitHub Pages delivery.

## Publication workflow summary
- Use `scientist-workspace/publish.py` (single publication entrypoint).
- Run backtest for strategy, regenerate `reports/index.html`, commit/push, verify HEAD parity.

## Naming conventions
- Strategy slug: hyphenated (e.g., `beta-engine-60-40`).
- Versioned report: `YYYY-MM-DD_HH-MM_<strategy>.html` (UTC).
- Dashboard: `reports/index.html`.

## Guardrails
- Safe to modify: `scientist-workspace/`, `reports/`.
- Protected: `.git/`, `archive/`.

## Current known strategies
- `beta_engine_60_40` (alias: `beta-engine-60-40`).

## Safe extension procedure
1. Add strategy mapping/validation in `publish.py`.
2. Keep outputs deterministic and self-contained HTML.
3. Preserve index rule: filename timestamp is publish truth.
4. Avoid changing engine core unless explicitly required.
5. Validate local run before commit/push.
