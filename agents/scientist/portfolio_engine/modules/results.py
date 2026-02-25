from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PortfolioResult:
    name: str
    weights: dict[str, float]
    returns: list[float] | list[dict[str, Any]]
