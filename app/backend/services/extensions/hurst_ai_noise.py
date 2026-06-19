import logging
from collections import deque
from typing import Any, Dict, Tuple
import numpy as np

from app.backend.services.extensions.base import BaseExtension

logger = logging.getLogger(__name__)

class HurstAiNoise(BaseExtension):
    """
    Elite extension implementing Package 3 "AI Pulse & Noise Filter".
    Applies microstructure scale-cutoff filters to exclude short-scale quantization noise.
    """
    
    def __init__(self, settings: Dict[str, Any]):
        defaults = {
            "enabled": True,
            "hurst_min_scale_cutoff": 12,
            "hurst_ai_confidence_threshold": 80.0,
        }
        defaults.update(settings)
        super().__init__(defaults)
        
        self.min_scale_cutoff = int(self.settings["hurst_min_scale_cutoff"])
        self.ai_confidence_threshold = float(self.settings["hurst_ai_confidence_threshold"])
        
        # Rolling tick price buffer
        self._price_buffers: Dict[str, deque[float]] = {}
        self._last_h: Dict[str, float] = {}

    def calculate_filtered_hurst(self, prices: np.ndarray, min_scale: int) -> float:
        """
        Calculates multi-scale Hurst exponent, ignoring any scales below the min_scale cutoff
        to bypass bid-ask bounces and quantization noise.
        """
        if len(prices) < 50:
            return 0.5
            
        returns = np.diff(np.log(prices))
        N = len(returns)
        
        # Standard scales
        all_scales = [16, 32, 64, 128, 256]
        # Exclude scales below cutoff
        scales = [s for s in all_scales if s >= min_scale]
        
        if not scales:
            scales = [16, 32, 64, 128, 256] # Fallback if cutoff is too large
            
        rs_list = []
        for scale in scales:
            if N < scale:
                continue
            num_segments = N // scale
            segments = returns[:num_segments * scale].reshape((num_segments, scale))
            
            means = np.mean(segments, axis=1, keepdims=True)
            cum_dev = np.cumsum(segments - means, axis=1)
            
            ranges = np.max(cum_dev, axis=1) - np.min(cum_dev, axis=1)
            stds = np.std(segments, axis=1, ddof=1)
            
            valid = stds > 0
            if np.any(valid):
                rs_list.append(np.mean(ranges[valid] / stds[valid]))
            else:
                rs_list.append(1.0)
                
        if len(rs_list) < 2:
            return 0.5
            
        try:
            h, _ = np.polyfit(np.log(scales[:len(rs_list)]), np.log(rs_list), 1)
            return float(np.clip(h, 0.0, 1.0))
        except Exception as err:
            logger.debug("Failed polyfit regression in filtered Hurst: %s", err)
            return 0.5

    def on_tick_processed(
        self, 
        asset: str, 
        price: float, 
        timestamp: float, 
        oteo_result: Dict[str, Any], 
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Track ticks in memory and override the standard Hurst value with the filtered calculation."""
        if not self.enabled:
            return oteo_result
            
        if asset not in self._price_buffers:
            self._price_buffers[asset] = deque(maxlen=1000)
        self._price_buffers[asset].append(price)
        
        # Override baseline Hurst with our microstructure noise-filtered Hurst
        if asset in self._last_h:
            h_val = self._last_h[asset]
            oteo_result["hurst"] = round(h_val, 3)
            if "market_context" not in oteo_result:
                oteo_result["market_context"] = {}
            oteo_result["market_context"]["hurst"] = round(h_val, 3)
            
        return oteo_result

    def on_candle_closed(
        self, 
        asset: str, 
        closed_candle: Any, 
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fired on candle close - calculate filtered Hurst."""
        if not self.enabled:
            return {}
            
        prices = list(self._price_buffers.get(asset, []))
        if len(prices) >= 100:
            h_val = self.calculate_filtered_hurst(np.array(prices), self.min_scale_cutoff)
            self._last_h[asset] = h_val
            market_context["hurst"] = round(h_val, 3)
            logger.info("Elite Noise Filter calculated Hurst for %s: H=%.3f (cutoff=%d)", asset, h_val, self.min_scale_cutoff)
            
        return {}

    def on_consider_signal(
        self, 
        asset: str, 
        price: float, 
        oteo_result: Dict[str, Any], 
        config: Any
    ) -> Tuple[bool, str | None]:
        """Veto signal if AI confidence or other elite parameters are not met."""
        if not self.enabled:
            return True, None
            
        # Dynamically read thresholds from config if available
        cutoff = getattr(config, "hurst_min_scale_cutoff", self.min_scale_cutoff)
        self.min_scale_cutoff = cutoff
        
        # Elite level AI Confidence constraint:
        # If the OTEO signal score is below the AI confidence threshold, veto
        score = float(oteo_result.get("oteo_score", 50.0))
        ai_conf_threshold = getattr(config, "hurst_ai_confidence_threshold", self.ai_confidence_threshold)
        
        if score < ai_conf_threshold:
            logger.info("[Elite] Vetoed trade: OTEO score %.1f < Elite AI Confidence threshold %.1f", score, ai_conf_threshold)
            return False, "elite_confidence_floor"
            
        return True, None
