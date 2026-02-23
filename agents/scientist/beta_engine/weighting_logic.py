from __future__ import annotations

from typing import Any


def weight_level_one(hierarchy: dict[str, Any]) -> dict[str, float]:
    keys = list(hierarchy.keys())
    if not keys:
        return {}
    w = 1.0 / len(keys)
    return {k: w for k in keys}


def weight_within_group(group: dict[str, Any] | list[Any]) -> dict[str, float]:
    if isinstance(group, dict):
        keys = list(group.keys())
    else:
        keys = list(range(len(group)))

    if not keys:
        return {}

    w = 1.0 / len(keys)
    return {str(k): w for k in keys}
