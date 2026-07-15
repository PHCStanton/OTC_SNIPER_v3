"""
RSI/CCI Momentum Confluence Extension.
Runs as a live streaming plugin — computes RSI(7) and CCI(9) on its own
30-second candle stream and vetoes Auto-Ghost trades lacking parallel momentum.
"""
from typing import Any, Dict, Tuple
from .base import BaseExtension
from ..candle_builder import CandleBuilder
from ..indicators import compute_rsi, compute_cci, compute_slope


class RSICCIConfluenceExtension(BaseExtension):
    def __init__(self, settings: Dict[str, Any]):
        super().__init__(settings)
        self._builders: Dict[str, CandleBuilder] = {}
        self._rsi_history: Dict[str, list] = {}
        self._cci_history: Dict[str, list] = {}
        self.rsi_period = settings.get("rsi_period", 7)
        self.cci_period = settings.get("cci_period", 9)
        self.candle_seconds = settings.get("candle_seconds", 30)
        self.rsi_overbought = settings.get("rsi_overbought", 70.0)
        self.rsi_oversold = settings.get("rsi_oversold", 30.0)
        self.min_slope = settings.get("min_slope_magnitude", 0.5)

    def _get_builder(self, asset: str) -> CandleBuilder:
        if asset not in self._builders:
            self._builders[asset] = CandleBuilder(self.candle_seconds, max_candles=50)
            self._rsi_history[asset] = []
            self._cci_history[asset] = []
        return self._builders[asset]

    def on_tick_processed(self, asset: str, price: float, timestamp: float, 
                           oteo_result: Dict[str, Any], market_context: Dict[str, Any]) -> Dict[str, Any]:
        builder = self._get_builder(asset)
        closed = builder.update(price, timestamp)
        
        if closed is not None:
            closes = builder.get_closes()
            highs = builder.get_highs()
            lows = builder.get_lows()
            rsi = compute_rsi(closes, self.rsi_period)
            cci = compute_cci(highs, lows, closes, self.cci_period)
            if rsi is not None:
                self._rsi_history[asset].append(rsi)
                self._rsi_history[asset] = self._rsi_history[asset][-10:]
            if cci is not None:
                self._cci_history[asset].append(cci)
                self._cci_history[asset] = self._cci_history[asset][-10:]

        # Append telemetry
        rsi_hist = self._rsi_history.get(asset, [])
        cci_hist = self._cci_history.get(asset, [])
        oteo_result["rsi_7"] = rsi_hist[-1] if rsi_hist else None
        oteo_result["cci_9"] = cci_hist[-1] if cci_hist else None
        oteo_result["rsi_slope"] = compute_slope(rsi_hist) if len(rsi_hist) >= 2 else 0.0
        oteo_result["cci9_slope"] = compute_slope(cci_hist) if len(cci_hist) >= 2 else 0.0
        return oteo_result

    def on_consider_signal(self, asset: str, price: float, oteo_result: Dict[str, Any], config: Any) -> Tuple[bool, str | None]:
        """Veto hook for Auto-Ghost. Returns (allow, reason)."""
        if not self.enabled:
            return True, None
        
        rsi = oteo_result.get("rsi_7")
        cci = oteo_result.get("cci_9")
        if rsi is None or cci is None:
            return True, None  # Insufficient data to veto — let it pass
        
        direction = oteo_result.get("recommended", "").upper()
        rsi_slope = oteo_result.get("rsi_slope", 0.0)
        cci_slope = oteo_result.get("cci9_slope", 0.0)
        
        # Check RSI extreme zone
        if direction == "CALL" and rsi > self.rsi_oversold:
            return False, f"rsi_cci_not_oversold_{rsi:.1f}"
        if direction == "PUT" and rsi < self.rsi_overbought:
            return False, f"rsi_cci_not_overbought_{rsi:.1f}"
        
        # Check slopes are parallel and sufficient
        if abs(rsi_slope) < self.min_slope or abs(cci_slope) < self.min_slope:
            return False, "rsi_cci_slope_weak"
        if (rsi_slope > 0) != (cci_slope > 0):
            return False, "rsi_cci_not_parallel"
        if direction == "CALL" and rsi_slope < 0:
            return False, "rsi_cci_wrong_direction"
        if direction == "PUT" and rsi_slope > 0:
            return False, "rsi_cci_wrong_direction"
        
        return True, None  # Confluence confirmed ✓
