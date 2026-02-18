from __future__ import annotations

from dataclasses import dataclass

from .config_schema import EngineConfig
from .interfaces import AllocationModel, Allocator, Overlay, Rebalancer
from .registry import ALLOCATION_MODELS, ALLOCATORS, OVERLAYS, REBALANCERS


@dataclass(frozen=True)
class Pipeline:
    allocation_model: AllocationModel
    overlays: list[Overlay]
    rebalancer: Rebalancer
    allocator: Allocator


def _build_typed(registry: dict[str, type], module_type: str, params: dict):
    if module_type not in registry:
        raise KeyError(f"Unknown module type: {module_type}")
    return registry[module_type](**params)


def build_pipeline(cfg: EngineConfig) -> Pipeline:
    allocation_model = _build_typed(
        ALLOCATION_MODELS,
        cfg.allocation_model.type,
        cfg.allocation_model.params,
    )

    overlays: list[Overlay] = []
    for overlay_cfg in cfg.overlays:
        overlays.append(_build_typed(OVERLAYS, overlay_cfg.type, overlay_cfg.params))

    rebalancer = _build_typed(REBALANCERS, cfg.rebalancer.type, cfg.rebalancer.params)
    allocator = _build_typed(ALLOCATORS, cfg.allocator.type, cfg.allocator.params)

    return Pipeline(
        allocation_model=allocation_model,
        overlays=overlays,
        rebalancer=rebalancer,
        allocator=allocator,
    )
