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


def fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _load_strategy_frame(workspace: Path, strategy_arg: str) -> tuple[str, pd.DataFrame]:
    portfolio, _ = bt._load_portfolio(strategy_arg)
    name = str(portfolio["name"])
    dataset_path = workspace / "output" / f"{strategy_arg}.parquet"
    if not dataset_path.exists():
        raise FileNotFoundError(f"Canonical dataset missing: {dataset_path}")

    df = pd.read_parquet(dataset_path)
    required = {
        "date",
        "portfolio_value",
        "monthly_return",
        "cumulative_return",
        "rolling_60m_cagr",
        "rolling_60m_vol",
        "rolling_60m_sharpe",
        "strategy_name",
        "publish_timestamp",
    }
    if not required.issubset(set(df.columns)):
        raise ValueError(f"Dataset schema mismatch for {dataset_path}")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return name, df


def _max_drawdown(series: pd.Series) -> float:
    dd = series / series.cummax() - 1.0
    return float(dd.min())


def _full_period_metrics(df: pd.DataFrame) -> dict[str, float]:
    monthly = df["monthly_return"].astype(float)
    n_months = max(len(monthly) - 1, 1)
    years = n_months / 12

    total_return = float(df["portfolio_value"].iloc[-1] / df["portfolio_value"].iloc[0] - 1)
    cagr = float((1 + total_return) ** (1 / years) - 1) if years > 0 else 0.0
    vol = float(monthly.iloc[1:].std(ddof=1) * math.sqrt(12)) if len(monthly) > 2 else 0.0
    sharpe = float((monthly.iloc[1:].mean() * 12) / vol) if vol > 0 else 0.0
    max_dd = _max_drawdown(df["portfolio_value"].astype(float))
    calmar = float(cagr / abs(max_dd)) if max_dd < 0 else 0.0
    pct_pos = float((monthly.iloc[1:] > 0).mean()) if len(monthly) > 1 else 0.0

    worst_12m = float(((1 + monthly).rolling(12).apply(lambda x: x.prod(), raw=False) - 1).min())
    worst_36m = float(((1 + monthly).rolling(36).apply(lambda x: x.prod(), raw=False) - 1).min())

    return {
        "CAGR": cagr,
        "Volatility": vol,
        "Sharpe": sharpe,
        "Max Drawdown": max_dd,
        "Calmar": calmar,
        "% Positive Months": pct_pos,
        "Worst 12M Return": worst_12m,
        "Worst 36M Return": worst_36m,
    }


def _drawdown_diagnostics(df: pd.DataFrame) -> dict[str, float]:
    eq = df["portfolio_value"].astype(float)
    peak = eq.cummax()
    dd = eq / peak - 1.0

    max_duration = 0
    cur = 0
    for v in dd:
        if v < 0:
            cur += 1
            max_duration = max(max_duration, cur)
        else:
            cur = 0

    max_recovery = 0
    i = 0
    n = len(eq)
    while i < n:
        if dd.iloc[i] < 0:
            j = i
            while j < n and dd.iloc[j] < 0:
                j += 1
            max_recovery = max(max_recovery, j - i)
            i = j
        else:
            i += 1

    return {
        "Max Drawdown Duration (months)": float(max_duration),
        "Max Recovery Time (months)": float(max_recovery),
    }


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.2f}%"


