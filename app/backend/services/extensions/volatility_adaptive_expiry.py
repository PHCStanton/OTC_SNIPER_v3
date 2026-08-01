import logging
from typing import Any, Dict, Tuple

from .base import BaseExtension

logger = logging.getLogger(__name__)

class VolatilityAdaptiveExpiry(BaseExtension):
    """
    Volatility-Adaptive Expiry Extension.
    Maps volatility scores directly to Pocket Option execution intervals
    (15s, 30s, 60s, 120s, 300s) to optimize trade duration dynamically.
    """
    
    def __init__(self, settings: Dict[str, Any]):
        defaults = {
            "enabled": True,
            "min_adaptive_expiry": 60,
        }
        defaults.update(settings)
        super().__init__(defaults)
        
        self.min_adaptive_expiry = int(self.settings["min_adaptive_expiry"])
        self.config_ref = None

    def on_tick_processed(
        self, 
        asset: str, 
        price: float, 
        timestamp: float, 
        oteo_result: Dict[str, Any], 
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Inject the volatility-adaptive contract duration into oteo_result."""
        if not self.enabled:
            return oteo_result
            
        vol_score = market_context.get("volatility_score")
        if vol_score is None:
            vol_score = oteo_result.get("volatility_score")
        if vol_score is None:
            vol_score = 50.0  # default baseline
            
        # Volatility-Adaptive Expiry Mapping:
        # Lower volatility -> longer expiry (since price takes longer to revert).
        # Higher volatility -> shorter expiry.
        if vol_score < 30.0:
            expiry = 300  # 5m
        elif vol_score < 50.0:
            expiry = 120  # 2m
        elif vol_score < 70.0:
            expiry = 60   # 1m
        elif vol_score < 85.0:
            expiry = 30   # 30s
        else:
            expiry = 15   # 15s
            
        # Clamp to configured min_adaptive_expiry
        min_expiry = getattr(self.config_ref, "min_adaptive_expiry", self.min_adaptive_expiry) if self.config_ref else self.min_adaptive_expiry
        
        if expiry < min_expiry:
            valid_intervals = [15, 30, 60, 120, 300]
            allowed = [i for i in valid_intervals if i >= min_expiry]
            expiry = min(allowed) if allowed else min_expiry
            
        oteo_result["override_expiration_seconds"] = expiry
        oteo_result["volatility_adaptive_expiry"] = expiry
        
        # Inject into market_context for frontend transparency
        if "market_context" not in oteo_result:
            oteo_result["market_context"] = {}
        oteo_result["market_context"]["volatility_adaptive_expiry"] = expiry
            
        return oteo_result

    def on_candle_closed(
        self, 
        asset: str, 
        closed_candle: Any, 
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {}

    def on_consider_signal(
        self, 
        asset: str, 
        price: float, 
        oteo_result: Dict[str, Any], 
        config: Any
    ) -> Tuple[bool, str | None]:
        """Store config reference dynamically; do not veto any trades (standalone expiry engine)."""
        self.config_ref = config
        if hasattr(config, "adaptive_expiry_enabled"):
            self.enabled = bool(config.adaptive_expiry_enabled)
        return True, None
