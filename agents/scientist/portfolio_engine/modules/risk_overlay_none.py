from datetime import date
from typing import Any, Dict


class RiskOverlayNone:
    """No-op risk overlay."""

    def apply(
        self,
        *,
        weights: Dict[str, float],
        as_of_date: date | None = None,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, float]:
        return dict(weights)
