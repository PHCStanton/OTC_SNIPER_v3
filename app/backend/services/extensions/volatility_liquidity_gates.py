import logging
from typing import Any, Dict, Tuple

from .base import BaseExtension

logger = logging.getLogger(__name__)

class VolatilityLiquidityGates(BaseExtension):
    """
    Volatility & Liquidity Gate Extension.
    Vetoes signals if volatility or liquidity scores fall outside
    user-configured minimum and maximum bounds.
    """
    
    def __init__(self, settings: Dict[str, Any]):
        defaults = {
            "enabled": True,
        }
        defaults.update(settings)
        super().__init__(defaults)
        self.config_ref = None

    def on_tick_processed(
        self, 
        asset: str, 
        price: float, 
        timestamp: float, 
        oteo_result: Dict[str, Any], 
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
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
        """Veto trade if volatility or liquidity scores violate gate bounds."""
        if not self.enabled:
            return True, None
            
        self.config_ref = config
        mc = oteo_result.get("market_context") or {}

        # 1. Volatility Gate Check
        vol_enabled = getattr(config, "volatility_gate_enabled", False)
        if vol_enabled:
            vol_score = mc.get("volatility_score")
            if vol_score is None:
                vol_score = oteo_result.get("volatility_score")
            if vol_score is not None:
                min_vol = float(getattr(config, "min_volatility", 0.0))
                max_vol = float(getattr(config, "max_volatility", 100.0))
                if vol_score < min_vol or vol_score > max_vol:
                    logger.info(
                        "Signal vetoed by Volatility Gate on %s: score %.1f outside [%.1f, %.1f]",
                        asset, vol_score, min_vol, max_vol
                    )
                    return False, "volatility_gate"

        # 2. Liquidity Gate Check
        liq_enabled = getattr(config, "liquidity_gate_enabled", False)
        if liq_enabled:
            liq_score = mc.get("liquidity_score")
            if liq_score is None:
                liq_score = oteo_result.get("liquidity_score")
            if liq_score is not None:
                min_liq = float(getattr(config, "min_liquidity", 0.0))
                max_liq = float(getattr(config, "max_liquidity", 100.0))
                if liq_score < min_liq or liq_score > max_liq:
                    logger.info(
                        "Signal vetoed by Liquidity Gate on %s: score %.1f outside [%.1f, %.1f]",
                        asset, liq_score, min_liq, max_liq
                    )
                    return False, "liquidity_gate"

        return True, None
