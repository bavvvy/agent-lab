from __future__ import annotations

import base64
import io
import math
from datetime import date
from pathlib import Path
import sys

_venv_site = Path(".venv/lib/python3.12/site-packages")
if _venv_site.exists():
    sys.path.insert(0, str(_venv_site))

import matplotlib.pyplot as plt
import pandas as pd

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


def run_backtest() -> None:
    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    for p in output_dir.iterdir():
        if p.is_file():
            p.unlink()

    engine = PortfolioEngine.from_yaml("config.yaml")
    dates = month_ends(2024, 1, 24)
    prices = pd.DataFrame(
        {
            "date": dates,
            "SPY": [float(480 + i * 3 + (i % 4) * 2) for i in range(len(dates))],
            "TLT": [float(95 + (i % 6) - i * 0.2) for i in range(len(dates))],
        }
    )

    cash, positions, last_reb = 10000.0, {"SPY": 0.0, "TLT": 0.0}, None
    equity = []
    for _, r in prices.iterrows():
        dt = r["date"]
        px = {"SPY": float(r["SPY"]), "TLT": float(r["TLT"])}
        pv = cash + sum(positions[s] * px[s] for s in positions)
        out = engine.run(dt, px, pv, positions, last_reb)
        if out["should_rebalance"]:
            for s, du in out["trades"].items():
                cash -= du * px[s]
                positions[s] = positions.get(s, 0.0) + du
            last_reb = dt
        equity.append(cash + sum(positions[s] * px[s] for s in positions))

    df = pd.DataFrame({"date": pd.to_datetime(dates), "equity": equity})
    df["ret"] = df["equity"].pct_change().fillna(0.0)
    monthly = df.iloc[1:].copy()
    years = len(monthly) / 12
    cagr = float((df["equity"].iloc[-1] / df["equity"].iloc[0]) ** (1 / years) - 1) if years > 0 else 0.0
    vol = ann_std(monthly["ret"])
    sharpe = float((monthly["ret"].mean() * 12) / vol) if vol > 0 else 0.0
    mdd = max_drawdown(df["equity"])
    best_idx = monthly["ret"].idxmax()
    worst_idx = monthly["ret"].idxmin()
    pct_pos = float((monthly["ret"] > 0).mean()) if len(monthly) else 0.0
    annual_returns = monthly.assign(year=monthly["date"].dt.year).groupby("year")["ret"].apply(lambda x: (1 + x).prod() - 1)

    fig1 = plt.figure(figsize=(9, 4)); plt.plot(df["date"], df["equity"], lw=2); plt.title("Equity Curve"); plt.grid(alpha=0.3)
    equity_b64 = fig_to_base64(fig1)
    dd = df["equity"] / df["equity"].cummax() - 1.0
    fig2 = plt.figure(figsize=(9, 3.5)); plt.plot(df["date"], dd, color="crimson", lw=2); plt.title("Drawdown"); plt.grid(alpha=0.3)
    dd_b64 = fig_to_base64(fig2)

    metrics = pd.DataFrame(
        [
            ["CAGR", f"{cagr:.2%}"],
            ["Vol", f"{vol:.2%}"],
            ["Sharpe (rf=0)", f"{sharpe:.3f}"],
            ["Max drawdown", f"{mdd:.2%}"],
            ["Best month", f"{monthly.loc[best_idx, 'date'].date()} ({monthly.loc[best_idx, 'ret']:.2%})"],
            ["Worst month", f"{monthly.loc[worst_idx, 'date'].date()} ({monthly.loc[worst_idx, 'ret']:.2%})"],
            ["% positive months", f"{pct_pos:.2%}"],
        ],
        columns=["Metric", "Value"],
    )

    html = f"""
<html><head><meta charset='utf-8'><title>Backtest Report</title>
<style>body{{font-family:Arial,sans-serif;max-width:1000px;margin:24px auto;line-height:1.35}}table{{border-collapse:collapse;width:100%;margin:12px 0}}th,td{{border:1px solid #ddd;padding:8px;text-align:left}}th{{background:#f5f5f5}}img{{max-width:100%}}</style>
</head><body>
<h1>Portfolio Engine Backtest Report</h1>
<p><b>Strategy:</b> static 60/40 SPY/TLT | <b>Tickers:</b> SPY, TLT | <b>Date range:</b> {dates[0]} to {dates[-1]}<br>
<b>Rebalance rule:</b> monthly month-change via engine rebalancer | <b>Transaction cost assumption:</b> 0 bps (slippage 0 bps)</p>
<h2>Summary Metrics</h2>
{metrics.to_html(index=False, escape=False)}
<h2>Equity Curve</h2><img src='data:image/png;base64,{equity_b64}' />
<h2>Drawdown</h2><img src='data:image/png;base64,{dd_b64}' />
<h2>Annual Returns</h2>
{annual_returns.rename('annual_return').to_frame().to_html()}
<h2>Methodology & Assumptions</h2>
<ul>
<li>Returns are simple close-to-close percentage returns: P_t / P_{{t-1}} - 1.</li>
<li>At each monthly timestamp, engine generates target holdings and trades only if rebalancing is due.</li>
<li>Data is deterministic synthetic monthly prices generated in backtest.py; no external data feed.</li>
<li>Calendar assumption uses day 28 as month-end proxy; timezone Australia/Brisbane.</li>
<li>No transaction costs, no slippage, no taxes, no borrow/leverage modeling.</li>
</ul>
</body></html>
"""
    (output_dir / "report.html").write_text(html, encoding="utf-8")
    print("Saved: outputs/report.html")


if __name__ == "__main__":
    run_backtest()
