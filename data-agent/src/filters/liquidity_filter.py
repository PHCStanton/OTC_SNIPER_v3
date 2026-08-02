"""Liquidity Gate Filter — Vetoes signals outside configured tick density bounds."""
from typing import Any, Dict, Tuple
from .base_filter import BaseFilter


class LiquidityFilter(BaseFilter):
    """Decoupled Liquidity Gate Filter enforcing min and max tick density scores."""

    def __init__(self, min_liquidity: float = 30.0, max_liquidity: float = 70.0, enabled: bool = True):
        super().__init__(name="liquidity", enabled=enabled)
        self.min_liquidity = min_liquidity
        self.max_liquidity = max_liquidity

    def evaluate(self, tick_data: Dict[str, Any], market_context: Dict[str, Any] | None = None) -> Tuple[bool, str | None]:
        if not self.enabled:
            return True, None

        mc = market_context or tick_data.get("market_context") or {}
        liq_score = mc.get("liquidity_score")
        if liq_score is None:
            liq_score = tick_data.get("liquidity_score")

        if liq_score is not None:
            if liq_score < self.min_liquidity or liq_score > self.max_liquidity:
                return False, f"liquidity_score_out_of_bounds ({liq_score:.1f} not in [{self.min_liquidity}, {self.max_liquidity}])"

        return True, None
