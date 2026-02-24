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
- Trigger phrase: `generate repo tree` (case-insensitive match accepted).
- Action: run `./scripts/generate_repo_tree.sh` from repo root.
- Behavior:
  - Exports full folder/file tree to depth 4.
  - Excludes `.git`, `.venv`, `__pycache__`, `outputs/capital/runs`, `outputs/research/runs`, and runtime-generated datasets.
  - Deterministic sorted output.
  - Writes to `control/infra_exports/repo_tree_YYYYMMDD.txt`.
  - Prints output path + first 40 lines.
  - Does not auto-commit.
