from __future__ import annotations

from datetime import date
from typing import Any, Dict, Protocol

Weights = Dict[str, float]
Positions = Dict[str, float]
Prices = Dict[str, float]
Trades = Dict[str, float]
Allocations = Dict[str, Dict[str, float]]
Context = Dict[str, Any]


class AllocationModel(Protocol):
    def target_weights(self, *, as_of_date: date, context: Context) -> Weights: ...


class Overlay(Protocol):
    def apply(self, *, weights: Weights, as_of_date: date, context: Context) -> Weights: ...


class Rebalancer(Protocol):
    def should_rebalance(
        self,
        *,
        as_of_date: date,
        last_rebalance_date: date | None,
        context: Context,
    ) -> bool: ...

    def generate_trades(
        self,
        *,
        current_positions: Positions,
        target_positions: Positions,
        context: Context,
    ) -> Trades: ...


class Allocator(Protocol):
    def allocate(
        self,
        *,
        weights: Weights,
        portfolio_value: float,
        prices: Prices,
        context: Context,
    ) -> Allocations: ...
