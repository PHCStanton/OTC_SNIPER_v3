"""Volatility Gate Filter — Vetoes signals outside configured volatility score bounds."""
from typing import Any, Dict, Tuple

from .base_filter import BaseFilter
from .context_provider import as_finite_float


class VolatilityFilter(BaseFilter):
    """Decoupled Volatility Gate Filter. Fail-closed on missing/invalid score."""

    def __init__(
        self,
        min_volatility: float = 30.0,
        max_volatility: float = 85.0,
        enabled: bool = True,
    ):
        super().__init__(name="volatility", enabled=enabled)
        self.min_volatility = min_volatility
        self.max_volatility = max_volatility

    def evaluate(
        self,
        tick_data: Dict[str, Any],
        market_context: Dict[str, Any] | None = None,
    ) -> Tuple[bool, str | None]:
        if not self.enabled:
            return True, None

        mc = market_context if isinstance(market_context, dict) else {}
        raw = mc.get("volatility_score")
        if raw is None:
            raw = tick_data.get("volatility_score")

        vol_score = as_finite_float(raw)
        if vol_score is None:
            return False, "volatility_context_unavailable"

        if vol_score < self.min_volatility or vol_score > self.max_volatility:
            return (
                False,
                f"volatility_score_out_of_bounds "
                f"({vol_score:.1f} not in [{self.min_volatility}, {self.max_volatility}])",
            )

        return True, None
