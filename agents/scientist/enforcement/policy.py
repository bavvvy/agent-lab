from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

TIMESTAMPED_REPORT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2})_(.+)\.html$")


def parse_report_timestamp_utc(filename: str) -> datetime | None:
    m = TIMESTAMPED_REPORT_RE.match(filename)
    if not m:
        return None
    return datetime.strptime(f"{m.group(1)}_{m.group(2)}", "%Y-%m-%d_%H-%M").replace(tzinfo=timezone.utc)


def ensure_timestamped_report_name(filename: str, strategy_slug: str) -> None:
    m = TIMESTAMPED_REPORT_RE.match(filename)
    if not m:
        raise ValueError("Report filename must match YYYY-MM-DD_HH-MM_<strategy>.html")
    if m.group(3) != strategy_slug:
        raise ValueError(f"Report strategy slug mismatch: expected {strategy_slug}, got {m.group(3)}")


def report_rows_for_index(report_files: list[Path]) -> list[tuple[str, str, float, str]]:
    rows: list[tuple[str, str, float, str]] = []
    for p in report_files:
        parsed = parse_report_timestamp_utc(p.name)
        if parsed is None:
            rows.append((p.name, p.stem, float("-inf"), "Legacy"))
        else:
            rows.append((p.name, p.stem, parsed.timestamp(), parsed.strftime("%Y-%m-%d %H:%M UTC")))
    rows.sort(key=lambda x: x[2], reverse=True)
    return rows


def enforce_head_parity(repo_root: Path) -> tuple[str, str]:
    local = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo_root), text=True).strip()
    remote = subprocess.check_output(["git", "rev-parse", "origin/main"], cwd=str(repo_root), text=True).strip()
    if local != remote:
        raise RuntimeError("HEAD parity invariant failed: local HEAD != origin/main")
    return local, remote
