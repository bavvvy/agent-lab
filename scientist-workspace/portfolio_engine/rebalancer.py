from datetime import date
from typing import Any, Dict


class MonthlyRebalancer:
    """Monthly schedule; rebalance on first observed trading day of month."""

    def should_rebalance(
        self,
        *,
        as_of_date: date,
        last_rebalance_date: date | None,
        context: Dict[str, Any] | None = None,
    ) -> bool:
        if last_rebalance_date is None:
            return True
        return (as_of_date.year, as_of_date.month) != (
            last_rebalance_date.year,
            last_rebalance_date.month,
        )

    def generate_trades(
        self,
        *,
        current_positions: Dict[str, float],
        target_positions: Dict[str, float],
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, float]:
        symbols = set(current_positions) | set(target_positions)
        return {
            symbol: target_positions.get(symbol, 0.0) - current_positions.get(symbol, 0.0)
            for symbol in sorted(symbols)
        }
