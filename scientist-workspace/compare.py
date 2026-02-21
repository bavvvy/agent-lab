from __future__ import annotations

import argparse
import base64
import io
import math
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import backtest as bt
from portfolio_engine.engine import PortfolioEngine


def fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def rolling_3y_sharpe(df: pd.DataFrame) -> pd.DataFrame:
    monthly = df.iloc[1:].copy()
    x = monthly[["date", "ret"]].copy()
    vol = x["ret"].rolling(36).std(ddof=1) * math.sqrt(12)
    mean_ann = x["ret"].rolling(36).mean() * 12
    x["rolling_3y_sharpe"] = mean_ann / vol
    return x.dropna(subset=["rolling_3y_sharpe"])[["date", "rolling_3y_sharpe"]]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--strategy", action="append", required=True)
    args = p.parse_args()

    strategies = args.strategy
    workspace = Path(__file__).resolve().parent
    reports_dir = workspace.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    engine = PortfolioEngine.from_yaml(str(workspace / "config.yaml"))

    series_5y = {}
    series_3y_sharpe = {}
    summary_rows = []

    for s in strategies:
        portfolio, _ = bt._load_portfolio(s)
        tickers = list(portfolio["tickers"].keys())
        prices_daily, _ = bt._load_validated_prices(tickers)
        prices = prices_daily.groupby(prices_daily.index.to_period("M")).tail(1).copy()

        df, _, _ = bt._simulate_strategy(engine, portfolio, prices)
        roll5 = bt._rolling_5y_cagr(df)
        roll3s = rolling_3y_sharpe(df)

        name = str(portfolio["name"])
        series_5y[name] = roll5
        series_3y_sharpe[name] = roll3s

        summary_rows.append(
            {
                "Strategy": name,
                "Mean 5Y CAGR": f"{roll5['rolling_5y_cagr'].mean():.2%}" if not roll5.empty else "N/A",
                "Mean 3Y Sharpe": f"{roll3s['rolling_3y_sharpe'].mean():.3f}" if not roll3s.empty else "N/A",
            }
        )

    fig1 = plt.figure(figsize=(10, 4))
    for name, d in series_5y.items():
        if not d.empty:
            plt.plot(d["date"], d["rolling_5y_cagr"], lw=2, label=name)
    plt.title("Rolling 5Y CAGR Comparison")
    plt.grid(alpha=0.3)
    plt.legend()
    cagr_b64 = fig_to_base64(fig1)

    fig2 = plt.figure(figsize=(10, 4))
    for name, d in series_3y_sharpe.items():
        if not d.empty:
            plt.plot(d["date"], d["rolling_3y_sharpe"], lw=2, label=name)
    plt.title("Rolling 3Y Sharpe Comparison (rf=0)")
    plt.grid(alpha=0.3)
    plt.legend()
    sharpe_b64 = fig_to_base64(fig2)

    pair_line = "N/A"
    if len(strategies) >= 2:
        p1, _ = bt._load_portfolio(strategies[0])
        p2, _ = bt._load_portfolio(strategies[1])
        n1 = str(p1["name"])
        n2 = str(p2["name"])
        a = series_5y[n1]
        b = series_5y[n2]
        m = pd.merge(a, b, on="date", how="inner", suffixes=("_a", "_b"))
        if not m.empty:
            pct = float((m["rolling_5y_cagr_a"] > m["rolling_5y_cagr_b"]).mean())
            pair_line = f"{n1} > {n2}: {pct:.2%}"
        else:
            pair_line = f"{n1} > {n2}: N/A"

    summary_df = pd.DataFrame(summary_rows)
    summary_html = summary_df.to_html(index=False)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    out_name = f"comparison_{ts}.html"
    out_path = reports_dir / out_name

    html_doc = f"""<html><head><meta charset='utf-8'><title>Comparison Report</title>
<style>body{{font-family:Arial,sans-serif;max-width:1100px;margin:28px auto;padding:0 16px}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ddd;padding:8px}}th{{background:#f3f4f6}}img{{width:100%;height:auto;border:1px solid #ddd;border-radius:8px}}</style>
</head><body>
<h1>Strategy Comparison Report</h1>
<p><b>Strategies:</b> {', '.join(strategies)}</p>
<h2>Rolling 5Y CAGR Comparison</h2><img src='data:image/png;base64,{cagr_b64}' />
<h2>Rolling 3Y Sharpe Comparison</h2><img src='data:image/png;base64,{sharpe_b64}' />
<h2>Summary</h2>
{summary_html}
<p><b>% periods strategy A &gt; strategy B:</b> {pair_line}</p>
</body></html>"""
    out_path.write_text(html_doc, encoding="utf-8")
    print(f"COMPARISON_REPORT_PATH: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
