from __future__ import annotations

import argparse
import base64
import html
import io
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import sys

_venv_site = Path(".venv/lib/python3.12/site-packages")
if _venv_site.exists():
    sys.path.insert(0, str(_venv_site))

import matplotlib.pyplot as plt
import pandas as pd
import yaml

from portfolio_engine.engine import PortfolioEngine

DATA_PATH = Path(__file__).resolve().parent / "data" / "prices_master.parquet"
PORTFOLIO_DIR = Path(__file__).resolve().parent / "portfolios"
SYMBOL_MAP = {"AGG": "TLT"}


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


def _to_engine_symbol(ticker: str) -> str:
    return SYMBOL_MAP.get(ticker, ticker)


def _to_portfolio_symbol(symbol: str) -> str:
    for k, v in SYMBOL_MAP.items():
        if v == symbol:
            return k
    return symbol


def _load_portfolio(strategy: str) -> tuple[dict, Path]:
    candidate_names = [strategy, strategy.replace("-", "_")]
    path = None
    for n in candidate_names:
        p = PORTFOLIO_DIR / f"{n}.yaml"
        if p.exists():
            path = p
            break

    if path is None:
        # Fallback: resolve by internal portfolio `name` field.
        for p in sorted(PORTFOLIO_DIR.glob("*.yaml")):
            payload = yaml.safe_load(p.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                nm = str(payload.get("name", "")).replace("-", "_")
                if nm == strategy.replace("-", "_"):
                    path = p
                    break

    if path is None:
        raise FileNotFoundError(f"Portfolio YAML not found for strategy '{strategy}'")

    portfolio = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(portfolio, dict):
        raise ValueError("Portfolio file must define a mapping")

    if "name" not in portfolio or "tickers" not in portfolio or "rebalance" not in portfolio:
        raise ValueError("Portfolio YAML requires: name, tickers, rebalance")

    tickers = portfolio["tickers"]
    if not isinstance(tickers, dict) or not tickers:
        raise ValueError("tickers must be a non-empty mapping")

    total = float(sum(float(v) for v in tickers.values()))
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"Portfolio weights must sum to 1.0 (got {total})")

    portfolio["tickers"] = {str(k): float(v) for k, v in tickers.items()}
    return portfolio, path


def _load_validated_prices(required_columns: list[str]) -> tuple[pd.DataFrame, dict[str, str | int]]:
    if not DATA_PATH.exists():
        raise FileNotFoundError("prices_master.parquet not found. Run data/update_prices.py first.")

    df = pd.read_parquet(DATA_PATH)
    if not set(required_columns).issubset(df.columns):
        raise ValueError(f"Dataset missing required columns. Expected: {required_columns}")

    if not isinstance(df.index, pd.DatetimeIndex):
        if "date" in df.columns:
            df = df.set_index("date")
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("Dataset index must be DatetimeIndex")

    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_convert(None)

    df = df.sort_index()
    raw_stats = {
        "RAW_START": str(df.index.min().date()),
        "RAW_END": str(df.index.max().date()),
        "RAW_ROWS": int(len(df)),
    }

    required = df[required_columns].copy()
    effective = required.dropna()
    if effective.empty:
        raise ValueError(f"Dataset contains no complete rows for required columns: {required_columns}")

    effective_stats = {
        "EFFECTIVE_START": str(effective.index.min().date()),
        "EFFECTIVE_END": str(effective.index.max().date()),
        "EFFECTIVE_ROWS": int(len(effective)),
    }

    in_window = required.loc[effective.index.min() : effective.index.max()]
    if in_window.isna().any().any():
        raise ValueError("Required tickers contain NaNs inside effective analysis window")

    pre_window = required.loc[required.index < effective.index.min()]
    if not pre_window.empty and pre_window.isna().any().any():
        print("INFO: NaNs detected before EFFECTIVE_START (likely ETF inception alignment).")

    return effective, {**raw_stats, **effective_stats}


