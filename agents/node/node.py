from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]


_FORBIDDEN_IDENTITY_STEMS = {"AGENTS", "BOOTSTRAP", "IDENTITY", "SOUL", "TOOLS", "USER", "HEARTBEAT"}


def _assert_root_write_allowed(target: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    t = target.resolve()
    if t.parent.resolve() != repo_root.resolve():
        return

    if t.name != "BOOTSTRAP_EXPORT.txt":
        raise RuntimeError("Root write blocked: immutable root policy.")

    stem = Path(t.name).stem.upper()
    if stem in _FORBIDDEN_IDENTITY_STEMS:
        raise RuntimeError("Root write blocked: immutable root policy.")

try:
    from schema import validate_payload, validate_required_fields
except ModuleNotFoundError:  # package execution path
    from node.schema import validate_payload, validate_required_fields

REQUIRED_FIELDS = [
    "strategy_type",
    "risk_tolerance",
    "leverage_allowed",
    "investment_vehicle",
    "base_currency",
    "time_horizon",
    "liquidity_constraints",
]

ALLOWED_PORTFOLIO_MODES = {"capital", "research"}
METRIC_KEYS = ["total_return", "cagr", "vol", "sharpe", "max_drawdown", "turnover"]


@dataclass
class NodeAgent:
    user_profile: str = "retail"

    def summary(self, current_payload: Dict[str, Any]) -> str:
        missing = validate_required_fields(current_payload)
        assumptions = self._assumptions(current_payload)

        lines = [
            "# Node Summary Preview",
            "",
            f"User profile: {self.user_profile}",
            f"Packaging readiness: {'ready' if not missing else 'not ready'}",
            "",
            "## Extracted Structured Fields",
        ]
        for field in REQUIRED_FIELDS:
            val = current_payload.get(field, "<missing>")
            pretty = json.dumps(val, ensure_ascii=False) if isinstance(val, (dict, list, bool)) else str(val)
            lines.append(f"- {field}: {pretty}")

        lines.extend(["", "## Interpreted Assumptions"])
        if assumptions:
            lines.extend([f"- {a}" for a in assumptions])
        else:
            lines.append("- No assumptions inferred yet.")

        if missing:
            lines.extend(["", "## Clarifications Required"])
            lines.extend([f"- {m}" for m in missing])

        lines.extend([
            "",
            "Preview only. No files written. No machine contract generated.",
        ])
        return "\n".join(lines)

    def package(self, current_payload: Dict[str, Any]) -> Dict[str, Any]:
        errors = validate_payload(current_payload)
        if errors:
            return {
                "status": "refused",
                "reason": "validation_failed",
                "errors": errors,
                "next_step": "Provide missing/invalid fields, then rerun /node package.",
            }

        now = datetime.now(timezone.utc).replace(microsecond=0)
        request_id = f"req_{now.strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:8]}"

        machine_contract = {
            "contract_version": "1.0",
            "contract_type": "allocation_request",
            "origin": "node",
            "request_id": request_id,
            "payload": current_payload,
            "created_at": now.isoformat(),
        }

        assumptions = self._assumptions(current_payload)
        clarifications = self._clarifications_made(current_payload)

        human_brief = self._build_brief_markdown(
            request_id=request_id,
            payload=current_payload,
            assumptions=assumptions,
            clarifications=clarifications,
        )

        repo_root = Path(__file__).resolve().parent.parent
        requests_dir = repo_root / "contracts" / "requests"
        briefs_dir = repo_root / "contracts" / "briefs"
        requests_dir.mkdir(parents=True, exist_ok=True)
        briefs_dir.mkdir(parents=True, exist_ok=True)

        json_path = requests_dir / f"{request_id}.json"
        md_path = briefs_dir / f"{request_id}.md"

        _assert_root_write_allowed(json_path)
        _assert_root_write_allowed(md_path)
        json_path.write_text(json.dumps(machine_contract, indent=2), encoding="utf-8")
        md_path.write_text(human_brief, encoding="utf-8")

        return {
            "status": "created",
            "request_id": request_id,
            "json_path": str(json_path),
            "markdown_path": str(md_path),
            "machine_contract": machine_contract,
            "human_brief_preview": human_brief,
        }

    def run_portfolio(self, *, portfolio_id: str, mode: str) -> Dict[str, Any]:
        repo_root = Path(__file__).resolve().parents[2]
        templates_csv = repo_root / "inputs" / "portfolios" / "portfolio_templates.csv"
        prices_master = repo_root / "data" / "market" / "prices_master.parquet"

        validation_errors: list[str] = []

        if mode not in ALLOWED_PORTFOLIO_MODES:
            validation_errors.append(
                f"Invalid mode '{mode}'. Allowed modes: {', '.join(sorted(ALLOWED_PORTFOLIO_MODES))}."
            )

        if not templates_csv.exists():
            validation_errors.append(f"Missing portfolio template file: {templates_csv}")
        else:
            known_ids = self._load_portfolio_ids(templates_csv)
            if portfolio_id not in known_ids:
                validation_errors.append(
                    f"Unknown portfolio_id '{portfolio_id}'. It is not listed in {templates_csv}."
                )

        if not prices_master.exists():
            validation_errors.append(f"Required market data not found: {prices_master}")

        if validation_errors:
            return {
                "status": "refused",
                "reason": "validation_failed",
                "errors": validation_errors,
                "execution_attempted": False,
            }

        scientist_dir = repo_root / "agents" / "scientist"
        cmd = [
            ".venv/bin/python",
            "cli/backtest.py",
            "--strategy",
            portfolio_id,
            "--mode",
            mode,
        ]
        proc = subprocess.run(
            cmd,
            cwd=scientist_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""

        return {
            "status": "completed" if proc.returncode == 0 else "failed",
            "portfolio": portfolio_id,
            "mode": mode,
            "exit_status": proc.returncode,
            "metrics": self._parse_metrics(stdout),
            "output_path": self._parse_output_path(stdout),
            "stdout": stdout,
            "stderr": stderr,
            "timestamp": self._now_local_iso(),
            "execution_attempted": True,
        }

    def _build_brief_markdown(
        self,
        *,
        request_id: str,
        payload: Dict[str, Any],
        assumptions: list[str],
        clarifications: list[str],
    ) -> str:
        lines = [
            f"# Allocation Request Brief — {request_id}",
            "",
            "## Request ID",
            f"`{request_id}`",
            "",
            "## Extracted Inputs",
        ]
        for field in REQUIRED_FIELDS:
            value = payload.get(field)
            pretty = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list, bool)) else str(value)
            lines.append(f"- **{field}**: {pretty}")

        lines.extend(["", "## Interpreted Assumptions"])
        if assumptions:
            lines.extend([f"- {a}" for a in assumptions])
        else:
            lines.append("- None inferred.")

        lines.extend(["", "## Clarifications Made"])
        if clarifications:
            lines.extend([f"- {c}" for c in clarifications])
        else:
            lines.append("- None beyond provided structured payload.")

        lines.extend([
            "",
            "## Execution Instruction",
            f"`/ms execute request_id={request_id}`",
        ])
        return "\n".join(lines)

    def _assumptions(self, payload: Dict[str, Any]) -> list[str]:
        out: list[str] = []
        rt = payload.get("risk_tolerance")
        if rt == "low":
            out.append("Client prioritizes capital stability over return maximization.")
        elif rt in {"high", "very_high"}:
            out.append("Client accepts materially higher volatility for upside potential.")

        if payload.get("leverage_allowed") is False:
            out.append("No leverage mandate inferred.")

        th = payload.get("time_horizon", {}) if isinstance(payload.get("time_horizon"), dict) else {}
        years = th.get("years")
        if isinstance(years, (int, float)) and years >= 10:
            out.append("Long-duration allocation posture is acceptable.")

        return out

    def _clarifications_made(self, payload: Dict[str, Any]) -> list[str]:
        made: list[str] = []
        for field in REQUIRED_FIELDS:
            if field in payload:
                made.append(f"Confirmed {field}.")
        return made

    def _load_portfolio_ids(self, csv_path: Path) -> set[str]:
        out: set[str] = set()
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return out

            id_column = None
            for name in reader.fieldnames:
                normalized = (name or "").strip().lower()
                if normalized in {"portfolio_id", "portfolio", "strategy", "strategy_id", "id"}:
                    id_column = name
                    break

            if not id_column:
                id_column = reader.fieldnames[0]

            for row in reader:
                value = (row.get(id_column) or "").strip()
                if value:
                    out.add(value)
        return out

    def _parse_metrics(self, stdout: str) -> Dict[str, str]:
        metrics: Dict[str, str] = {}
        for raw_line in stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            for key in METRIC_KEYS:
                pattern = rf"(?i)\b{re.escape(key)}\b\s*[:=]\s*([^,|]+)"
                m = re.search(pattern, line)
                if m:
                    metrics[key] = m.group(1).strip()
                    continue
        return metrics

    def _parse_output_path(self, stdout: str) -> str:
        for raw_line in stdout.splitlines()[::-1]:
            line = raw_line.strip()
            if not line:
                continue
            m = re.search(r"(?i)(?:output(?:\s+path)?|saved\s+to|wrote\s+to)\s*[:=]\s*(.+)$", line)
            if m:
                return m.group(1).strip()
            if "outputs/" in line:
                return line
        return "<not reported>"

    def _now_local_iso(self) -> str:
        if ZoneInfo is not None:
            return datetime.now(ZoneInfo("Australia/Brisbane")).replace(microsecond=0).isoformat()
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json_arg(raw: str) -> Dict[str, Any]:
    if not raw:
        return {}
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(prog="/node")
    subparsers = parser.add_subparsers(dest="command", required=True)

    summary_parser = subparsers.add_parser("summary")
    summary_parser.add_argument("--payload", default="{}", help="JSON payload for allocation request")
    summary_parser.add_argument("--profile", choices=["retail", "sophisticated"], default="retail")

    package_parser = subparsers.add_parser("package")
    package_parser.add_argument("--payload", default="{}", help="JSON payload for allocation request")
    package_parser.add_argument("--profile", choices=["retail", "sophisticated"], default="retail")

    run_parser = subparsers.add_parser("run")
    run_subparsers = run_parser.add_subparsers(dest="run_target", required=True)
    run_portfolio_parser = run_subparsers.add_parser("portfolio")
    run_portfolio_parser.add_argument("portfolio_id")
    run_portfolio_parser.add_argument("mode")
    run_portfolio_parser.add_argument("--profile", choices=["retail", "sophisticated"], default="retail")

    args = parser.parse_args()
    agent = NodeAgent(user_profile=getattr(args, "profile", "retail"))

    if args.command == "summary":
        payload = _read_json_arg(args.payload)
        print(agent.summary(payload))
        return 0

    if args.command == "package":
        payload = _read_json_arg(args.payload)
        result = agent.package(payload)
        if result["status"] == "refused":
            print(json.dumps(result, indent=2))
            return 1

        print("FILES_CREATED:")
        print(f"- {result['json_path']}")
        print(f"- {result['markdown_path']}")
        print("\nMACHINE_CONTRACT_PREVIEW:")
        print(json.dumps(result["machine_contract"], indent=2))
        print("\nHUMAN_BRIEF_PREVIEW:")
        print(result["human_brief_preview"])
        return 0

    if args.command == "run" and args.run_target == "portfolio":
        result = agent.run_portfolio(portfolio_id=args.portfolio_id, mode=args.mode)
        if result["status"] == "refused":
            print("RUN SUMMARY")
            print(f"Portfolio: {args.portfolio_id}")
            print(f"Mode: {args.mode}")
            print("Exit status: validation_failed")
            print("Metrics: <not available>")
            print("Output path: <not available>")
            print(f"Timestamp: {agent._now_local_iso()}")
            print("Errors:")
            for err in result["errors"]:
                print(f"- {err}")
            return 1

        print("RUN SUMMARY")
        print(f"Portfolio: {result['portfolio']}")
        print(f"Mode: {result['mode']}")
        print(f"Exit status: {result['exit_status']}")
        metrics = result["metrics"]
        if metrics:
            metrics_str = ", ".join(f"{k}={v}" for k, v in metrics.items())
        else:
            metrics_str = "<not reported>"
        print(f"Metrics: {metrics_str}")
        print(f"Output path: {result['output_path']}")
        print(f"Timestamp: {result['timestamp']}")
        print("\nSTDOUT:")
        print(result["stdout"].rstrip() or "<empty>")
        print("\nSTDERR:")
        print(result["stderr"].rstrip() or "<empty>")
        return 0 if result["exit_status"] == 0 else result["exit_status"]

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
