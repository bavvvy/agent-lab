# ARCHITECTURE.md

## Scope
Repository structure only. This document defines layer boundaries, not runtime behaviour.

## Layer meanings
- `control/` — governance, constitutional constraints, and structural policy.
- `contracts/` — structured request/brief payload boundaries between intake and execution.
- `orchestration/` — workflow coordination, scheduling, and sequencing glue.
- `agents/` — interface and execution actors that consume contracts and invoke orchestrated flows.
- `systems/` — bounded financial domain containers.
- `data/` — canonical datasets and market inputs persisted for execution.
- `inputs/` — human-authored definitions, templates, and parameter sources.
- `outputs/` — generated runtime artefacts (reports, runs, archives, indexes).
- `scripts/` — utility and maintenance tooling.

## Formal definition: System
A **System** is a bounded financial domain container with its own engine, configuration surface, and runtime behaviour.

## Structural invariants
- Financial logic may exist only in `systems/<name>/engine/`.
- `orchestration/` may not compute financial metrics or allocation logic.
- `contracts/` may not contain executable business logic.
- `scripts/` may not contain financial models.
- `outputs/` are runtime artefacts and may not be imported as logic.
- `agents/` may not create new top-level folders without governance update.
