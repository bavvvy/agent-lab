# Node module example flows

## 1) Retail user scenario

User: "I want something balanced and not too scary."

Node (`/node gather --profile retail --payload '{}'`):
- Asks missing-field questions in plain language
- Example clarifier: "How much volatility can you tolerate: low, moderate, high, or very high?"

User provides structured details.

Node (`/node package --profile retail --payload '<json>'`):
- Returns JSON handoff payload for MS.

Node does **not** provide allocation percentages until MS responds.

---

## 2) Sophisticated allocator scenario

Allocator: "Need real-return sleeve, AUD base, leverage off, monthly liquidity."

Node (`/node gather --profile sophisticated --payload '<partial json>'`):
- Asks only unresolved fields with terse institutional wording.

Node (`/node package --profile sophisticated --payload '<complete json>'`):
- Emits schema-bound payload for MS.

After MS returns results:

Node (`/node explain --profile sophisticated --ms-result '<json>'`):
- Converts structured MS output into concise human-readable summary.

---

## Example payload to MS

```json
{
  "module": "node",
  "action": "package",
  "status": "ready",
  "schema_id": "node/allocation_request.schema.json",
  "allocation_request": {
    "strategy_type": "balanced",
    "risk_tolerance": "moderate",
    "leverage_allowed": false,
    "investment_vehicle": "etf",
    "base_currency": "AUD",
    "time_horizon": {
      "years": 10,
      "objective": "balanced_growth"
    },
    "liquidity_constraints": {
      "redemption_window": "monthly",
      "max_lockup_days": 30,
      "notes": "Prefer liquid broad-market exposures"
    },
    "user_profile": "retail"
  },
  "handoff_target": "ms",
  "guarantees": {
    "no_backtest_executed": true,
    "no_strategy_logic_change": true,
    "no_portfolio_engine_modification": true
  }
}
```
