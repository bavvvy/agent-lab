from __future__ import annotations

from typing import Any


def _equal_weights(keys: list[Any]) -> dict[str, float]:
    if not keys:
        return {}
    w = 1.0 / len(keys)
    return {str(k): w for k in keys}


def weight_level_one(hierarchy: dict[str, Any]) -> dict[str, float]:
    return _equal_weights(list(hierarchy.keys()))


def weight_within_group(group: dict[str, Any] | list[Any]) -> dict[str, float]:
    if isinstance(group, dict):
        return _equal_weights(list(group.keys()))
    return _equal_weights(list(range(len(group))))
