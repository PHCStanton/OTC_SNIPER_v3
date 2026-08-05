"""Manipulation Gate Filter — Vetoes when broker manipulation severity exceeds threshold."""
from typing import Any, Dict, Tuple

from .base_filter import BaseFilter
from .context_provider import as_finite_float, as_strict_bool


class ManipulationFilter(BaseFilter):
    """
    Decoupled Broker Manipulation Gate Filter.

    Severity is authoritative. has_manipulation is explanatory metadata only;
    a flag alone below threshold does not veto.
    Fail-closed when severity is missing or invalid.
    """

    def __init__(self, severity_threshold: float = 0.15, enabled: bool = True):
        super().__init__(name="manipulation", enabled=enabled)
        self.severity_threshold = severity_threshold

    def evaluate(
        self,
        tick_data: Dict[str, Any],
        market_context: Dict[str, Any] | None = None,
    ) -> Tuple[bool, str | None]:
        if not self.enabled:
            return True, None

        mc = market_context if isinstance(market_context, dict) else {}

        raw_severity = mc.get("manipulation_severity")
        if raw_severity is None:
            raw_severity = tick_data.get("manipulation_severity")

        manip_severity = as_finite_float(raw_severity)
        if manip_severity is None:
            return False, "manipulation_context_unavailable"

        raw_flag = mc.get("has_manipulation", tick_data.get("has_manipulation"))
        has_manip = as_strict_bool(raw_flag)

        if manip_severity > self.severity_threshold:
            reason = (
                f"manipulation_veto (severity {manip_severity:.3f} > "
                f"{self.severity_threshold})"
            )
            if has_manip is True:
                reason = f"{reason}; has_manipulation=true"
            return False, reason

        return True, None
