# CONTEXT_BOOTSTRAP.md

## Architecture version
- 2.1

## High-level architecture
Agent Lab uses a layered architecture with explicit constitutional, system-mode, execution, shared-input, and artifact layers.

- Constitutional layer: `control/`
- System mode layer: `systems/` (`capital/`, `research/`)
- Execution layer: `agents/node/`, `agents/scientist/`
- Shared data layer: `inputs/`
- Artifact layer: `outputs/` (mode-scoped)
- Contracts plane: `contracts/`

## Responsibility boundaries
### control/
- Owns architecture definitions, invariants, and configuration context.
- Must describe reality of repository state; it does not execute workloads.

### systems/
- Owns mode-scoped orchestration/config and portfolio definitions.
- `systems/capital/` is canonical for capital runtime behavior.
- `systems/research/` is isolated research-mode configuration.

### agents/node/
- Owns structured payload validation and request packaging.
- Produces contracts in `contracts/requests/` and briefs in `contracts/briefs/`.

### agents/scientist/
- Owns deterministic backtest execution wrappers and engine runtime.
- Owns comparative report generation.
- Owns publication orchestration runtime.

### outputs/
- Owns runtime and publication artifacts.
- Artifacts are mode-scoped under `outputs/<mode>/...`.

## Publication/output model
- Entrypoint wrapper: `agents/scientist/publish.py`
- Engine implementation: `agents/scientist/engine/publish.py`
- Active runs root: `outputs/<mode>/runs/`
- Active archive root: `outputs/<mode>/archive/`
- Active runtime root: `outputs/<mode>/runtime/`
- Timestamped artifact format: `YYYY-MM-DD_HH-MM_<strategy>.html` (UTC)
- Index ordering source: filename timestamp parsing

## Invariants
1. Publication writes timestamped reports under `outputs/<mode>/runs/`.
2. Archive target is `outputs/<mode>/archive/` and must be created if missing.
3. Runtime artifacts are mode-scoped under `outputs/<mode>/runtime/`.
4. Index ordering is derived from filename timestamps, not commit time.
5. Publish flow stages changes with `git add -A`.
6. Publish flow executes pytest gate before push when staged changes exist.
7. Publish flow commits and pushes to `origin/main` when changes exist.
8. HEAD parity is enforced at end of publish flow.
9. Capital system must not depend on research system.

## Guardrails
### Modifiable paths
- `control/`
- `systems/`
- `agents/node/`
- `agents/scientist/`
- `contracts/`
- `inputs/`

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
