"""Manipulation Gate Filter — Vetoes signals when broker manipulation severity exceeds threshold."""
from typing import Any, Dict, Tuple
from .base_filter import BaseFilter


class ManipulationFilter(BaseFilter):
    """Decoupled Broker Manipulation Gate Filter."""

    def __init__(self, severity_threshold: float = 0.15, enabled: bool = True):
        super().__init__(name="manipulation", enabled=enabled)
        self.severity_threshold = severity_threshold

    def evaluate(self, tick_data: Dict[str, Any], market_context: Dict[str, Any] | None = None) -> Tuple[bool, str | None]:
        if not self.enabled:
            return True, None

        mc = market_context or tick_data.get("market_context") or {}
        has_manip = mc.get("has_manipulation", tick_data.get("has_manipulation", False))
        manip_severity = mc.get("manipulation_severity", tick_data.get("manipulation_severity", 0.0))

        if has_manip or manip_severity > self.severity_threshold:
            return False, f"manipulation_veto (severity {manip_severity:.3f} > {self.severity_threshold})"

        return True, None
