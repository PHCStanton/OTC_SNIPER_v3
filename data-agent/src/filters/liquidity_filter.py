"""Liquidity Gate Filter — Vetoes signals outside configured tick density bounds."""
from typing import Any, Dict, Tuple

from .base_filter import BaseFilter
from .context_provider import as_finite_float


class LiquidityFilter(BaseFilter):
    """Decoupled Liquidity Gate Filter. Fail-closed on missing/invalid score."""

    def __init__(
        self,
        min_liquidity: float = 30.0,
        max_liquidity: float = 70.0,
        enabled: bool = True,
    ):
        super().__init__(name="liquidity", enabled=enabled)
        self.min_liquidity = min_liquidity
        self.max_liquidity = max_liquidity

    def evaluate(
        self,
        tick_data: Dict[str, Any],
        market_context: Dict[str, Any] | None = None,
    ) -> Tuple[bool, str | None]:
        if not self.enabled:
            return True, None

        mc = market_context if isinstance(market_context, dict) else {}
        raw = mc.get("liquidity_score")
        if raw is None:
            raw = tick_data.get("liquidity_score")

        liq_score = as_finite_float(raw)
        if liq_score is None:
            return False, "liquidity_context_unavailable"

        if liq_score < self.min_liquidity or liq_score > self.max_liquidity:
            return (
                False,
                f"liquidity_score_out_of_bounds "
                f"({liq_score:.1f} not in [{self.min_liquidity}, {self.max_liquidity}])",
            )

        return True, None
