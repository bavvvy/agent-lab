from __future__ import annotations

import argparse
import base64
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
from templates.report_template import render_strategy_report
from enforcement.io_guard import assert_not_forbidden_identity_root_file, assert_root_write_allowed

_SCIENTIST_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SYSTEMS_ROOT = _REPO_ROOT / "systems"
DATA_PATH = _REPO_ROOT / "data" / "market" / "prices_master.parquet"
PORTFOLIO_TEMPLATES_PATH = _REPO_ROOT / "inputs" / "portfolios" / "portfolio_templates.csv"
PORTFOLIO_WEIGHTS_PATH = _REPO_ROOT / "inputs" / "portfolios" / "portfolio_weights.csv"
PORTFOLIO_METADATA_PATH = _REPO_ROOT / "inputs" / "portfolios" / "portfolio_metadata.csv"
SYMBOL_MAP = {"AGG": "TLT"}


def _resolve_system_mode(mode: str) -> str:
    allowed = {"capital", "research"}
    if mode not in allowed:
        raise ValueError(f"Invalid mode '{mode}'. Allowed: {sorted(allowed)}")
    return mode


def _outputs_mode_root(mode: str) -> Path:
    return _REPO_ROOT / "outputs" / _resolve_system_mode(mode)


def _config_path(mode: str) -> Path:
    return _SYSTEMS_ROOT / _resolve_system_mode(mode) / "config.yaml"


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


def load_portfolio_from_csv(portfolio_id: str, mode: str = "capital") -> tuple[dict, Path]:
    mode = _resolve_system_mode(mode)
    canonical_id = portfolio_id.replace("-", "_")

    if not PORTFOLIO_TEMPLATES_PATH.exists():
        raise FileNotFoundError(f"Missing portfolio templates CSV: {PORTFOLIO_TEMPLATES_PATH}")
    if not PORTFOLIO_WEIGHTS_PATH.exists():
        raise FileNotFoundError(f"Missing portfolio weights CSV: {PORTFOLIO_WEIGHTS_PATH}")

    templates = pd.read_csv(PORTFOLIO_TEMPLATES_PATH)
    weights = pd.read_csv(PORTFOLIO_WEIGHTS_PATH)

    sel = templates[(templates["mode"] == mode) & (templates["portfolio_id"].astype(str).str.replace("-", "_", regex=False) == canonical_id)]
    if sel.empty:
        raise FileNotFoundError(f"Portfolio template not found for portfolio_id '{portfolio_id}' in mode '{mode}'")

    row = sel.iloc[0]
    portfolio_name = str(row["name"])
    rebalance = str(row["rebalance"])

    wsel = weights[(weights["mode"] == mode) & (weights["portfolio_id"].astype(str).str.replace("-", "_", regex=False) == canonical_id)]
    if wsel.empty:
        raise ValueError(f"No weights found for portfolio_id '{portfolio_id}' in mode '{mode}'")

    tickers = {str(r["ticker"]): float(r["weight"]) for _, r in wsel.iterrows()}

    total = float(sum(float(v) for v in tickers.values()))
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"Portfolio weights must sum to 1.0 (got {total})")

    portfolio: dict = {
        "id": str(row["portfolio_id"]),
        "name": portfolio_name,
        "tickers": tickers,
        "rebalance": rebalance,
    }

    if PORTFOLIO_METADATA_PATH.exists():
        meta = pd.read_csv(PORTFOLIO_METADATA_PATH)
        msel = meta[(meta["mode"] == mode) & (meta["portfolio_id"].astype(str).str.replace("-", "_", regex=False) == canonical_id)]
        for _, mr in msel.iterrows():
            key = str(mr["key"])
            value = mr["value"]
            if key == "lookback_years":
                try:
                    value = int(float(value))
                except Exception:
                    pass
            portfolio[key] = value

    return portfolio, PORTFOLIO_TEMPLATES_PATH


def _load_portfolio(strategy: str, mode: str = "capital") -> tuple[dict, Path]:
    return load_portfolio_from_csv(strategy, mode=mode)


def _load_validated_prices(required_columns: list[str]) -> tuple[pd.DataFrame, dict[str, str | int]]:
    if not DATA_PATH.exists():
        raise FileNotFoundError("prices_master.parquet not found. Run inputs/prices/update_prices.py first.")

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


def _simulate_strategy(engine: PortfolioEngine, portfolio: dict, prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, float]:
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

    df = pd.DataFrame({"date": prices.index, "portfolio_value": equity})
    df["monthly_return"] = df["portfolio_value"].pct_change().fillna(0.0)
    weights_df = pd.DataFrame(weight_rows)
    turnover = float(sum(turnover_rows)) if turnover_rows else 0.0
    return df, weights_df, turnover


