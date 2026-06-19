from __future__ import annotations

from typing import Any, Dict, Tuple

class BaseExtension:
    """Base class for all OTC SNIPER backend plugins."""
    
    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.enabled = settings.get("enabled", False)

    def on_tick_processed(
        self, 
        asset: str, 
        price: float, 
        timestamp: float, 
        oteo_result: Dict[str, Any], 
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Intercepts ticks immediately after OTEO/Level 2/Level 3 calculation.
        Allows plugins to append telemetry data or modify the oteo_score before emission.
        """
        return oteo_result

    def on_candle_closed(
        self, 
        asset: str, 
        closed_candle: Any, 
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Lifecycle hook fired when a 60s bar closes. 
        Ideal for slow, CPU-heavy indicators (e.g., Hurst R/S) to avoid tick-by-tick lag.
        """
        return {}

    def on_consider_signal(
        self, 
        asset: str, 
        price: float, 
        oteo_result: Dict[str, Any], 
        config: Any
    ) -> Tuple[bool, str | None]:
        """
        Veto Gate hook evaluated inside the Auto-Ghost trade processor.
        Returns:
            - True, None: Allow execution.
            - False, "reason": Suppress trade execution and record reject reason.
        """
        return True, None
