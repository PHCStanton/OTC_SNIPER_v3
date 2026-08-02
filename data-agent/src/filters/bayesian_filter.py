"""Bayesian Gate Filter — Evaluates posterior win-rate probability against confidence threshold."""
from typing import Any, Dict, Tuple
from .base_filter import BaseFilter


class BayesianFilter(BaseFilter):
    """
    Decoupled Bayesian posterior win-rate filter.
    Evaluates probability that win-rate exceeds breakeven (e.g. 52.63% at 90% payout).
    """

    def __init__(self, confidence_threshold: float = 0.90, breakeven_wr: float = 0.5263, enabled: bool = True):
        super().__init__(name="bayesian", enabled=enabled)
        self.confidence_threshold = confidence_threshold
        self.breakeven_wr = breakeven_wr

    def evaluate(self, tick_data: Dict[str, Any], market_context: Dict[str, Any] | None = None) -> Tuple[bool, str | None]:
        if not self.enabled:
            return True, None

        mc = market_context or tick_data.get("market_context") or {}
        posterior_prob = mc.get("bayesian_posterior_prob")
        if posterior_prob is None:
            posterior_prob = tick_data.get("bayesian_posterior_prob", 0.95)

        if posterior_prob < self.confidence_threshold:
            return False, f"bayesian_posterior_below_threshold ({posterior_prob:.3f} < {self.confidence_threshold})"

        return True, None
