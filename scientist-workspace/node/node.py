from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any, Dict, List

from schema import ALLOCATION_REQUEST_SCHEMA, validate_required_fields


REQUIRED_ORDER = [
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
    """Node: outward-facing intake and translation layer.

    Constraints enforced by design:
    - Stateless by default (operates on passed payload only)
    - Does not run backtests
    - Does not mutate strategy logic
    - Outputs structured JSON payloads for MS
    """

    user_profile: str = "retail"

    def gather(self, current_payload: Dict[str, Any]) -> Dict[str, Any]:
        missing = validate_required_fields(current_payload)
        questions = [self._question_for(field) for field in REQUIRED_ORDER if field in missing]
        return {
            "module": "node",
            "action": "gather",
            "user_profile": self.user_profile,
            "missing_fields": missing,
            "clarifying_questions": questions,
            "ready_for_package": len(missing) == 0,
        }

    def package(self, current_payload: Dict[str, Any]) -> Dict[str, Any]:
        missing = validate_required_fields(current_payload)
        if missing:
            return {
                "module": "node",
                "action": "package",
                "status": "incomplete",
                "missing_fields": missing,
                "message": "Allocation request is incomplete. Run /node gather.",
            }

        return {
            "module": "node",
            "action": "package",
            "status": "ready",
            "schema_id": ALLOCATION_REQUEST_SCHEMA["$id"],
            "allocation_request": current_payload,
            "handoff_target": "ms",
            "guarantees": {
                "no_backtest_executed": True,
                "no_strategy_logic_change": True,
                "no_portfolio_engine_modification": True,
            },
        }

    def explain(self, ms_result: Dict[str, Any]) -> str:
        summary = ms_result.get("summary", "MS result received.")
        recommendation = ms_result.get("allocation_recommendation", "No allocation recommendation provided.")
        risk = ms_result.get("risk_notes", "No additional risk notes.")

        intro = (
            "Here’s the plain-English result."
            if self.user_profile == "retail"
            else "Structured outcome from MS follows."
        )
        return f"{intro}\n\nSummary: {summary}\nRecommendation: {recommendation}\nRisk notes: {risk}"

    def _question_for(self, field: str) -> str:
        retail_q = {
            "strategy_type": "What style are you aiming for: balanced, income, growth, or inflation-aware?",
            "risk_tolerance": "How much volatility can you tolerate: low, moderate, high, or very high?",
            "leverage_allowed": "Are you comfortable with leverage? (yes/no)",
            "investment_vehicle": "Which vehicle do you want to use: ETF, fund, futures, SMA, or mixed?",
            "base_currency": "What base currency should we optimize in? (e.g., USD, AUD)",
            "time_horizon": "What’s your time horizon and main objective?",
            "liquidity_constraints": "How often do you need liquidity, and what lock-up can you tolerate?",
        }
        sophist_q = {
            "strategy_type": "Specify mandate type (balanced/income/growth/real-return/custom).",
            "risk_tolerance": "Specify risk bucket (low/moderate/high/very_high).",
            "leverage_allowed": "Leverage constraint: allowed true/false?",
            "investment_vehicle": "Execution vehicle set (etf/mutual_fund/futures/SMA/mixed)?",
            "base_currency": "Base reporting currency (ISO-4217).",
            "time_horizon": "Provide horizon in years and objective enum.",
            "liquidity_constraints": "Provide redemption cadence + max lockup days.",
        }
        return (retail_q if self.user_profile == "retail" else sophist_q)[field]


def _read_json_arg(raw: str) -> Dict[str, Any]:
    if not raw:
        return {}
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(prog="/node")
    parser.add_argument("command", choices=["gather", "package", "explain"])
    parser.add_argument("--payload", default="{}", help="JSON payload for allocation request")
    parser.add_argument("--ms-result", default="{}", help="JSON result payload from MS")
    parser.add_argument("--profile", choices=["retail", "sophisticated"], default="retail")
    args = parser.parse_args()

    agent = NodeAgent(user_profile=args.profile)

    if args.command == "gather":
        payload = _read_json_arg(args.payload)
        print(json.dumps(agent.gather(payload), indent=2))
        return 0

    if args.command == "package":
        payload = _read_json_arg(args.payload)
        print(json.dumps(agent.package(payload), indent=2))
        return 0

    ms_result = _read_json_arg(args.ms_result)
    print(agent.explain(ms_result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
