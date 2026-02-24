from __future__ import annotations

import argparse
import os
import subprocess
import sys
import shutil
from datetime import datetime, timezone
from pathlib import Path

from policy import enforce_head_parity, ensure_timestamped_report_name, report_rows_for_index


def run(cmd: list[str], cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=str(cwd), text=True).strip()


def regenerate_index(repo_root: Path) -> None:
    reports = repo_root / "outputs" / "reports"
    archive = reports / "archive"
    reports.mkdir(parents=True, exist_ok=True)
    archive.mkdir(parents=True, exist_ok=True)

    current_files = sorted([p for p in reports.glob("*.html") if p.name != "index.html"])
    archive_files = sorted([p for p in archive.glob("*.html")])

    current_rows = report_rows_for_index(current_files)
    archive_rows = report_rows_for_index(archive_files)

    def _rows_html(rows: list[tuple[str, str, float, str]], prefix: str = "") -> str:
        if not rows:
            return "<tr><td colspan='4'>No reports found.</td></tr>"
        out = []
        count = len(rows)
        for i, (fname, stem, _, dt) in enumerate(rows):
            n = count - i
            link = f"{prefix}{fname}"
            out.append(f"<tr><td class='num'>{n}</td><td>{stem}</td><td>{dt}</td><td><a href='{link}'>{fname}</a></td></tr>")
        return "\n".join(out)

    current_tbody = _rows_html(current_rows, "")
    archive_tbody = _rows_html(archive_rows, "archive/")

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>MS Report Dashboard</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; margin: 32px auto; max-width: 980px; padding: 0 16px; color: #111; }}
    h1 {{ margin: 0 0 10px; }} h2 {{ margin: 24px 0 10px; }}
    p {{ color: #555; margin: 0 0 16px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 10px; text-align: left; }}
    th {{ background: #f5f5f5; }}
    td.num {{ text-align: left; width: 70px; }}
    a {{ color: #0b57d0; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>MS Report Dashboard</h1>
  <p>Current reports are root-level timestamped files. Archive lists historical versions.</p>
  <h2>Current Reports</h2>
  <table>
    <thead><tr><th>#</th><th>Report Name</th><th>Published (UTC)</th><th>Link</th></tr></thead>
    <tbody>{current_tbody}</tbody>
  </table>
  <h2>Archive</h2>
  <table>
    <thead><tr><th>#</th><th>Report Name</th><th>Published (UTC)</th><th>Link</th></tr></thead>
    <tbody>{archive_tbody}</tbody>
  </table>
</body>
</html>
"""
    (reports / "index.html").write_text(html, encoding="utf-8")


def run_pytest(workspace: Path) -> None:
    env = {**os.environ, "PYTHONPATH": "."}
    rc = subprocess.call([sys.executable, "-m", "pytest", "-q"], cwd=str(workspace), env=env)
    if rc == 0:
        return
    venv_py = workspace / ".venv" / "bin" / "python"
    if venv_py.exists():
        rc = subprocess.call([str(venv_py), "-m", "pytest", "-q"], cwd=str(workspace), env=env)
    if rc != 0:
        raise RuntimeError("Invariant failed: pytest checks must pass before push")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--mode", choices=["capital", "research"], default="capital")
    args = parser.parse_args()

    workspace = Path(__file__).resolve().parents[1]
    repo_root = workspace.parents[1]

    strategy_raw = args.strategy
    strategy = strategy_raw.replace("-", "_")

    if strategy == "sandbox":
        raise RuntimeError("Sandbox cannot be published.")

    portfolio_dir = repo_root / "systems" / args.mode / "portfolios"
    portfolio_path = portfolio_dir / f"{strategy}.yaml"
    if not portfolio_path.exists():
        raise FileNotFoundError(f"Portfolio not found: {portfolio_path}")

    output_dataset_path = workspace / "output" / f"{strategy}.parquet"
    subprocess.check_call(
        [
            sys.executable,
            "backtest.py",
            "--strategy",
            strategy,
            "--output-dataset-path",
            str(output_dataset_path),
            "--mode",
            args.mode,
        ],
        cwd=str(workspace),
        env={**os.environ, "PYTHONPATH": "."},
    )

    portfolio = __import__("yaml").safe_load(portfolio_path.read_text(encoding="utf-8"))
    strategy_slug = str(portfolio.get("name", strategy)).replace("_", "-").lower()
    reports_dir = repo_root / "outputs" / "reports"
    source_path = reports_dir / f"{strategy_slug}.html"
    ts_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    versioned_name = f"{ts_utc}_{strategy_slug}.html"
    ensure_timestamped_report_name(versioned_name, strategy_slug)
    versioned_path = reports_dir / versioned_name

    if not source_path.exists():
        raise FileNotFoundError(f"Expected source report not found: {source_path}")

    archive_dir = reports_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for existing in sorted(reports_dir.glob(f"*_{strategy_slug}.html")):
        if existing.name != versioned_name:
            shutil.move(str(existing), str(archive_dir / existing.name))

    shutil.move(str(source_path), str(versioned_path))

    regenerate_index(repo_root)
    run(["git", "add", "-A"], repo_root)

    has_staged = subprocess.call(["git", "diff", "--cached", "--quiet"], cwd=str(repo_root)) != 0
    if has_staged:
        run_pytest(workspace)
        run(["git", "commit", "-m", f"Publish {strategy} report"], repo_root)
        run(["git", "push", "origin", "main"], repo_root)

    local, remote = enforce_head_parity(repo_root)
    print(f"HEAD_LOCAL: {local}")
    print(f"HEAD_REMOTE: {remote}")
    print("HEAD_MATCH: true")
    print("https://bavvvy.github.io/agent-lab/outputs/reports/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