def _build_canonical_dataset(
    df: pd.DataFrame,
    weights_df: pd.DataFrame,
    strategy_name: str,
    publish_timestamp: str,
    tickers: list[str],
) -> pd.DataFrame:
    base = df.copy()
    base["date"] = pd.to_datetime(base["date"]).dt.date.astype(str)
    base["cumulative_return"] = (1 + base["monthly_return"]).cumprod() - 1

    weights = weights_df.copy()
    for t in tickers:
        if t in weights.columns:
            weights = weights.rename(columns={t: f"weight_{t}"})

    merged = base.merge(weights, on="date", how="left")

    pv = merged["portfolio_value"].to_list()
    rolling_cagr = [float("nan")] * len(pv)
    for i in range(60, len(pv)):
        rolling_cagr[i] = (pv[i] / pv[i - 60]) ** (1 / 5) - 1
    merged["rolling_60m_cagr"] = rolling_cagr

    roll_std = merged["monthly_return"].rolling(window=60).std(ddof=1) * math.sqrt(12)
    roll_mean = merged["monthly_return"].rolling(window=60).mean() * 12
    merged["rolling_60m_vol"] = roll_std
    merged["rolling_60m_sharpe"] = roll_mean / roll_std

    merged["strategy_name"] = strategy_name
    merged["publish_timestamp"] = publish_timestamp

    weight_cols = sorted([c for c in merged.columns if c.startswith("weight_")])
    ordered = [
        "date",
        "portfolio_value",
        "monthly_return",
        "cumulative_return",
        "rolling_60m_cagr",
        "rolling_60m_vol",
        "rolling_60m_sharpe",
    ] + weight_cols + ["strategy_name", "publish_timestamp"]

    return merged[ordered]


