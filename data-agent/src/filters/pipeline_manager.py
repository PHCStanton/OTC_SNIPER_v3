"""Pipeline Manager — Orchestrates on-demand execution of single or combined filter gates."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence, Tuple

from .base_filter import BaseFilter
from .bayesian_filter import BayesianFilter
from .liquidity_filter import LiquidityFilter
from .manipulation_filter import ManipulationFilter
from .volatility_filter import VolatilityFilter

logger = logging.getLogger(__name__)


class UnknownGateError(ValueError):
    """Raised when one or more requested gate names are not registered."""

    def __init__(self, unknown_gates: Sequence[str]):
        self.unknown_gates = list(unknown_gates)
        super().__init__(
            f"Unknown filter gate(s): {', '.join(self.unknown_gates)}"
        )


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
        key = name.strip().lower()
        self.available_filters[key] = filter_instance
        logger.info("Registered dynamic filter plugin: %s", key)

    def unknown_gates(self, active_gates: Sequence[str] | None) -> List[str]:
        """Return gate names that are not registered (original casing preserved)."""
        if not active_gates:
            return []
        unknown: List[str] = []
        for gate_name in active_gates:
            clean = gate_name.strip()
            if not clean:
                continue
            if clean.lower() not in self.available_filters:
                unknown.append(clean)
        return unknown

    def evaluate_pipeline(
        self,
        tick_data: Dict[str, Any],
        active_gates: List[str] | None = None,
        market_context: Dict[str, Any] | None = None,
        *,
        reject_unknown: bool = True,
    ) -> Tuple[bool, List[str]]:
        """
        Evaluate tick data against requested filter gates.

        Unknown gate names raise UnknownGateError when reject_unknown is True
        (default), instead of silently passing.

        Returns:
            Tuple[bool, List[str]]: (Overall passed boolean, List of veto reasons)
        """
        if not active_gates:
            return True, []

        unknown = self.unknown_gates(active_gates)
        if unknown and reject_unknown:
            raise UnknownGateError(unknown)

        veto_reasons: List[str] = []
        overall_passed = True

        for gate_name in active_gates:
            gate_name_clean = gate_name.strip().lower()
            if not gate_name_clean:
                continue
            filter_plugin = self.available_filters.get(gate_name_clean)
            if filter_plugin is None:
                continue
            if not filter_plugin.enabled:
                continue
            passed, reason = filter_plugin.evaluate(tick_data, market_context)
            if not passed and reason:
                overall_passed = False
                veto_reasons.append(reason)

        return overall_passed, veto_reasons
