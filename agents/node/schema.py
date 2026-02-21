from __future__ import annotations

import re
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
                "objective": {
                    "type": "string",
                    "enum": ["capital_preservation", "income", "balanced_growth", "max_growth"],
                },
            },
        },
        "liquidity_constraints": {
            "type": "object",
            "additionalProperties": False,
            "required": ["redemption_window", "max_lockup_days"],
            "properties": {
                "redemption_window": {
                    "type": "string",
                    "enum": ["daily", "weekly", "monthly", "quarterly", "annual"],
                },
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
    return [field for field in required if field not in payload]


def validate_payload(payload: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    missing = validate_required_fields(payload)
    if missing:
        errors.extend([f"Missing required field: {m}" for m in missing])
        return errors

    if payload.get("strategy_type") not in ALLOCATION_REQUEST_SCHEMA["properties"]["strategy_type"]["enum"]:
        errors.append("Invalid strategy_type")

    if payload.get("risk_tolerance") not in ALLOCATION_REQUEST_SCHEMA["properties"]["risk_tolerance"]["enum"]:
        errors.append("Invalid risk_tolerance")

    if not isinstance(payload.get("leverage_allowed"), bool):
        errors.append("leverage_allowed must be boolean")

    if payload.get("investment_vehicle") not in ALLOCATION_REQUEST_SCHEMA["properties"]["investment_vehicle"]["enum"]:
        errors.append("Invalid investment_vehicle")

    if not isinstance(payload.get("base_currency"), str) or not re.match(r"^[A-Z]{3}$", payload["base_currency"]):
        errors.append("base_currency must be 3-letter uppercase ISO code")

    th = payload.get("time_horizon")
    if not isinstance(th, dict):
        errors.append("time_horizon must be object")
    else:
        years = th.get("years")
        objective = th.get("objective")
        if not isinstance(years, (int, float)) or years < 0.5 or years > 100:
            errors.append("time_horizon.years must be between 0.5 and 100")
        if objective not in ALLOCATION_REQUEST_SCHEMA["properties"]["time_horizon"]["properties"]["objective"]["enum"]:
            errors.append("Invalid time_horizon.objective")

    lc = payload.get("liquidity_constraints")
    if not isinstance(lc, dict):
        errors.append("liquidity_constraints must be object")
    else:
        rw = lc.get("redemption_window")
        lockup = lc.get("max_lockup_days")
        if rw not in ALLOCATION_REQUEST_SCHEMA["properties"]["liquidity_constraints"]["properties"]["redemption_window"]["enum"]:
            errors.append("Invalid liquidity_constraints.redemption_window")
        if not isinstance(lockup, int) or lockup < 0 or lockup > 3650:
            errors.append("liquidity_constraints.max_lockup_days must be integer 0..3650")

    up = payload.get("user_profile")
    if up is not None and up not in ["retail", "sophisticated"]:
        errors.append("user_profile must be retail|sophisticated")

    return errors
