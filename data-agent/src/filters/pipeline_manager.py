"""Pipeline Manager — Orchestrates on-demand execution of single or combined filter gates."""
import logging
from typing import Any, Dict, List, Tuple
from .base_filter import BaseFilter
from .bayesian_filter import BayesianFilter
from .volatility_filter import VolatilityFilter
from .liquidity_filter import LiquidityFilter
from .manipulation_filter import ManipulationFilter

logger = logging.getLogger(__name__)


class FilterPipelineManager:
    """Manages dynamic filter loading and execution for Data Agent DaaS Bridge."""

    def __init__(self):
        self.available_filters: Dict[str, BaseFilter] = {
            "bayesian": BayesianFilter(),
            "volatility": VolatilityFilter(),
            "liquidity": LiquidityFilter(),
            "manipulation": ManipulationFilter(),
        }

    def register_filter(self, name: str, filter_instance: BaseFilter) -> None:
        """Register a new filter module dynamically."""
        self.available_filters[name] = filter_instance
        logger.info(f"Registered dynamic filter plugin: {name}")

    def evaluate_pipeline(
        self, 
        tick_data: Dict[str, Any], 
        active_gates: List[str] | None = None,
        market_context: Dict[str, Any] | None = None
    ) -> Tuple[bool, List[str]]:
        """
        Evaluate tick data against requested filter gates.

        Args:
            tick_data: Raw tick/signal data dictionary
            active_gates: List of filter names to evaluate (e.g. ['bayesian', 'volatility']). If None/empty, no filters applied.
            market_context: Optional market metrics dictionary

        Returns:
            Tuple[bool, List[str]]: (Overall passed boolean, List of veto reasons)
        """
        if not active_gates:
            return True, []

        veto_reasons: List[str] = []
        overall_passed = True

        for gate_name in active_gates:
            gate_name_clean = gate_name.strip().lower()
            filter_plugin = self.available_filters.get(gate_name_clean)
            if filter_plugin and filter_plugin.enabled:
                passed, reason = filter_plugin.evaluate(tick_data, market_context)
                if not passed and reason:
                    overall_passed = False
                    veto_reasons.append(reason)

        return overall_passed, veto_reasons
