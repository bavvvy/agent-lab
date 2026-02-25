This file is subordinate to control/*. In case of conflict, control/ prevails.

# Scientist Agent Operating Notes

## Scope
- Owns research, backtesting, comparison, and publication orchestration for scientist workflows.
- Works only within scientist execution boundaries.

## Allowed focus
- `agents/scientist/` code and data workflow support.
- Runtime artifacts required by scientist execution flows.

## Prohibited without explicit instruction
- Modifying control-plane constitutional files beyond requested documentation tasks.
- Changing publish invariants or system-level governance behavior.

## Operational reminders
- Keep outputs deterministic.
- Preserve path and naming invariants defined in `control/SYSTEM.md`.
- Use explicit commits with clear intent.

## Infrastructure Commands
- Trigger phrase: `refresh repo tree` (case-insensitive match accepted).
- Action: run `./scripts/refresh_repo_tree.sh` from repo root.
- Behavior:
  - Exports deterministic, sorted folder/file tree to depth 4.
  - Includes files and directories.
  - Excludes `.git`, `.venv`, `__pycache__`, `outputs/capital/runs`, `outputs/research/runs`, and large archive paths (`outputs/*/archive`) as needed.
  - Excludes runtime-generated datasets (including `agents/scientist/output` and generated `csv/parquet` datasets under `outputs/`).
  - Writes to `control/infra_exports/repo_tree_YYYYMMDD.txt` (or `_NN` suffix on same date to avoid overwrite).
  - Prints full saved path + first 40 lines.
  - Does not modify `SYSTEM.md`, bootstrap, or agents; does not run npm; does not auto-commit.

## Constitution Maintenance Commands
- `refresh constitution`
  - Update `control/SYSTEM.md` to match current layered architecture/invariants and reconcile outdated references.
  - Regenerate `BOOTSTRAP_EXPORT.txt` at repo root.
  - Do **not** run npm.
  - Do **not** upgrade OpenClaw.
  - Do **not** modify runtime.
  - Do **not** change portfolio logic.
  - Do **not** change enforcement.
  - Do **not** change systems config.
  - Do **not** modify `agents/*` or `systems/*`.
  - Do **not** delete files.
  - Do **not** auto-commit; print summary + diff preview only.

- `regenerate bootstrap export`
  - Generate `BOOTSTRAP_EXPORT.txt` at repo root from current control-plane content.
  - Do **not** modify `SYSTEM.md`.
  - Do **not** modify OpenClaw runtime.

- `refresh constitution and bootstrap`
  - Run `refresh constitution`, then `regenerate bootstrap export`.
  - No runtime updates.