def run_backtest(strategy: str, publish: bool = False, output_dataset_path: str | None = None, mode: str = "capital") -> None:
    config_path = _config_path(mode)
    with open(config_path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)
    engine = PortfolioEngine.from_yaml(str(config_path))

    portfolio, portfolio_path = _load_portfolio(strategy, mode=mode)
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
    transaction_cost_bps = 0
    slippage_bps = 0
    rebalance_rule = str(portfolio.get("rebalance", "monthly"))
    publish_ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    df, weights_df, turnover = _simulate_strategy(engine, portfolio, prices)
    canonical = _build_canonical_dataset(df, weights_df, strategy_name, publish_ts, tickers)

    if output_dataset_path:
        out_path = Path(output_dataset_path)
        assert_root_write_allowed(out_path)
        assert_not_forbidden_identity_root_file(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        canonical.to_parquet(out_path, index=False)

        csv_path = out_path.with_suffix(".csv")
        assert_root_write_allowed(csv_path)
        assert_not_forbidden_identity_root_file(csv_path)
        canonical.to_csv(csv_path, index=False, float_format="%.10f")

        print(f"CANONICAL_DATASET_PATH: {out_path}")
        print(f"CANONICAL_DATASET_CSV_PATH: {csv_path}")

    monthly = canonical.copy()
    years = len(monthly.iloc[1:]) / 12
    total_return = float(monthly["portfolio_value"].iloc[-1] / monthly["portfolio_value"].iloc[0] - 1)
    cagr = float((1 + total_return) ** (1 / years) - 1) if years > 0 else 0.0
    vol = ann_std(monthly["monthly_return"].iloc[1:])
    sharpe = float((monthly["monthly_return"].iloc[1:].mean() * 12) / vol) if vol > 0 else 0.0
    mdd = max_drawdown(monthly["portfolio_value"])

    monthly_nonzero = monthly.iloc[1:].copy()
    best_idx = monthly_nonzero["monthly_return"].idxmax()
    worst_idx = monthly_nonzero["monthly_return"].idxmin()
    best_month = str(monthly.loc[best_idx, "date"])
    worst_month = str(monthly.loc[worst_idx, "date"])
    pct_pos = float((monthly_nonzero["monthly_return"] > 0).mean()) if len(monthly_nonzero) else 0.0
    turnover_annualised = (turnover / len(monthly_nonzero)) * 12 if len(monthly_nonzero) > 0 else 0.0

    annual_returns = (
        monthly_nonzero.assign(year=pd.to_datetime(monthly_nonzero["date"]).dt.year)
        .groupby("year")["monthly_return"]
        .apply(lambda x: (1 + x).prod() - 1)
        .reset_index(name="annual_return")
    )

    fig1 = plt.figure(figsize=(9, 4))
    plt.plot(pd.to_datetime(monthly["date"]), monthly["portfolio_value"], lw=2)
    plt.title("Equity Curve")
    plt.grid(alpha=0.3)
    equity_b64 = fig_to_base64(fig1)

    dd = monthly["portfolio_value"] / monthly["portfolio_value"].cummax() - 1.0
    fig2 = plt.figure(figsize=(9, 3.5))
    plt.plot(pd.to_datetime(monthly["date"]), dd, color="crimson", lw=2)
    plt.title("Drawdown")
    plt.grid(alpha=0.3)
    drawdown_b64 = fig_to_base64(fig2)

    def _fmt_pct(x: float) -> str:
        return f"{float(x) * 100:.2f}%"

    metrics = pd.DataFrame(
        [
            ["Total return", f"{total_return:.2%}"],
            ["CAGR", f"{cagr:.2%}"],
            ["Volatility", f"{vol:.2%}"],
            ["Sharpe (rf=0)", f"{sharpe:.3f}"],
            ["Max drawdown", f"{mdd:.2%}"],
            ["Best month", f"{best_month} ({monthly.loc[best_idx, 'monthly_return']:.2%})"],
            ["Worst month", f"{worst_month} ({monthly.loc[worst_idx, 'monthly_return']:.2%})"],
            ["% positive months", f"{pct_pos:.2%}"],
            ["Turnover (annualised)", f"{turnover_annualised:.2%}"],
        ],
        columns=["Metric", "Value"],
    )

    weight_cols = [c for c in canonical.columns if c.startswith("weight_")]
    monthly_display = monthly[["date", "portfolio_value", "monthly_return", "cumulative_return", *weight_cols]].copy()
    monthly_display["portfolio_value"] = monthly_display["portfolio_value"].map(lambda x: f"{float(x):.2f}")
    monthly_display["monthly_return"] = monthly_display["monthly_return"].map(_fmt_pct)
    monthly_display["cumulative_return"] = monthly_display["cumulative_return"].map(_fmt_pct)
    for c in weight_cols:
        monthly_display[c] = monthly_display[c].map(lambda x: _fmt_pct(float(x)) if pd.notna(x) else "")

    weight_alloc = pd.DataFrame(
        {
            "Ticker": [t for t in tickers],
            "Weight": [_fmt_pct(float(portfolio["tickers"][t])) for t in tickers],
        }
    )

    annual_display = annual_returns.copy()
    annual_display["annual_return"] = annual_display["annual_return"].map(lambda x: f"{x:.2%}")

    cfg_engine = raw_config.get("engine", {})
    cfg_overlays = raw_config.get("overlays", {})
    cfg_rebalancer = raw_config.get("rebalancer", {})
    cfg_constraints = raw_config.get("constraints", {})

    runs_dir = _outputs_mode_root(mode) / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    report_path = runs_dir / f"{strategy_slug}.html"

    html_report = render_strategy_report(
        strategy_name=strategy_name,
        tickers=tickers,
        start_date=str(start_date),
        end_date=str(end_date),
        rebalance_rule=rebalance_rule,
        transaction_cost_bps=transaction_cost_bps,
        slippage_bps=slippage_bps,
        initial_capital=10000.0,
        engine_name=str(cfg_engine.get("name", "")),
        engine_version=str(cfg_engine.get("version", "")),
        portfolio_file=portfolio_path.name,
        overlays=cfg_overlays,
        rebalancer=cfg_rebalancer,
        constraints=cfg_constraints,
        weights=portfolio["tickers"],
        metrics_df=metrics,
        annual_returns_df=annual_display,
        weight_alloc_df=weight_alloc,
        monthly_data_df=monthly_display,
        equity_chart_b64=equity_b64,
        drawdown_chart_b64=drawdown_b64,
    )

    assert_root_write_allowed(report_path)
    assert_not_forbidden_identity_root_file(report_path)
    report_path.write_text(html_report, encoding="utf-8")

    print(f"CONFIG: {portfolio_path}")
    print(f"DATE_RANGE: {start_date} to {end_date}")
    print(
        f"METRICS: total_return={total_return:.6f}, cagr={cagr:.6f}, vol={vol:.6f}, "
        f"sharpe={sharpe:.6f}, max_drawdown={mdd:.6f}, turnover={turnover:.6f}"
    )
    print(f"REPORT_PATH: {report_path}")

    if publish:
        archive_dir = _outputs_mode_root(mode) / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        ts_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
        archive_path = archive_dir / f"{ts_utc}_{strategy_slug}.html"
        assert_root_write_allowed(archive_path)
        assert_not_forbidden_identity_root_file(archive_path)
        archive_path.write_text(html_report, encoding="utf-8")

        git_cmd(["git", "add", str(report_path), str(archive_path)])
        has_staged_changes = subprocess.call(["git", "diff", "--cached", "--quiet"]) != 0
        if not has_staged_changes:
            print("PUBLISH: No changes detected. Skipping commit.")
        else:
            git_cmd(["git", "commit", "-m", f"Add report {strategy_slug}.html"])
            git_cmd(["git", "push"])
            print("PUBLISH: Report committed and pushed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--output-dataset-path", default=None)
    parser.add_argument("--mode", choices=["capital", "research"], default="capital")
    args = parser.parse_args()
    run_backtest(strategy=args.strategy, publish=args.publish, output_dataset_path=args.output_dataset_path, mode=args.mode)
