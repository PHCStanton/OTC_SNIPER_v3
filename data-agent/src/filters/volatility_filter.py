"""Volatility Gate Filter — Vetoes signals outside configured volatility score bounds."""
from typing import Any, Dict, Tuple
from .base_filter import BaseFilter


class VolatilityFilter(BaseFilter):
    """Decoupled Volatility Gate Filter enforcing min and max volatility scores."""

    def __init__(self, min_volatility: float = 30.0, max_volatility: float = 85.0, enabled: bool = True):
        super().__init__(name="volatility", enabled=enabled)
        self.min_volatility = min_volatility
        self.max_volatility = max_volatility

    def evaluate(self, tick_data: Dict[str, Any], market_context: Dict[str, Any] | None = None) -> Tuple[bool, str | None]:
        if not self.enabled:
            return True, None

        mc = market_context or tick_data.get("market_context") or {}
        vol_score = mc.get("volatility_score")
        if vol_score is None:
            vol_score = tick_data.get("volatility_score")

        if vol_score is not None:
            if vol_score < self.min_volatility or vol_score > self.max_volatility:
                return False, f"volatility_score_out_of_bounds ({vol_score:.1f} not in [{self.min_volatility}, {self.max_volatility}])"

        return True, None