def _simulate_strategy(
    engine: PortfolioEngine,
    portfolio: dict,
    prices: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    tickers = list(portfolio["tickers"].keys())
    engine_weights = {_to_engine_symbol(k): float(v) for k, v in portfolio["tickers"].items()}
    engine.config.allocation_model.params["weights"] = engine_weights

    engine_symbols = [_to_engine_symbol(t) for t in tickers]
    engine_to_portfolio = {_to_engine_symbol(t): t for t in tickers}
    cash, positions, last_reb = 10000.0, {s: 0.0 for s in engine_symbols}, None
    equity, weight_rows, turnover_rows = [], [], []

    for dt, row in prices.iterrows():
        as_of = dt.date()
        px = {_to_engine_symbol(t): float(row[t]) for t in tickers}
        pv = cash + sum(positions[s] * px[s] for s in positions)
        out = engine.run(as_of, px, pv, positions, last_reb)

        display_weights = {engine_to_portfolio.get(k, k): v for k, v in out["weights"].items()}
        weight_rows.append({"date": as_of.isoformat(), **display_weights})

        if out["should_rebalance"]:
            turnover_notional = sum(abs(du) * px[s] for s, du in out["trades"].items())
            turnover_rows.append(turnover_notional / pv if pv > 0 else 0.0)
            for s, du in out["trades"].items():
                cash -= du * px[s]
                positions[s] = positions.get(s, 0.0) + du
            last_reb = as_of
        equity.append(cash + sum(positions[s] * px[s] for s in positions))

    df = pd.DataFrame({"date": prices.index, "equity": equity})
    df["ret"] = df["equity"].pct_change().fillna(0.0)
    weights_df = pd.DataFrame(weight_rows)
    turnover = float(sum(turnover_rows)) if turnover_rows else 0.0
    return df, weights_df, turnover


def _rolling_5y_cagr(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) < 61:
        return pd.DataFrame(columns=["date", "rolling_5y_cagr"])
    out = []
    eq = df["equity"].tolist()
    dates = df["date"].tolist()
    for i in range(0, len(eq) - 60):
        cagr = (eq[i + 60] / eq[i]) ** (1 / 5) - 1
        out.append({"date": dates[i + 60], "rolling_5y_cagr": cagr})
    return pd.DataFrame(out)


def run_backtest(strategy: str, publish: bool = False) -> None:
    with open("config.yaml", "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)
    engine = PortfolioEngine.from_yaml("config.yaml")

    portfolio, portfolio_path = _load_portfolio(strategy)
    strategy_name = str(portfolio["name"])
    strategy_slug = strategy_name.replace("_", "-").lower()
    tickers = list(portfolio["tickers"].keys())

    prices_daily, stats = _load_validated_prices(tickers)
    print(f"RAW_START: {stats['RAW_START']}")
    print(f"RAW_END: {stats['RAW_END']}")
    print(f"RAW_ROWS: {stats['RAW_ROWS']}")
    print(f"EFFECTIVE_START: {stats['EFFECTIVE_START']}")
    print(f"EFFECTIVE_END: {stats['EFFECTIVE_END']}")
    print(f"EFFECTIVE_ROWS: {stats['EFFECTIVE_ROWS']}")
    print(f"DATASET_TICKERS: {', '.join(tickers)}")

    prices = prices_daily.groupby(prices_daily.index.to_period("M")).tail(1).copy()

    start_date = prices.index.min().date()
    end_date = prices.index.max().date()
    initial_capital = 10000.0
    transaction_cost_bps = 0
    slippage_bps = 0
    rebalance_rule = str(portfolio.get("rebalance", "monthly"))

    df, weights_df, turnover = _simulate_strategy(engine, portfolio, prices)
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
    periods = len(monthly)
    turnover_annualised = (turnover / periods) * 12 if periods > 0 else 0.0

    annual_returns = monthly.assign(year=monthly["date"].dt.year).groupby("year")["ret"].apply(lambda x: (1 + x).prod() - 1)

    rolling_5y = _rolling_5y_cagr(df).rename(columns={"rolling_5y_cagr": "rolling_60m_cagr"})

    rolling_60 = monthly[["date", "ret"]].copy()
    rolling_60["rolling_60m_vol"] = rolling_60["ret"].rolling(window=60).std(ddof=1) * math.sqrt(12)
    roll_mean_60 = rolling_60["ret"].rolling(window=60).mean() * 12
    rolling_60["rolling_60m_sharpe"] = roll_mean_60 / rolling_60["rolling_60m_vol"]

    rolling_36 = monthly[["date", "ret"]].copy()
    roll_mean_36 = rolling_36["ret"].rolling(window=36).mean() * 12
    rolling_36["rolling_36m_vol"] = rolling_36["ret"].rolling(window=36).std(ddof=1) * math.sqrt(12)
    rolling_36["rolling_36m_sharpe"] = roll_mean_36 / rolling_36["rolling_36m_vol"]

    rolling_table = rolling_5y[["date", "rolling_60m_cagr"]].merge(
        rolling_60[["date", "rolling_60m_vol", "rolling_60m_sharpe"]], on="date", how="left"
    ).merge(
        rolling_36[["date", "rolling_36m_sharpe"]], on="date", how="left"
    ).dropna(subset=["rolling_60m_cagr", "rolling_60m_vol", "rolling_60m_sharpe"])

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

    fig3 = plt.figure(figsize=(9, 3.8))
    if not rolling_table.empty:
        plt.plot(rolling_table["date"], rolling_table["rolling_60m_cagr"], lw=2)
    plt.title("Rolling 5Y CAGR (60M window)")
    plt.grid(alpha=0.3)
    rolling5_b64 = fig_to_base64(fig3)

    fig4 = plt.figure(figsize=(9, 3.8))
    if not rolling_table.empty:
        plt.plot(rolling_table["date"], rolling_table["rolling_60m_vol"], lw=2)
    plt.title("Rolling 5Y Volatility (60M window)")
    plt.grid(alpha=0.3)
    rolling_vol_b64 = fig_to_base64(fig4)

    fig5 = plt.figure(figsize=(9, 3.8))
    if not rolling_table.empty:
        plt.plot(rolling_table["date"], rolling_table["rolling_60m_sharpe"], lw=2)
    plt.title("Rolling 5Y Sharpe (rf=0, 60M window)")
    plt.grid(alpha=0.3)
    rolling_sharpe_b64 = fig_to_base64(fig5)

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
            ["Turnover (annualised)", f"{turnover_annualised:.2%}"],
        ],
        columns=["Metric", "Value"],
    )

    reports_dir = Path("../reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    dashboard_name = f"{strategy_slug}.html"
    report_path = reports_dir / dashboard_name

    annual_df = annual_returns.rename("annual_return").to_frame().reset_index()
    annual_df["annual_return"] = annual_df["annual_return"].map(lambda x: f"{x:.2%}")
    def _fmt_pct(x: float) -> str:
        return f"{float(x) * 100:.2f}%"

    monthly_table = pd.DataFrame({
        "date": df["date"].dt.date.astype(str),
        "portfolio_value": df["equity"],
        "monthly_return": df["ret"],
    })
    monthly_table["cumulative_return"] = (1 + monthly_table["monthly_return"]).cumprod() - 1
    weights_for_monthly = weights_df.copy()
    weights_for_monthly["date"] = weights_for_monthly["date"].astype(str)
    for t in tickers:
        if t in weights_for_monthly.columns:
            weights_for_monthly = weights_for_monthly.rename(columns={t: f"weight_{t}"})
    monthly_table = monthly_table.merge(weights_for_monthly, on="date", how="left")

    rolling_metrics_table = rolling_table.copy()
    if not rolling_metrics_table.empty:
        rolling_metrics_table["date"] = pd.to_datetime(rolling_metrics_table["date"]).dt.date.astype(str)

    weights_fmt = weights_df.copy()
    for col in tickers:
        if col in weights_fmt.columns:
            weights_fmt[col] = weights_fmt[col].map(_fmt_pct)

    for col in tickers:
        if col in weights_fmt.columns:
            has_bare_float = weights_fmt[col].map(
                lambda v: isinstance(v, (int, float)) and 0.0 <= float(v) <= 1.0
            ).any()
            if has_bare_float:
                raise AssertionError(f"Unformatted weight cell detected in column {col}")

    def table_html(df_in: pd.DataFrame, numeric_cols: set[str]) -> str:
        cols = list(df_in.columns)
        thead = "".join(f"<th{' class=\"num\"' if c in numeric_cols else ''}>{html.escape(str(c))}</th>" for c in cols)
        body_rows = []
        for _, rw in df_in.iterrows():
            tds = []
            for c in cols:
                cls = " class=\"num\"" if c in numeric_cols else ""
                tds.append(f"<td{cls}>{html.escape(str(rw[c]))}</td>")
            body_rows.append("<tr>" + "".join(tds) + "</tr>")
        return f"<table><thead><tr>{thead}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"

    monthly_fmt = monthly_table.copy()
    monthly_fmt["portfolio_value"] = monthly_fmt["portfolio_value"].map(lambda x: f"{float(x):.2f}")
    monthly_fmt["monthly_return"] = monthly_fmt["monthly_return"].map(_fmt_pct)
    monthly_fmt["cumulative_return"] = monthly_fmt["cumulative_return"].map(_fmt_pct)
    for c in monthly_fmt.columns:
        if c.startswith("weight_"):
            monthly_fmt[c] = monthly_fmt[c].map(lambda x: _fmt_pct(float(x)) if pd.notna(x) else "")

    rolling_fmt = rolling_metrics_table.copy()
    if not rolling_fmt.empty:
        rolling_fmt["rolling_60m_cagr"] = rolling_fmt["rolling_60m_cagr"].map(_fmt_pct)
        rolling_fmt["rolling_60m_vol"] = rolling_fmt["rolling_60m_vol"].map(_fmt_pct)
        rolling_fmt["rolling_60m_sharpe"] = rolling_fmt["rolling_60m_sharpe"].map(lambda x: f"{float(x):.3f}")
        if "rolling_36m_sharpe" in rolling_fmt.columns:
            rolling_fmt["rolling_36m_sharpe"] = rolling_fmt["rolling_36m_sharpe"].map(lambda x: f"{float(x):.3f}" if pd.notna(x) else "")

    metrics_html = table_html(metrics, {"Value"})
    annual_html = table_html(annual_df, {"annual_return"})
    weights_html = table_html(weights_fmt, set(tickers))
    monthly_data_html = table_html(monthly_fmt, {c for c in monthly_fmt.columns if c != "date"})
    rolling_metrics_html = table_html(
        rolling_fmt if not rolling_fmt.empty else pd.DataFrame(columns=["date", "rolling_60m_cagr", "rolling_60m_vol", "rolling_60m_sharpe", "rolling_36m_sharpe"]),
        {"rolling_60m_cagr", "rolling_60m_vol", "rolling_60m_sharpe", "rolling_36m_sharpe"},
    )

    cfg_engine = raw_config.get("engine", {})
    cfg_overlays = raw_config.get("overlays", {})
    cfg_rebalancer = raw_config.get("rebalancer", {})
    cfg_constraints = raw_config.get("constraints", {})
    weights_items = "".join(
        f"<li><span>{html.escape(str(k))}</span><span class='num'>{_fmt_pct(float(v))}</span></li>"
        for k, v in sorted(portfolio["tickers"].items())
    )

    config_snapshot_html = f"""
<div class='config-grid'>
  <div class='cfg-card'><h3>Engine</h3><ul>
    <li><span>Name</span><span>{html.escape(str(cfg_engine.get('name', '')))}</span></li>
    <li><span>Version</span><span>{html.escape(str(cfg_engine.get('version', '')))}</span></li>
  </ul></div>
  <div class='cfg-card'><h3>Strategy</h3><ul>
    <li><span>Name</span><span>{html.escape(strategy_name)}</span></li>
    <li><span>Portfolio File</span><span>{html.escape(portfolio_path.name)}</span></li>
  </ul><h4>Weights</h4><ul>{weights_items}</ul></div>
  <div class='cfg-card'><h3>Overlays</h3><ul>
    <li><span>Risk</span><span>{html.escape(str(cfg_overlays.get('risk', '')))}</span></li>
    <li><span>Regime</span><span>{html.escape(str(cfg_overlays.get('regime', '')))}</span></li>
  </ul></div>
  <div class='cfg-card'><h3>Rebalancer</h3><ul>
    <li><span>Type</span><span>{html.escape(str(cfg_rebalancer.get('type', '')))}</span></li>
  </ul></div>
  <div class='cfg-card'><h3>Constraints</h3><ul>
    <li><span>Leverage</span><span>{html.escape(str(cfg_constraints.get('leverage', '')))}</span></li>
  </ul></div>
</div>
"""

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
<div class='subhead'><b>Tickers:</b> {', '.join(tickers)}<br><b>Date range:</b> {start_date.isoformat()} to {end_date.isoformat()}<br><b>Rebalance rule:</b> {html.escape(rebalance_rule)}<br><b>Transaction cost assumption:</b> {transaction_cost_bps} bps (slippage {slippage_bps} bps)<br><b>Initial capital:</b> {initial_capital:,.2f}</div>
<h2>Config Snapshot</h2>{config_snapshot_html}
<h2>Summary Metrics</h2>{metrics_html}
<h2>Equity Curve</h2><div class='chart'><img src='data:image/png;base64,{equity_b64}' /></div>
<h2>Drawdown</h2><div class='chart'><img src='data:image/png;base64,{dd_b64}' /></div>
<h2>Annual Returns</h2>{annual_html}
<h2>Rolling 5Y CAGR</h2><div class='chart'><img src='data:image/png;base64,{rolling5_b64}' /></div>
<h2>Rolling 5Y Volatility</h2><div class='chart'><img src='data:image/png;base64,{rolling_vol_b64}' /></div>
<h2>Rolling 5Y Sharpe (rf=0)</h2><div class='chart'><img src='data:image/png;base64,{rolling_sharpe_b64}' /></div>
<h2>Monthly Portfolio Data</h2>{monthly_data_html}
<h2>Rolling Metrics (60M window)</h2>{rolling_metrics_html}
<h2>Weight Allocation</h2>{weights_html}
<h2>Methodology</h2>
<ul>
<li>Asset returns: simple close-to-close returns, P_t / P_{{t-1}} - 1.</li>
<li>Rebalancing: engine produces target holdings monthly; trades executed on rebalance months only.</li>
<li>Data source: local canonical dataset from `data/prices_master.parquet` (no network calls).</li>
<li>Assumptions: no taxes, no transaction costs, no slippage, no leverage/borrow modeling beyond engine behavior.</li>
</ul>
</div>
</body></html>
"""
    report_path.write_text(html_report, encoding="utf-8")

    print(f"CONFIG: {portfolio_path}")
    print(f"DATE_RANGE: {start_date.isoformat()} to {end_date.isoformat()}")
    print(
        f"METRICS: total_return={total_return:.6f}, cagr={cagr:.6f}, vol={vol:.6f}, "
        f"sharpe={sharpe:.6f}, max_drawdown={mdd:.6f}, turnover={turnover:.6f}"
    )
    print(f"REPORT_PATH: {report_path}")

    if publish:
        archive_dir = reports_dir / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        ts_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
        archive_name = f"{ts_utc}_{strategy_slug}.html"
        archive_path = archive_dir / archive_name
        archive_path.write_text(html_report, encoding="utf-8")

        git_cmd(["git", "add", str(report_path), str(archive_path)])
        has_staged_changes = subprocess.call(["git", "diff", "--cached", "--quiet"]) != 0
        if not has_staged_changes:
            print("PUBLISH: No changes detected. Skipping commit.")
        else:
            git_cmd(["git", "commit", "-m", f"Add report {dashboard_name}"])
            git_cmd(["git", "push"])
            print("PUBLISH: Report committed and pushed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    run_backtest(strategy=args.strategy, publish=args.publish)
