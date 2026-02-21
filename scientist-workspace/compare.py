from __future__ import annotations

import argparse
import base64
import io
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


def _pct_to_float(x: str) -> float:
    return float(str(x).replace("%", "")) / 100.0


def _read_rolling_table(dataset_path: Path) -> pd.DataFrame:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Canonical dataset missing: {dataset_path}")
    out = pd.read_parquet(dataset_path)
    required = {"date", "rolling_60m_cagr", "rolling_60m_vol", "rolling_60m_sharpe"}
    if not required.issubset(set(out.columns)):
        raise ValueError(f"Rolling metrics columns missing in canonical dataset: {dataset_path}")
    out = out[["date", "rolling_60m_cagr", "rolling_60m_vol", "rolling_60m_sharpe"] + (["rolling_36m_sharpe"] if "rolling_36m_sharpe" in out.columns else [])].copy()
    out["date"] = pd.to_datetime(out["date"])
    out["rolling_60m_cagr"] = pd.to_numeric(out["rolling_60m_cagr"], errors="coerce")
    out["rolling_60m_vol"] = pd.to_numeric(out["rolling_60m_vol"], errors="coerce")
    out["rolling_60m_sharpe"] = pd.to_numeric(out["rolling_60m_sharpe"], errors="coerce")
    if "rolling_36m_sharpe" in out.columns:
        out["rolling_36m_sharpe"] = pd.to_numeric(out["rolling_36m_sharpe"], errors="coerce")
    else:
        out["rolling_36m_sharpe"] = float("nan")
    return out.dropna(subset=["rolling_60m_cagr", "rolling_60m_vol", "rolling_60m_sharpe"])


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--strategy", action="append", required=True)
    args = p.parse_args()

    workspace = Path(__file__).resolve().parent
    reports_dir = workspace.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    roll_by_name: dict[str, pd.DataFrame] = {}
    summary_rows = []

    for s in args.strategy:
        portfolio, _ = bt._load_portfolio(s)
        name = str(portfolio["name"])
        dataset_path = workspace / "output" / f"{s}.parquet"
        roll = _read_rolling_table(dataset_path)
        roll_by_name[name] = roll

        mean_5y = roll["rolling_60m_cagr"].mean() if not roll.empty else float("nan")
        mean_3y_sharpe = roll["rolling_36m_sharpe"].mean() if not roll.empty else float("nan")
        summary_rows.append(
            {
                "Strategy": name,
                "Mean 5Y CAGR": f"{mean_5y:.2%}" if pd.notna(mean_5y) else "N/A",
                "Mean 3Y Sharpe": f"{mean_3y_sharpe:.3f}" if pd.notna(mean_3y_sharpe) else "N/A",
            }
        )

    fig1 = plt.figure(figsize=(10, 4))
    for name, d in roll_by_name.items():
        if not d.empty:
            plt.plot(d["date"], d["rolling_60m_cagr"], lw=2, label=name)
    plt.title("Rolling 5Y CAGR Comparison")
    plt.grid(alpha=0.3)
    if plt.gca().lines:
        plt.legend()
    cagr_b64 = fig_to_base64(fig1)

    fig2 = plt.figure(figsize=(10, 4))
    for name, d in roll_by_name.items():
        z = d.dropna(subset=["rolling_36m_sharpe"])
        if not z.empty:
            plt.plot(z["date"], z["rolling_36m_sharpe"], lw=2, label=name)
    plt.title("Rolling 3Y Sharpe Comparison (rf=0)")
    plt.grid(alpha=0.3)
    if plt.gca().lines:
        plt.legend()
    sharpe_b64 = fig_to_base64(fig2)

    pair_line = "N/A"
    if len(args.strategy) >= 2:
        p1, _ = bt._load_portfolio(args.strategy[0])
        p2, _ = bt._load_portfolio(args.strategy[1])
        n1, n2 = str(p1["name"]), str(p2["name"])
        m = pd.merge(roll_by_name[n1][["date", "rolling_60m_cagr"]], roll_by_name[n2][["date", "rolling_60m_cagr"]], on="date", how="inner", suffixes=("_a", "_b"))
        if not m.empty:
            pair_line = f"{n1} > {n2}: {(m['rolling_60m_cagr_a'] > m['rolling_60m_cagr_b']).mean():.2%}"

    summary_html = pd.DataFrame(summary_rows).to_html(index=False)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    out_path = reports_dir / f"comparison_{ts}.html"
    out_path.write_text(
        f"""<html><head><meta charset='utf-8'><title>Comparison Report</title>
<style>body{{font-family:Arial,sans-serif;max-width:1100px;margin:28px auto;padding:0 16px}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ddd;padding:8px}}th{{background:#f3f4f6}}img{{width:100%;height:auto;border:1px solid #ddd;border-radius:8px}}</style>
</head><body>
<h1>Strategy Comparison Report</h1>
<p><b>Strategies:</b> {', '.join(args.strategy)}</p>
<h2>Rolling 5Y CAGR Comparison</h2><img src='data:image/png;base64,{cagr_b64}' />
<h2>Rolling 3Y Sharpe Comparison</h2><img src='data:image/png;base64,{sharpe_b64}' />
<h2>Summary</h2>{summary_html}
<p><b>% periods strategy A &gt; strategy B:</b> {pair_line}</p>
</body></html>""",
        encoding="utf-8",
    )
    print(f"COMPARISON_REPORT_PATH: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
