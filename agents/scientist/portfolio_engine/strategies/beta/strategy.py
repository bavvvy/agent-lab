from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .weighting_logic import weight_level_one


@dataclass(frozen=True)
class BetaStrategy:
    name: str
    template: dict[str, Any]

    def generate_weights(self) -> dict[str, float]:
        tickers = self.template.get("tickers", {}) if isinstance(self.template, dict) else {}
        if isinstance(tickers, dict) and tickers:
            hierarchy = {str(k): {} for k in tickers.keys()}
            return weight_level_one(hierarchy)
        return {}
