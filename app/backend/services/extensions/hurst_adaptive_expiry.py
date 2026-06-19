import logging
from collections import deque
from typing import Any, Dict, Tuple
import numpy as np

from app.backend.services.extensions.base import BaseExtension

logger = logging.getLogger(__name__)

class HurstAdaptiveExpiry(BaseExtension):
    """
    Premium extension implementing Package 2 "Adaptive Edge".
    Uses vectorized multi-scale R/S to compute the Hurst exponent and dynamically
    scales binary contract expirations.
    """
    
    def __init__(self, settings: Dict[str, Any]):
        # Default settings for Adaptive Edge
        defaults = {
            "enabled": True,
            "mean_revert_limit": 0.44,
            "trend_limit": 0.58,
            "min_adaptive_expiry": 60,
        }
        defaults.update(settings)
        super().__init__(defaults)
        
        self.mean_revert_limit = float(self.settings["mean_revert_limit"])
        self.trend_limit = float(self.settings["trend_limit"])
        self.min_adaptive_expiry = int(self.settings["min_adaptive_expiry"])
        
        # In-memory price buffers for tick-level data (up to 1000 ticks)
        self._price_buffers: Dict[str, deque[float]] = {}
        # Regime state machine trackers per asset
        self._regime_states: Dict[str, str] = {}
        # Last calculated Hurst value
        self._last_h: Dict[str, float] = {}

    def calculate_vectorized_hurst(self, prices: np.ndarray) -> float:
        """
        Vectorized Multi-Scale R/S computation using NumPy.
        Fits scales to find the log-log regression slope.
        """
        if len(prices) < 50:
            return 0.5
            
        # Log returns
        returns = np.diff(np.log(prices))
        N = len(returns)
        
        # Reference scales
        scales = [16, 32, 64, 128, 256]
        rs_list = []
        
        for scale in scales:
            if N < scale:
                continue
            # Truncate returns to be divisible by scale
            num_segments = N // scale
            segments = returns[:num_segments * scale].reshape((num_segments, scale))
            
            # Column-wise mean-deviation and range analysis
            means = np.mean(segments, axis=1, keepdims=True)
            cum_dev = np.cumsum(segments - means, axis=1)
            
            # Compute range and sample standard deviation
            ranges = np.max(cum_dev, axis=1) - np.min(cum_dev, axis=1)
            stds = np.std(segments, axis=1, ddof=1)
            
            valid = stds > 0
            if np.any(valid):
                rs_list.append(np.mean(ranges[valid] / stds[valid]))
            else:
                rs_list.append(1.0)
                
        if len(rs_list) < 2:
            return 0.5
            
        # Polyfit log(R/S) vs log(scales)
        try:
            h, _ = np.polyfit(np.log(scales[:len(rs_list)]), np.log(rs_list), 1)
            return float(np.clip(h, 0.0, 1.0))
        except Exception as err:
            logger.debug("Failed polyfit regression in vectorized Hurst: %s", err)
            return 0.5

    def update_regime(self, current_state: str, current_h: float) -> str:
        """
        Regime Hysteresis State Machine to prevent high-frequency state swapping.
        """
        if current_state == "mean_reverting":
            if current_h > 0.48:  # Escape buffer threshold
                return "random_walk"
        elif current_state == "trending":
            if current_h < 0.52:  # Escape buffer threshold
                return "random_walk"
        else:  # Currently in random_walk
            if current_h < self.mean_revert_limit:
                return "mean_reverting"
            elif current_h > self.trend_limit:
                return "trending"
                
        return current_state

    def on_tick_processed(
        self, 
        asset: str, 
        price: float, 
        timestamp: float, 
        oteo_result: Dict[str, Any], 
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Track ticks in memory and inject multi-scale metadata into oteo_result."""
        if not self.enabled:
            return oteo_result
            
        if asset not in self._price_buffers:
            self._price_buffers[asset] = deque(maxlen=1000)
        self._price_buffers[asset].append(price)
        
        # Inject current premium data into results
        if asset in self._regime_states:
            h_val = self._last_h.get(asset, 0.5)
            state = self._regime_states[asset]
            
            oteo_result["hurst"] = round(h_val, 3)
            if "market_context" not in oteo_result:
                oteo_result["market_context"] = {}
            oteo_result["market_context"]["hurst"] = round(h_val, 3)
            oteo_result["market_context"]["hurst_regime"] = state
            
        return oteo_result

    def on_candle_closed(
        self, 
        asset: str, 
        closed_candle: Any, 
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fired on candle close - calculate vectorized Hurst and update the regime state."""
        if not self.enabled:
            return {}
            
        prices = list(self._price_buffers.get(asset, []))
        if len(prices) >= 100:
            h_val = self.calculate_vectorized_hurst(np.array(prices))
            self._last_h[asset] = h_val
            
            current_state = self._regime_states.get(asset, "random_walk")
            next_state = self.update_regime(current_state, h_val)
            self._regime_states[asset] = next_state
            
            market_context["hurst"] = round(h_val, 3)
            market_context["hurst_regime"] = next_state
            
            logger.info("Adaptive Edge calculated Hurst for %s: H=%.3f, Regime=%s", asset, h_val, next_state)
            
        return {}

    def on_consider_signal(
        self, 
        asset: str, 
        price: float, 
        oteo_result: Dict[str, Any], 
        config: Any
    ) -> Tuple[bool, str | None]:
        """Veto trades if in trending or chop regimes, and override expiration seconds."""
        if not self.enabled:
            return True, None
            
        h_val = self._last_h.get(asset, 0.5)
        state = self._regime_states.get(asset, "random_walk")
        
        # Veto check
        if state == "trending":
            return False, "regime_trending"
        elif state == "random_walk":
            return False, "regime_chop"
            
        # Adaptive Expiry Logic:
        # Strong mean reversion (H <= 0.35) -> shorter expiry
        # Moderate mean reversion (H < 0.44) -> longer expiry
        if h_val <= 0.35:
            expiry = self.min_adaptive_expiry  # e.g., 60s
        else:
            expiry = self.min_adaptive_expiry * 2  # e.g., 120s
            
        oteo_result["override_expiration_seconds"] = expiry
        logger.info("[Premium] Adaptive Expiry set option contract duration to %ds for %s (H=%.3f)", expiry, asset, h_val)
        
        return True, None
