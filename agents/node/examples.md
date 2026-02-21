# Node module example flows

## 1) `/node summary` (preview-only)

```bash
python node.py summary --profile retail --payload '{"strategy_type":"balanced","risk_tolerance":"moderate"}'
```

Behavior:
- Produces a human-readable interpretation of current inputs.
- Lists extracted structured fields and missing fields.
- Writes **no files**.
- Generates **no machine contract**.

---

## 2) `/node package` (manual approval workflow)

```bash
python node.py package --profile sophisticated --payload '{
  "strategy_type":"balanced",
  "risk_tolerance":"moderate",
  "leverage_allowed":false,
  "investment_vehicle":"etf",
  "base_currency":"AUD",
  "time_horizon":{"years":10,"objective":"balanced_growth"},
  "liquidity_constraints":{"redemption_window":"monthly","max_lockup_days":30}
}'
```

Behavior:
- Validates payload against `schema.py`.
- Refuses packaging if required fields are missing/invalid.
- Creates dual artefacts when valid:
  - `contracts/requests/<request_id>.json`
  - `contracts/briefs/<request_id>.md`
- Does **not** auto-trigger Scientist.

---

## Machine contract example

```json
{
  "contract_version": "1.0",
  "contract_type": "allocation_request",
  "origin": "node",
  "request_id": "req_20260221T061200Z_ab12cd34",
  "payload": {
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
      "max_lockup_days": 30
    }
  },
  "created_at": "2026-02-21T06:12:00+00:00"
}
```
