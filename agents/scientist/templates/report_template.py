from __future__ import annotations

import html
import pandas as pd


def _table_html(df_in: pd.DataFrame, numeric_cols: set[str]) -> str:
    cols = list(df_in.columns)
    thead = "".join(
        f"<th{' class=\"num\"' if c in numeric_cols else ''}>{html.escape(str(c))}</th>" for c in cols
    )
    rows = []
    for _, row in df_in.iterrows():
        tds = []
        for c in cols:
            cls = " class=\"num\"" if c in numeric_cols else ""
            tds.append(f"<td{cls}>{html.escape(str(row[c]))}</td>")
        rows.append("<tr>" + "".join(tds) + "</tr>")
    return f"<table><thead><tr>{thead}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def render_strategy_report(
    *,
    strategy_name: str,
    tickers: list[str],
    start_date: str,
    end_date: str,
    rebalance_rule: str,
    transaction_cost_bps: int,
    slippage_bps: int,
    initial_capital: float,
    engine_name: str,
    engine_version: str,
    portfolio_file: str,
    overlays: dict,
    rebalancer: dict,
    constraints: dict,
    weights: dict,
    metrics_df: pd.DataFrame,
    annual_returns_df: pd.DataFrame,
    weight_alloc_df: pd.DataFrame,
    monthly_data_df: pd.DataFrame,
    equity_chart_b64: str,
    drawdown_chart_b64: str,
) -> str:
    metrics_html = _table_html(metrics_df, {"Value"})
    annual_html = _table_html(annual_returns_df, {"annual_return"})
    weight_alloc_html = _table_html(weight_alloc_df, {"Weight"})
    monthly_html = _table_html(monthly_data_df, {c for c in monthly_data_df.columns if c != "date"})

    weights_items = "".join(
        f"<li><span>{html.escape(str(k))}</span><span class='num'>{float(v)*100:.2f}%</span></li>"
        for k, v in sorted(weights.items())
    )

    return f"""
<html><head><meta charset='utf-8'><title>Strategy Report</title>
<style>
  :root {{ --bg:#ffffff; --text:#111827; --muted:#4b5563; --line:#e5e7eb; --head:#f3f4f6; --code:#f8fafc; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,"Noto Sans",sans-serif; line-height:1.45; }}
  .container {{ max-width:1100px; margin:28px auto; padding:0 20px 28px; }}
  h1 {{ font-size:32px; margin:0 0 14px; letter-spacing:-0.02em; }}
  h2 {{ font-size:20px; margin:30px 0 12px; padding-bottom:8px; border-bottom:1px solid var(--line); }}
  .subhead {{ border:1px solid var(--line); border-radius:10px; background:#fafafa; padding:14px 16px; color:var(--muted); }}
  .subhead b {{ color:var(--text); }}
  table {{ border-collapse:collapse; width:100%; margin:10px 0 0; font-size:14px; }}
  th, td {{ border:1px solid var(--line); padding:8px 10px; }}
  th {{ background:var(--head); text-align:left; font-weight:600; }}
  td.num, th.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .chart img {{ width:100%; height:auto; border:1px solid var(--line); border-radius:8px; }}
  ul {{ margin:8px 0 0 18px; padding:0; }}
  .config-grid {{ display:grid; gap:12px; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); }}
  .cfg-card {{ background:var(--code); border:1px solid var(--line); border-radius:10px; padding:12px; }}
  .cfg-card h3 {{ margin:0 0 8px; font-size:15px; }}
  .cfg-card h4 {{ margin:10px 0 6px; font-size:13px; color:var(--muted); }}
  .cfg-card ul {{ list-style:none; margin:0; padding:0; }}
  .cfg-card li {{ display:flex; justify-content:space-between; gap:8px; padding:4px 0; border-bottom:1px dashed #e6e9ef; }}
  .cfg-card li:last-child {{ border-bottom:none; }}
</style>
</head><body><div class='container'>
<h1>Strategy Report: {html.escape(strategy_name)}</h1>
<div class='subhead'><b>Tickers:</b> {', '.join(tickers)}<br><b>Date range:</b> {start_date} to {end_date}<br><b>Rebalance rule:</b> {html.escape(rebalance_rule)}<br><b>Transaction cost assumption:</b> {transaction_cost_bps} bps (slippage {slippage_bps} bps)<br><b>Initial capital:</b> {initial_capital:,.2f}</div>
<h2>Config Snapshot</h2>
<div class='config-grid'>
  <div class='cfg-card'><h3>Engine</h3><ul><li><span>Name</span><span>{html.escape(engine_name)}</span></li><li><span>Version</span><span>{html.escape(engine_version)}</span></li></ul></div>
  <div class='cfg-card'><h3>Strategy</h3><ul><li><span>Name</span><span>{html.escape(strategy_name)}</span></li><li><span>Portfolio File</span><span>{html.escape(portfolio_file)}</span></li></ul><h4>Weights</h4><ul>{weights_items}</ul></div>
  <div class='cfg-card'><h3>Overlays</h3><ul><li><span>Risk</span><span>{html.escape(str(overlays.get('risk', '')))}</span></li><li><span>Regime</span><span>{html.escape(str(overlays.get('regime', '')))}</span></li></ul></div>
  <div class='cfg-card'><h3>Rebalancer</h3><ul><li><span>Type</span><span>{html.escape(str(rebalancer.get('type', '')))}</span></li></ul></div>
  <div class='cfg-card'><h3>Constraints</h3><ul><li><span>Leverage</span><span>{html.escape(str(constraints.get('leverage', '')))}</span></li></ul></div>
</div>
<h2>Summary Metrics</h2>{metrics_html}
<h2>Equity Curve</h2><div class='chart'><img src='data:image/png;base64,{equity_chart_b64}' /></div>
<h2>Drawdown</h2><div class='chart'><img src='data:image/png;base64,{drawdown_chart_b64}' /></div>
<h2>Annual Returns</h2>{annual_html}
<h2>Weight Allocation</h2>{weight_alloc_html}
<h2>Monthly Portfolio Data</h2>{monthly_html}
<h2>Methodology</h2>
<ul>
<li>Asset returns: simple close-to-close returns, P_t / P_{{t-1}} - 1.</li>
<li>Rebalancing: engine produces target holdings monthly; trades executed on rebalance months only.</li>
<li>Data source: local canonical dataset from `inputs/prices/prices_master.parquet` (no network calls).</li>
<li>Assumptions: no taxes, no transaction costs, no slippage, no leverage/borrow modeling beyond engine behavior.</li>
</ul>
</div></body></html>
"""
