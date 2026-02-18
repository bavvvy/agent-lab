from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class TypedModuleConfig:
    type: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EngineMetaConfig:
    name: str
    version: str


@dataclass(frozen=True)
class ConstraintConfig:
    leverage: bool = False


@dataclass(frozen=True)
class EngineConfig:
    engine: EngineMetaConfig
    allocation_model: TypedModuleConfig
    overlays: List[TypedModuleConfig]
    rebalancer: TypedModuleConfig
    allocator: TypedModuleConfig
    constraints: ConstraintConfig


def _require_dict(value: Any, field_name: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _parse_typed_module(value: Any, field_name: str) -> TypedModuleConfig:
    raw = _require_dict(value, field_name)
    module_type = raw.get("type")
    if not isinstance(module_type, str) or not module_type:
        raise ValueError(f"{field_name}.type must be a non-empty string")
    params = raw.get("params", {})
    if not isinstance(params, dict):
        raise TypeError(f"{field_name}.params must be a mapping")
    return TypedModuleConfig(type=module_type, params=params)


def parse_engine_config(config: Dict[str, Any]) -> EngineConfig:
    root = _require_dict(config, "config")

    engine_raw = _require_dict(root.get("engine"), "engine")
    name = engine_raw.get("name")
    version = engine_raw.get("version")
    if not isinstance(name, str) or not name:
        raise ValueError("engine.name must be a non-empty string")
    if isinstance(version, (int, float)):
        version = str(version)
    if not isinstance(version, str) or not version:
        raise ValueError("engine.version must be a non-empty string")

    allocation_model = _parse_typed_module(root.get("allocation_model"), "allocation_model")

    overlays_raw = root.get("overlays", [])
    if not isinstance(overlays_raw, list):
        raise TypeError("overlays must be a list")
    overlays = [_parse_typed_module(item, f"overlays[{idx}]") for idx, item in enumerate(overlays_raw)]

    rebalancer = _parse_typed_module(root.get("rebalancer"), "rebalancer")
    allocator = _parse_typed_module(root.get("allocator"), "allocator")

    constraints_raw = root.get("constraints", {})
    constraints_raw = _require_dict(constraints_raw, "constraints")
    leverage = constraints_raw.get("leverage", False)
    if not isinstance(leverage, bool):
        raise TypeError("constraints.leverage must be a boolean")

    return EngineConfig(
        engine=EngineMetaConfig(name=name, version=version),
        allocation_model=allocation_model,
        overlays=overlays,
        rebalancer=rebalancer,
        allocator=allocator,
        constraints=ConstraintConfig(leverage=leverage),
    )
