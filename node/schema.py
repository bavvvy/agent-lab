from __future__ import annotations

from typing import Any, Dict, List

ALLOCATION_REQUEST_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "node/allocation_request.schema.json",
    "title": "AllocationRequest",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "strategy_type",
        "risk_tolerance",
        "leverage_allowed",
        "investment_vehicle",
        "base_currency",
        "time_horizon",
        "liquidity_constraints",
    ],
    "properties": {
        "strategy_type": {
            "type": "string",
            "enum": ["balanced", "income", "growth", "real-return", "custom"],
        },
        "risk_tolerance": {
            "type": "string",
            "enum": ["low", "moderate", "high", "very_high"],
        },
        "leverage_allowed": {"type": "boolean"},
        "investment_vehicle": {
            "type": "string",
            "enum": ["etf", "mutual_fund", "futures", "separately_managed_account", "mixed"],
        },
        "base_currency": {
            "type": "string",
            "pattern": "^[A-Z]{3}$",
            "examples": ["USD", "AUD", "EUR"],
        },
        "time_horizon": {
            "type": "object",
            "additionalProperties": False,
            "required": ["years", "objective"],
            "properties": {
                "years": {"type": "number", "minimum": 0.5, "maximum": 100},
                "objective": {"type": "string", "enum": ["capital_preservation", "income", "balanced_growth", "max_growth"]},
            },
        },
        "liquidity_constraints": {
            "type": "object",
            "additionalProperties": False,
            "required": ["redemption_window", "max_lockup_days"],
            "properties": {
                "redemption_window": {"type": "string", "enum": ["daily", "weekly", "monthly", "quarterly", "annual"]},
                "max_lockup_days": {"type": "integer", "minimum": 0, "maximum": 3650},
                "notes": {"type": "string"},
            },
        },
        "user_profile": {
            "type": "string",
            "enum": ["retail", "sophisticated"],
            "default": "retail",
        },
    },
}


def validate_required_fields(payload: Dict[str, Any]) -> List[str]:
    required = ALLOCATION_REQUEST_SCHEMA["required"]
    missing = [field for field in required if field not in payload]
    return missing
