from typing import Any, Dict


class CapitalAllocator:
    """Converts target weights to target notionals and unit counts."""

    def allocate(
        self,
        *,
        weights: Dict[str, float],
        portfolio_value: float,
        prices: Dict[str, float],
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Dict[str, float]]:
        if portfolio_value < 0:
            raise ValueError("portfolio_value must be non-negative")

        allocations: Dict[str, Dict[str, float]] = {}
        for symbol, weight in weights.items():
            if symbol not in prices:
                raise KeyError(f"Missing price for {symbol}")
            px = prices[symbol]
            if px <= 0:
                raise ValueError(f"Invalid non-positive price for {symbol}")

            target_notional = portfolio_value * weight
            target_units = target_notional / px
            allocations[symbol] = {
                "weight": weight,
                "target_notional": target_notional,
                "target_units": target_units,
            }
        return allocations
