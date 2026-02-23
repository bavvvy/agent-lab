from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4


def _assert_root_write_allowed(target: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    t = target.resolve()
    if t.parent.resolve() == repo_root.resolve() and t.name != "BOOTSTRAP_EXPORT.txt":
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


def _read_json_arg(raw: str) -> Dict[str, Any]:
    if not raw:
        return {}
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(prog="/node")
    parser.add_argument("command", choices=["summary", "package"])
    parser.add_argument("--payload", default="{}", help="JSON payload for allocation request")
    parser.add_argument("--profile", choices=["retail", "sophisticated"], default="retail")
    args = parser.parse_args()

    payload = _read_json_arg(args.payload)
    agent = NodeAgent(user_profile=args.profile)

    if args.command == "summary":
        print(agent.summary(payload))
        return 0

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


if __name__ == "__main__":
    raise SystemExit(main())
