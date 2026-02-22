# Execution Brief: mcd_bac_50_50_20y (Contract Only)

## Intent
Create a new portfolio strategy with a 50/50 split between McDonald's (`MCD`) and Bank of America (`BAC`), using a 20-year lookback horizon.

## Strategy Parameters
- **new_strategy:** `mcd_bac_50_50_20y`
- **assets:**
  - `MCD`: `0.50`
  - `BAC`: `0.50`
- **lookback_period:** `20_years`
- **action:** `create_and_publish`
- **mode:** `deterministic`

## Required Deliverables (Specified, Not Executed)
- Strategy definition for `mcd_bac_50_50_20y`
- Publish deterministic report for `mcd_bac_50_50_20y`

## Execution Guardrails
- **Do not execute**
- **Do not call Scientist**
- **Do not modify:** `agents/`, `outputs/`, `control/`
- **Do not create YAML directly**
- **Do not publish**

## Status
Structured execution contract generated only.
