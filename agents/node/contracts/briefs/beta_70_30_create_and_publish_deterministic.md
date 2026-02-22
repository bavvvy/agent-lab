# Execution Brief: beta_70_30 (Contract Only)

## Intent
Create a new portfolio strategy from `beta_60_40`, keeping the same underlying assets, and adjusting weights to 70/30.

## Strategy Parameters
- **base_strategy:** `beta_60_40`
- **new_strategy:** `beta_70_30`
- **weights:**
  - `SPY`: `0.70`
  - `AGG`: `0.30`
- **action:** `create_and_publish`
- **mode:** `deterministic`

## Required Deliverables (Specified, Not Executed)
- Strategy definition for `beta_70_30`
- Publish report for `beta_70_30`

## Execution Guardrails
- **Do not execute**
- **Do not call Scientist**
- **Do not modify:** `agents/`, `outputs/`, `control/`
- **Do not create YAML directly**
- **Do not publish**

## Status
Structured execution contract generated only.
