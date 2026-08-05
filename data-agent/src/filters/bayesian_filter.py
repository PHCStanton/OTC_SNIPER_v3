"""Bayesian Gate Filter — Evaluates posterior win-rate probability against confidence threshold."""
from typing import Any, Dict, Tuple

from .base_filter import BaseFilter
from .context_provider import as_finite_float


class BayesianFilter(BaseFilter):
    """
    Decoupled Bayesian posterior win-rate filter.
    Fail-closed: missing or invalid posterior yields bayesian_context_unavailable.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.90,
        breakeven_wr: float = 0.5263,
        enabled: bool = True,
    ):
        super().__init__(name="bayesian", enabled=enabled)
        self.confidence_threshold = confidence_threshold
        self.breakeven_wr = breakeven_wr

    def evaluate(
        self,
        tick_data: Dict[str, Any],
        market_context: Dict[str, Any] | None = None,
    ) -> Tuple[bool, str | None]:
        if not self.enabled:
            return True, None

        mc = market_context if isinstance(market_context, dict) else {}
        raw = mc.get("bayesian_posterior_prob")
        if raw is None:
            raw = tick_data.get("bayesian_posterior_prob")

        posterior_prob = as_finite_float(raw)
        if posterior_prob is None:
            return False, "bayesian_context_unavailable"

        if posterior_prob < self.confidence_threshold:
            return (
                False,
                f"bayesian_posterior_below_threshold "
                f"({posterior_prob:.3f} < {self.confidence_threshold})",
            )

        return True, None
