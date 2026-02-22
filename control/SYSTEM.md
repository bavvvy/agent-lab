# SYSTEM.md

## Architecture version
- 2.0

## Purpose
Agent Lab is a deterministic multi-agent portfolio research and publication system with a separated control-plane and execution layer.

## Canonical topology
- `control/` — control-plane documentation, invariants, and configuration context.
- `agents/node/` — Node intake/packaging agent and schema validation.
- `agents/scientist/` — Scientist execution pipeline (backtest, compare, publish, tests).
- `outputs/` — runtime and publication artifacts.
- `contracts/` — generated machine contracts and human briefs.

## Control-plane / execution separation
- Control-plane definitions live under `control/` and must not be treated as execution outputs.
- Execution code lives under `agents/`.
- Publication artifacts live under `outputs/`.

## Publication paths (canonical)
- Publish root: `outputs/reports/`
- Archive: `outputs/reports/archive/`
- Index: `outputs/reports/index.html`

## Publication entrypoint
- `agents/scientist/publish.py` is the publication entrypoint.

## Deterministic execution model
- Backtest execution is deterministic from local inputs and strategy configuration.
- Publish workflow invokes backtest generation before publication actions.

## Report naming invariant
Versioned report filename format is:
- `YYYY-MM-DD_HH-MM_<strategy>.html`
- Timestamp is UTC minute precision.

## Index ordering invariant
- Index ordering and displayed publish time are derived from filename timestamps.
- Non-conforming filenames are treated as legacy rows by policy utilities.

## Publish workflow invariants
In `agents/scientist/publish.py`:
1. Resolve strategy and validate allowed publication scope.
2. Execute backtest generation for target strategy.
3. Create timestamped report in `outputs/reports/`.
4. Ensure `outputs/reports/archive/` exists and archive prior timestamped versions.
5. Regenerate `outputs/reports/index.html` from filename timestamps.
6. Stage repository changes with `git add -A`.
7. If staged changes exist, run pytest gate before push.
8. Commit and push to `origin/main`.
9. Enforce HEAD parity (`HEAD == origin/main`).

## Guardrails
### Modifiable
- `control/`
- `agents/node/`
- `agents/scientist/`
- `contracts/`

### Protected / caution
- `.git/`
- `outputs/` (artifact space; modify only via execution workflows unless explicitly requested)

## Multi-agent responsibility summary
- Node agent (`agents/node/`) validates and packages structured requests into contracts.
- Scientist agent (`agents/scientist/`) executes portfolio analytics and publication workflows.
- Control-plane (`control/`) defines architecture and invariants without replacing runtime truth.
