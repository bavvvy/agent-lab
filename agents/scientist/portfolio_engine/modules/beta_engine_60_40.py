from dataclasses import dataclass
from datetime import date
from typing import Any, Dict


@dataclass(frozen=True)
class BetaEngine6040:
    """Static beta engine; emits configured SPY/TLT-style weights."""

    weights: Dict[str, float]

    def target_weights(
        self,
        *,
        as_of_date: date | None = None,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, float]:
        total = sum(self.weights.values())
        if total <= 0:
            raise ValueError("Configured weights must sum to a positive value")
        return {symbol: weight / total for symbol, weight in self.weights.items()}
