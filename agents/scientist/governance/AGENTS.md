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
