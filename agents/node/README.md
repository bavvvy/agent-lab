# Node module

Node is the outward-facing capital allocation interface.

It gathers structured portfolio inputs from users and translates them into machine-readable payloads for MS. It can also provide a human preview before packaging.

## Hard boundaries

- Node does **not** modify `portfolio_engine`
- Node does **not** execute backtests
- Node does **not** change strategy logic
- Node does **not** publish reports
- Node does **not** commit to GitHub
- Node is session-scoped/stateless by default

## Commands

Run from `agent-lab/node/`:

- `/node summary` → preview interpreted understanding + extracted fields
- `/node package` → generate machine contract JSON + human brief markdown

### CLI usage

```bash
python node.py summary --profile retail --payload '{}'
python node.py package --profile sophisticated --payload '{"strategy_type":"balanced","risk_tolerance":"moderate","leverage_allowed":false,"investment_vehicle":"etf","base_currency":"AUD","time_horizon":{"years":10,"objective":"balanced_growth"},"liquidity_constraints":{"redemption_window":"monthly","max_lockup_days":30}}'
```

## Package outputs

- JSON contract: `agent-lab/contracts/requests/<request_id>.json`
- Markdown brief: `agent-lab/contracts/briefs/<request_id>.md`

JSON includes:
- `contract_version = "1.0"`
- `contract_type = "allocation_request"`
- `origin = "node"`
- `request_id`
- `payload`
- `created_at` (ISO8601 UTC)

Markdown includes:
- Request ID
- Extracted inputs
- Interpreted assumptions
- Clarifications made
- Execution instruction: `/ms execute request_id=<ID>`
