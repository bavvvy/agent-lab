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

## Repository Identity Invariant
The following files must NOT exist at repository root:
- `AGENTS.md`
- `BOOTSTRAP.md`
- `IDENTITY.md`
- `SOUL.md`
- `TOOLS.md`
- `USER.md`
- `HEARTBEAT.md`

Identity files are permitted ONLY in:
- `control/`
- `agents/node/`
- `agents/scientist/`

If root-level identity files are detected, this constitutes architectural drift and must be corrected before any publish action.

## Node Capability Specification (Passive Mode)
Purpose:
Node is the external interface layer. It ingests unstructured human instructions (e.g., from Discord) and produces structured contracts for execution by Scientist.

Scope (Allowed):
- Ingest natural language instructions.
- Validate payload structure.
- Generate structured JSON requests.
- Generate human-readable briefs.
- Write ONLY to:
  - `contracts/requests/`
  - `contracts/briefs/`

Explicitly Forbidden:
- Modifying `control/`
- Modifying `agents/scientist/`
- Modifying `outputs/`
- Calling `publish.py`
- Executing backtests directly
- Updating `system_config.yaml`
- Introducing new top-level directories
- Writing to repository root

Execution Boundary:
- Scientist must consume structured contracts only.
- Scientist must not parse raw Discord messages.

Autonomy Level:
Node operates in Passive Mode:
- It writes contracts.
- It does NOT trigger execution automatically.

## Guardrails
### Modifiable
- `control/`
- `agents/node/`
- `agents/scientist/`
- `contracts/`

### Protected / caution
- `.git/`
- `outputs/` (artifact space; modify only via execution workflows unless explicitly requested)

### Node Write Guardrail
Node write permissions are restricted to:
- `contracts/requests/`
- `contracts/briefs/`

Any attempt to write elsewhere constitutes architectural violation.

## Multi-agent responsibility summary
- Node agent (`agents/node/`) validates and packages structured requests into contracts.
- Scientist agent (`agents/scientist/`) executes portfolio analytics and publication workflows.
- Control-plane (`control/`) defines architecture and invariants without replacing runtime truth.

## Control Commands
### generate bootstrap
When the phrase `generate bootstrap` is received, the system must:
1. Overwrite `./BOOTSTRAP_EXPORT.txt` at repository root.
2. Insert full unmodified contents of:
   - `control/SYSTEM.md`
   - `control/CONTEXT_BOOTSTRAP.md`
   - `control/system_config.yaml`
3. Preserve formatting exactly.
4. Confirm only `BOOTSTRAP_EXPORT.txt` changed.
5. Commit with message:
   - `Regenerate portable control-plane bootstrap export`
6. Push to `origin main`.
7. Confirm HEAD parity `TRUE`.

### update system
When the phrase `update system` is received, the system must:
1. Inspect live repository state at repo root.
2. Inspect:
   - `agents/scientist/backtest.py`
   - `agents/scientist/compare.py`
   - `agents/scientist/publish.py`
   - `agents/node/`
   - `outputs/`
   - `contracts/`
3. Derive architecture strictly from current repository state.
4. Update ONLY the following files if misaligned:
   - `control/SYSTEM.md`
   - `control/CONTEXT_BOOTSTRAP.md`
   - `control/system_config.yaml`
5. Requirements:
   - Preserve canonical publish root: `outputs/reports/`
   - Preserve archive path: `outputs/reports/archive/`
   - Preserve timestamp format invariant.
   - Preserve pytest gate + git add + commit + push flow.
   - Preserve HEAD parity enforcement.
   - Preserve Repository Identity Invariant.
   - Do NOT introduce legacy references (e.g., `scientist-workspace/`, root `reports/`).
6. Do NOT modify:
   - `agents/`
   - `outputs/`
   - `contracts/`
   - `.git/`
7. After changes:
   - Show diff summary for modified control files only.
   - Commit with message:
     - `Update control-plane documentation to reflect live repository state`
   - Push to `origin main`.
   - Confirm HEAD parity `TRUE`.
