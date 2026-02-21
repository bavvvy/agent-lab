# Node module

Node is the outward-facing capital allocation interface.

It gathers structured portfolio inputs from users and translates them into machine-readable payloads for MS. It can also translate MS results back into human-readable summaries.

## Hard boundaries

- Node does **not** modify `portfolio_engine`
- Node does **not** execute backtests
- Node does **not** change strategy logic
- Node does **not** publish reports
- Node does **not** commit to GitHub
- Node is stateless by default

## Commands

Run from `scientist-workspace/node/`:

- `/node gather` → collect missing required fields via clarifying questions
- `/node package` → emit structured JSON payload for MS
- `/node explain` → translate structured MS result into concise narrative

### CLI usage

```bash
python node.py gather --profile retail --payload '{}'
python node.py package --profile sophisticated --payload '{"strategy_type":"balanced"}'
python node.py explain --profile retail --ms-result '{"summary":"..."}'
```

## Schema

`schema.py` defines `ALLOCATION_REQUEST_SCHEMA` with required fields:

- `strategy_type`
- `risk_tolerance`
- `leverage_allowed`
- `investment_vehicle`
- `base_currency`
- `time_horizon`
- `liquidity_constraints`

See `examples.md` for complete flows and payload examples.
