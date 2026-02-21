from .layers.capital_allocation import CapitalAllocator
from .modules.beta_engine_60_40 import BetaEngine6040
from .modules.regime_overlay_none import RegimeOverlayNone
from .modules.risk_overlay_none import RiskOverlayNone
from .rebalancer import MonthlyRebalancer

ALLOCATION_MODELS = {
    "beta_engine_60_40": BetaEngine6040,
}

OVERLAYS = {
    "risk_overlay_none": RiskOverlayNone,
    "regime_overlay_none": RegimeOverlayNone,
}

REBALANCERS = {
    "monthly": MonthlyRebalancer,
}

ALLOCATORS = {
    "capital_allocator": CapitalAllocator,
}
