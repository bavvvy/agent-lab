# CONTEXT_BOOTSTRAP.md

## Architecture version
- 2.0

## High-level architecture
Agent Lab uses a v2 multi-agent structure with explicit separation between control-plane definitions and execution runtime.

- Control-plane: `control/`
- Execution agents: `agents/node/`, `agents/scientist/`
- Artifacts/output plane: `outputs/`
- Contracts plane: `contracts/`

## Responsibility boundaries
### control/
- Owns architecture definitions, invariants, and configuration context.
- Must describe reality of repository state; it does not execute workloads.

### agents/node/
- Owns structured payload validation and request packaging.
- Produces contracts in `contracts/requests/` and briefs in `contracts/briefs/`.

### agents/scientist/
- Owns deterministic backtest execution (`backtest.py`).
- Owns comparative report generation (`compare.py`).
- Owns publication orchestration (`publish.py`).

### outputs/
- Owns publication artifacts and runtime artifacts.
- Canonical publish root is `outputs/reports/`.

## Publication model
- Entrypoint: `agents/scientist/publish.py`
- Publish root: `outputs/reports/`
- Archive path: `outputs/reports/archive/`
- Index path: `outputs/reports/index.html`
- Timestamped artifact format: `YYYY-MM-DD_HH-MM_<strategy>.html` (UTC)
- Index ordering source: filename timestamp parsing

## Invariants
1. Publication writes timestamped reports under `outputs/reports/`.
2. Archive target is `outputs/reports/archive/` and must be created if missing.
3. Index regeneration targets `outputs/reports/index.html`.
4. Index ordering is derived from filename timestamps, not commit time.
5. Publish flow stages changes with `git add -A`.
6. Publish flow executes pytest gate before push when staged changes exist.
7. Publish flow commits and pushes to `origin/main` when changes exist.
8. HEAD parity is enforced at end of publish flow.

## Guardrails
### Modifiable paths
- `control/`
- `agents/node/`
- `agents/scientist/`
- `contracts/`

### Protected paths
- `.git/`
- `outputs/` (artifact plane; do not mutate manually unless explicitly requested)

## Existence assertions (repository state)
- `scientist-workspace/` does not exist in this repository.
- `reports/` at repository root does not exist in this repository.

## Deterministic operating posture
- Derive architecture from current repository state and live execution code.
- Do not assume legacy v1 topology.
- Keep control-plane statements aligned with runtime entrypoints and artifact paths.