def _table_html(df: pd.DataFrame, numeric_cols: set[str]) -> str:
    cols = list(df.columns)
    th = "".join([f"<th{' class=\"num\"' if c in numeric_cols else ''}>{c}</th>" for c in cols])
    rows = []
    for _, r in df.iterrows():
        tds = "".join([f"<td{' class=\"num\"' if c in numeric_cols else ''}>{r[c]}</td>" for c in cols])
        rows.append(f"<tr>{tds}</tr>")
    return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", action="append", required=True)
    args = parser.parse_args()

    if len(args.strategy) < 2:
        raise ValueError("Provide at least two --strategy values")

    workspace = Path(__file__).resolve().parent
    reports_dir = workspace.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    names: list[str] = []
    frames: dict[str, pd.DataFrame] = {}

    for s in args.strategy:
        name, df = _load_strategy_frame(workspace, s)
        names.append(name)
        frames[name] = df

    a, b = names[0], names[1]
    dfa, dfb = frames[a], frames[b]

    full_rows = []
    for name, df in frames.items():
        m = _full_period_metrics(df)
        ddx = _drawdown_diagnostics(df)
        full_rows.append(
            {
                "Strategy": name,
                "CAGR": _fmt_pct(m["CAGR"]),
                "Volatility": _fmt_pct(m["Volatility"]),
                "Sharpe": f"{m['Sharpe']:.3f}",
                "Max Drawdown": _fmt_pct(m["Max Drawdown"]),
                "Calmar": f"{m['Calmar']:.3f}",
                "% Positive Months": _fmt_pct(m["% Positive Months"]),
                "Worst 12M Return": _fmt_pct(m["Worst 12M Return"]),
                "Worst 36M Return": _fmt_pct(m["Worst 36M Return"]),
                "Max DD Duration (m)": f"{ddx['Max Drawdown Duration (months)']:.0f}",
                "Max Recovery (m)": f"{ddx['Max Recovery Time (months)']:.0f}",
            }
        )

    merged = pd.merge(
        dfa[["date", "monthly_return", "rolling_60m_cagr", "rolling_60m_vol", "rolling_60m_sharpe"]],
        dfb[["date", "monthly_return", "rolling_60m_cagr", "rolling_60m_vol", "rolling_60m_sharpe"]],
        on="date",
        suffixes=("_a", "_b"),
        how="inner",
    )

    merged_roll = merged.dropna(subset=["rolling_60m_cagr_a", "rolling_60m_cagr_b", "rolling_60m_sharpe_a", "rolling_60m_sharpe_b"])
    pct_cagr_out = float((merged_roll["rolling_60m_cagr_a"] > merged_roll["rolling_60m_cagr_b"]).mean()) if not merged_roll.empty else float("nan")
    pct_sharpe_out = float((merged_roll["rolling_60m_sharpe_a"] > merged_roll["rolling_60m_sharpe_b"]).mean()) if not merged_roll.empty else float("nan")

    corr = float(merged["monthly_return_a"].corr(merged["monthly_return_b"]))
    avg_roll_vol = (merged["rolling_60m_vol_a"] + merged["rolling_60m_vol_b"]) / 2
    q75 = avg_roll_vol.quantile(0.75)

    high_vol = merged[avg_roll_vol >= q75]
    rising_vol = merged[avg_roll_vol.diff() > 0]
    falling_equity = merged[merged["monthly_return_b"] < 0]

    def _regime_row(label: str, df: pd.DataFrame) -> dict[str, str]:
        if df.empty:
            return {"Regime": label, a: "N/A", b: "N/A", f"{a} - {b}": "N/A"}
        ra = float(df["monthly_return_a"].mean())
        rb = float(df["monthly_return_b"].mean())
        return {"Regime": label, a: _fmt_pct(ra), b: _fmt_pct(rb), f"{a} - {b}": _fmt_pct(ra - rb)}

    regime_rows = [
        _regime_row("High vol periods", high_vol),
        _regime_row("Rising vol periods", rising_vol),
        _regime_row("Falling equity periods", falling_equity),
    ]

    dist_rows = []
    for name, df in frames.items():
        s = df["monthly_return"].iloc[1:]
        dist_rows.append({"Strategy": name, "Skewness": f"{float(s.skew()):.3f}", "Kurtosis": f"{float(s.kurt()):.3f}"})

    fig1 = plt.figure(figsize=(10, 4))
    plt.plot(merged_roll["date"], merged_roll["rolling_60m_cagr_a"], lw=2, label=a)
    plt.plot(merged_roll["date"], merged_roll["rolling_60m_cagr_b"], lw=2, label=b)
    plt.title("Rolling 60M CAGR Comparison")
    plt.grid(alpha=0.3)
    if plt.gca().lines:
        plt.legend()
    cagr_b64 = fig_to_base64(fig1)

    fig2 = plt.figure(figsize=(10, 4))
    plt.plot(merged_roll["date"], merged_roll["rolling_60m_vol_a"], lw=2, label=a)
    plt.plot(merged_roll["date"], merged_roll["rolling_60m_vol_b"], lw=2, label=b)
    plt.title("Rolling 60M Volatility Comparison")
    plt.grid(alpha=0.3)
    if plt.gca().lines:
        plt.legend()
    vol_b64 = fig_to_base64(fig2)

    fig3 = plt.figure(figsize=(10, 4))
    plt.plot(merged_roll["date"], merged_roll["rolling_60m_sharpe_a"], lw=2, label=a)
    plt.plot(merged_roll["date"], merged_roll["rolling_60m_sharpe_b"], lw=2, label=b)
    plt.title("Rolling 60M Sharpe Comparison")
    plt.grid(alpha=0.3)
    if plt.gca().lines:
        plt.legend()
    sharpe_b64 = fig_to_base64(fig3)

    fig4 = plt.figure(figsize=(10, 4))
    plt.hist(dfa["monthly_return"].iloc[1:], bins=30, alpha=0.5, label=a, density=True)
    plt.hist(dfb["monthly_return"].iloc[1:], bins=30, alpha=0.5, label=b, density=True)
    plt.title("Monthly Return Distribution Overlay")
    plt.grid(alpha=0.3)
    plt.legend()
    dist_b64 = fig_to_base64(fig4)

    full_df = pd.DataFrame(full_rows)
    rolling_summary = pd.DataFrame(
        [
            {"Metric": f"% periods {a} > {b} (Rolling CAGR)", "Value": _fmt_pct(pct_cagr_out) if pd.notna(pct_cagr_out) else "N/A"},
            {"Metric": f"% periods {a} > {b} (Rolling Sharpe)", "Value": _fmt_pct(pct_sharpe_out) if pd.notna(pct_sharpe_out) else "N/A"},
            {"Metric": "Strategy correlation (monthly returns)", "Value": f"{corr:.3f}" if pd.notna(corr) else "N/A"},
        ]
    )

    regime_df = pd.DataFrame(regime_rows)
    dist_df = pd.DataFrame(dist_rows)

    conclusion = [
        f"{a} compounds better." if _full_period_metrics(dfa)["CAGR"] > _full_period_metrics(dfb)["CAGR"] else f"{b} compounds better.",
        f"{a} manages drawdowns better." if _full_period_metrics(dfa)["Max Drawdown"] > _full_period_metrics(dfb)["Max Drawdown"] else f"{b} manages drawdowns better.",
        f"{a} is more risk-efficient." if _full_period_metrics(dfa)["Sharpe"] > _full_period_metrics(dfb)["Sharpe"] else f"{b} is more risk-efficient.",
        f"Trade-off: higher protection vs higher upside depends on regime transitions.",
    ]

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    out_path = reports_dir / f"{ts}_comparison.html"

    html_doc = f"""<html><head><meta charset='utf-8'><title>Comparison Report</title>
<style>body{{font-family:Arial,sans-serif;max-width:1100px;margin:28px auto;padding:0 16px}}table{{border-collapse:collapse;width:100%;margin:10px 0}}th,td{{border:1px solid #ddd;padding:8px;text-align:left}}th{{background:#f3f4f6}}td.num{{text-align:right}}img{{width:100%;height:auto;border:1px solid #ddd;border-radius:8px}}</style>
</head><body>
<h1>Comparative Analytics Report</h1>
<p><b>Strategies:</b> {a}, {b}</p>
<h2>Full-period comparison</h2>{_table_html(full_df, {'CAGR','Volatility','Sharpe','Max Drawdown','Calmar','% Positive Months','Worst 12M Return','Worst 36M Return','Max DD Duration (m)','Max Recovery (m)'})}
<h2>Rolling 60M CAGR comparison</h2><img src='data:image/png;base64,{cagr_b64}' />
<h2>Rolling 60M Volatility comparison</h2><img src='data:image/png;base64,{vol_b64}' />
<h2>Rolling 60M Sharpe comparison</h2><img src='data:image/png;base64,{sharpe_b64}' />
{_table_html(rolling_summary, {'Value'})}
<h2>Regime insight</h2>{_table_html(regime_df, {a,b,f'{a} - {b}'})}
<h2>Distribution diagnostics</h2><img src='data:image/png;base64,{dist_b64}' />
{_table_html(dist_df, {'Skewness','Kurtosis'})}
<h2>Conclusion</h2><ul>{''.join(f'<li>{c}</li>' for c in conclusion)}</ul>
</body></html>"""

    out_path.write_text(html_doc, encoding="utf-8")
    print(f"COMPARISON_REPORT_PATH: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
