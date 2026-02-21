from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=str(cwd), text=True).strip()


def regenerate_index(repo_root: Path) -> None:
    reports = repo_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    files = sorted([p for p in reports.glob("*.html") if p.name != "index.html"])
    rows = []
    for p in files:
        ts = run(["git", "log", "-1", "--format=%ct", "--", str(p.relative_to(repo_root))], repo_root)
        epoch = int(ts) if ts else 0
        dt = datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if epoch else "N/A"
        rows.append((p.name, p.stem, epoch, dt))
    rows.sort(key=lambda x: x[2], reverse=True)
    count = len(rows)

    body = []
    for i, (fname, stem, _, dt) in enumerate(rows):
        n = count - i
        body.append(f"<tr><td class='num'>{n}</td><td>{stem}</td><td>{dt}</td><td><a href='{fname}'>{fname}</a></td></tr>")
    tbody = "\n".join(body) if body else "<tr><td colspan='4'>No reports found.</td></tr>"

    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>MS Report Dashboard</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, Arial, sans-serif; margin: 32px auto; max-width: 980px; padding: 0 16px; color: #111; }}
    h1 {{ margin: 0 0 10px; }}
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
  <p>Reports sorted by latest git commit timestamp (UTC), newest first.</p>
  <table>
    <thead><tr><th>#</th><th>Report Name</th><th>Published (UTC)</th><th>Link</th></tr></thead>
    <tbody>{tbody}</tbody>
  </table>
</body>
</html>
"""
    (reports / "index.html").write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", required=True)
    args = parser.parse_args()

    workspace = Path(__file__).resolve().parent
    repo_root = workspace.parent

    # Current engine/backtest supports one deterministic strategy path.
    if args.strategy != "beta_engine_60_40":
        print(f"Unsupported strategy: {args.strategy}. Supported: beta_engine_60_40")
        return 2

    subprocess.check_call([sys.executable, "backtest.py"], cwd=str(workspace), env={**os.environ, "PYTHONPATH": "."})

    regenerate_index(repo_root)

    run(["git", "add", "-A"], repo_root)
    has_staged = subprocess.call(["git", "diff", "--cached", "--quiet"], cwd=str(repo_root)) != 0
    if has_staged:
        run(["git", "commit", "-m", f"Publish {args.strategy} report"], repo_root)
        run(["git", "push", "origin", "main"], repo_root)

    local = run(["git", "rev-parse", "HEAD"], repo_root)
    remote = run(["git", "ls-remote", "--heads", "origin", "main"], repo_root).split()[0]
    print(f"HEAD_LOCAL: {local}")
    print(f"HEAD_REMOTE: {remote}")
    print(f"HEAD_MATCH: {str(local == remote).lower()}")
    print("https://bavvvy.github.io/agent-lab/reports/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
