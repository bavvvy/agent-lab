from __future__ import annotations

import argparse
import base64
import html
import io
import json
import math
import subprocess
from datetime import date
from pathlib import Path
import sys

_venv_site = Path(".venv/lib/python3.12/site-packages")
if _venv_site.exists():
    sys.path.insert(0, str(_venv_site))

import matplotlib.pyplot as plt
import pandas as pd
import yaml

from portfolio_engine.engine import PortfolioEngine


def month_ends(start_year: int, start_month: int, periods: int) -> list[date]:
    y, m = start_year, start_month
    out = []
    for _ in range(periods):
        out.append(date(y, m, 28))
        m += 1
        if m > 12:
            y += 1
            m = 1
    return out


def ann_std(xs: pd.Series) -> float:
    return float(xs.std(ddof=1) * math.sqrt(12)) if len(xs) > 1 else 0.0


def max_drawdown(equity: pd.Series) -> float:
    dd = equity / equity.cummax() - 1.0
    return float(dd.min())


def fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def git_cmd(args: list[str]) -> str:
    return subprocess.check_output(args, text=True).strip()


def run_backtest(publish: bool = False) -> None:
    with open("config.yaml", "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)
    engine = PortfolioEngine.from_yaml("config.yaml")

    strategy_name = str(
        raw_config.get("strategy", {}).get("name")
        or getattr(engine.config.allocation_model, "type", "strategy")
    )
    strategy_slug = strategy_name.replace("_", "-").lower()

    dates = month_ends(2024, 1, 24)
    start_date, end_date = dates[0], dates[-1]
    initial_capital = 10000.0
    transaction_cost_bps = 0
    slippage_bps = 0
    rebalance_rule = "monthly month-change via engine rebalancer"

    prices = pd.DataFrame(
        {
            "date": pd.to_datetime(dates),
            "SPY": [float(480 + i * 3 + (i % 4) * 2) for i in range(len(dates))],
            "TLT": [float(95 + (i % 6) - i * 0.2) for i in range(len(dates))],
        }
    )

    cash, positions, last_reb = initial_capital, {"SPY": 0.0, "TLT": 0.0}, None
    equity, weight_rows, turnover_rows = [], [], []

    for _, r in prices.iterrows():
        dt = r["date"].date()
        px = {"SPY": float(r["SPY"]), "TLT": float(r["TLT"])}
        pv = cash + sum(positions[s] * px[s] for s in positions)
        out = engine.run(dt, px, pv, positions, last_reb)
        weight_rows.append({"date": dt.isoformat(), **out["weights"]})
        if out["should_rebalance"]:
            turnover_notional = sum(abs(du) * px[s] for s, du in out["trades"].items())
            turnover_rows.append(turnover_notional / pv if pv > 0 else 0.0)
            for s, du in out["trades"].items():
                cash -= du * px[s]
                positions[s] = positions.get(s, 0.0) + du
            last_reb = dt
        equity.append(cash + sum(positions[s] * px[s] for s in positions))

    df = pd.DataFrame({"date": prices["date"], "equity": equity})
    df["ret"] = df["equity"].pct_change().fillna(0.0)
    monthly = df.iloc[1:].copy()

    years = len(monthly) / 12
    total_return = float(df["equity"].iloc[-1] / df["equity"].iloc[0] - 1)
    cagr = float((1 + total_return) ** (1 / years) - 1) if years > 0 else 0.0
    vol = ann_std(monthly["ret"])
    sharpe = float((monthly["ret"].mean() * 12) / vol) if vol > 0 else 0.0
    mdd = max_drawdown(df["equity"])
    best_idx = monthly["ret"].idxmax()
    worst_idx = monthly["ret"].idxmin()
    best_month = monthly.loc[best_idx, "date"].date().isoformat()
    worst_month = monthly.loc[worst_idx, "date"].date().isoformat()
    pct_pos = float((monthly["ret"] > 0).mean()) if len(monthly) else 0.0
    turnover = float(sum(turnover_rows)) if turnover_rows else 0.0

    annual_returns = (
        monthly.assign(year=monthly["date"].dt.year)
        .groupby("year")["ret"]
        .apply(lambda x: (1 + x).prod() - 1)
    )
    weights_df = pd.DataFrame(weight_rows)

    fig1 = plt.figure(figsize=(9, 4))
    plt.plot(df["date"], df["equity"], lw=2)
    plt.title("Equity Curve")
    plt.grid(alpha=0.3)
    equity_b64 = fig_to_base64(fig1)

    dd = df["equity"] / df["equity"].cummax() - 1.0
    fig2 = plt.figure(figsize=(9, 3.5))
    plt.plot(df["date"], dd, color="crimson", lw=2)
    plt.title("Drawdown")
    plt.grid(alpha=0.3)
    dd_b64 = fig_to_base64(fig2)

    metrics = pd.DataFrame(
        [
            ["Total return", f"{total_return:.2%}"],
            ["CAGR", f"{cagr:.2%}"],
            ["Volatility", f"{vol:.2%}"],
            ["Sharpe (rf=0)", f"{sharpe:.3f}"],
            ["Max drawdown", f"{mdd:.2%}"],
            ["Best month", f"{best_month} ({monthly.loc[best_idx, 'ret']:.2%})"],
            ["Worst month", f"{worst_month} ({monthly.loc[worst_idx, 'ret']:.2%})"],
            ["% positive months", f"{pct_pos:.2%}"],
            ["Turnover", f"{turnover:.2%}"],
        ],
        columns=["Metric", "Value"],
    )

    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_name = f"{end_date.isoformat()}_{strategy_slug}.html"
    report_path = reports_dir / report_name

    annual_df = annual_returns.rename("annual_return").to_frame().reset_index()
    annual_df["annual_return"] = annual_df["annual_return"].map(lambda x: f"{x:.2%}")
    weights_fmt = weights_df.copy()
    for col in ["SPY", "TLT"]:
        if col in weights_fmt.columns:
            weights_fmt[col] = weights_fmt[col].map(lambda x: f"{float(x):.2%}")

    def table_html(df_in: pd.DataFrame, numeric_cols: set[str]) -> str:
        cols = list(df_in.columns)
        thead = "".join(
            f"<th{' class=\"num\"' if c in numeric_cols else ''}>{html.escape(str(c))}</th>"
            for c in cols
        )
        body_rows = []
        for _, row in df_in.iterrows():
            tds = []
            for c in cols:
                cls = " class=\"num\"" if c in numeric_cols else ""
                tds.append(f"<td{cls}>{html.escape(str(row[c]))}</td>")
            body_rows.append("<tr>" + "".join(tds) + "</tr>")
        return f"<table><thead><tr>{thead}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"

    metrics_html = table_html(metrics, {"Value"})
    annual_html = table_html(annual_df, {"annual_return"})
    weights_html = table_html(weights_fmt, {"SPY", "TLT"})

    html_report = f"""
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
  pre {{ background:var(--code); border:1px solid var(--line); border-radius:10px; padding:14px; overflow-x:auto; margin:0; font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace; font-size:13px; white-space:pre; }}
  .chart img {{ width:100%; height:auto; border:1px solid var(--line); border-radius:8px; }}
  ul {{ margin:8px 0 0 18px; padding:0; }}
</style>
</head><body><div class='container'>
<h1>Strategy Report: {html.escape(strategy_name)}</h1>
<div class='subhead'><b>Tickers:</b> SPY, TLT<br><b>Date range:</b> {start_date.isoformat()} to {end_date.isoformat()}<br><b>Rebalance rule:</b> {html.escape(rebalance_rule)}<br><b>Transaction cost assumption:</b> {transaction_cost_bps} bps (slippage {slippage_bps} bps)<br><b>Initial capital:</b> {initial_capital:,.2f}</div>
<h2>Config Snapshot</h2><pre>{html.escape(json.dumps(raw_config, indent=2))}</pre>
<h2>Summary Metrics</h2>{metrics_html}
<h2>Equity Curve</h2><div class='chart'><img src='data:image/png;base64,{equity_b64}' /></div>
<h2>Drawdown</h2><div class='chart'><img src='data:image/png;base64,{dd_b64}' /></div>
<h2>Annual Returns</h2>{annual_html}
<h2>Weight Allocation</h2>{weights_html}
<h2>Methodology</h2>
<ul>
<li>Asset returns: simple close-to-close returns, P_t / P_{{t-1}} - 1.</li>
<li>Rebalancing: engine produces target holdings monthly; trades executed on rebalance months only.</li>
<li>Data: deterministic synthetic monthly prices generated in this script (no external feed).</li>
<li>Assumptions: no taxes, no transaction costs, no slippage, no leverage/borrow modeling beyond engine behavior.</li>
</ul>
</div>
</body></html>
"""
    report_path.write_text(html_report, encoding="utf-8")

    print(f"CONFIG: config.yaml (strategy={strategy_name})")
    print(f"DATE_RANGE: {start_date.isoformat()} to {end_date.isoformat()}")
    print(f"METRICS: total_return={total_return:.6f}, cagr={cagr:.6f}, vol={vol:.6f}, sharpe={sharpe:.6f}, max_drawdown={mdd:.6f}, turnover={turnover:.6f}")
    print(f"REPORT_PATH: {report_path}")

    if publish:
        git_cmd(["git", "add", str(report_path)])
        has_staged_changes = subprocess.call(["git", "diff", "--cached", "--quiet"]) != 0
        if not has_staged_changes:
            print("PUBLISH: No changes detected. Skipping commit.")
        else:
            git_cmd(["git", "commit", "-m", f"Add report {report_name}"])
            git_cmd(["git", "push"])
            print("PUBLISH: Report committed and pushed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    run_backtest(publish=args.publish)
