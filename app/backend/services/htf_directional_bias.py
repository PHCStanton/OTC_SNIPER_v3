from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("app.backend.services.htf_directional_bias")


@dataclass
class HTFCandle:
    start_ts: int
    open: float
    high: float
    low: float
    close: float
    volume: int = 1


class HTFDirectionalBiasEngine:
    """
    Multi-Scale Higher-Timeframe (HTF) and Micro-Tick Flow Directional Bias Engine.
    Synthesizes 5m and 15m candles from in-memory 1m candle buffers and calculates
    rolling tick flow pressure to evaluate directional confluence for trading setups.
    """

    _instance: Optional[HTFDirectionalBiasEngine] = None

    @classmethod
    def get_instance(cls) -> HTFDirectionalBiasEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def resample_1m_candles(candles: List[Any], timeframe_minutes: int) -> List[HTFCandle]:
        """Resample a list of 1-minute candles into N-minute candles (e.g. 5m, 15m)."""
        if not candles or timeframe_minutes <= 1:
            return []

        tf_seconds = timeframe_minutes * 60
        grouped: Dict[int, List[Any]] = {}

        for c in candles:
            # Handle both dataclass and dict forms
            ts = c.start_ts if hasattr(c, "start_ts") else c.get("start_ts", 0)
            c_open = c.open if hasattr(c, "open") else c.get("open", 0.0)
            c_high = c.high if hasattr(c, "high") else c.get("high", 0.0)
            c_low = c.low if hasattr(c, "low") else c.get("low", 0.0)
            c_close = c.close if hasattr(c, "close") else c.get("close", 0.0)

            bucket_ts = int(ts // tf_seconds) * tf_seconds
            grouped.setdefault(bucket_ts, []).append((ts, c_open, c_high, c_low, c_close))

        resampled: List[HTFCandle] = []
        for bucket_ts in sorted(grouped.keys()):
            items = sorted(grouped[bucket_ts], key=lambda x: x[0])
            open_p = items[0][1]
            high_p = max(x[2] for x in items)
            low_p = min(x[3] for x in items)
            close_p = items[-1][4]

            resampled.append(
                HTFCandle(
                    start_ts=bucket_ts,
                    open=open_p,
                    high=high_p,
                    low=low_p,
                    close=close_p,
                    volume=len(items),
                )
            )

        return resampled

    @staticmethod
    def compute_ema(prices: List[float], period: int) -> List[float]:
        """Compute exponential moving average for a series of prices."""
        if not prices or period <= 0:
            return []
        if len(prices) < period:
            period = max(2, len(prices))

        multiplier = 2.0 / (period + 1.0)
        ema = [prices[0]]
        for p in prices[1:]:
            ema.append((p - ema[-1]) * multiplier + ema[-1])
        return ema

    def compute_htf_trend(self, candles_1m: List[Any]) -> Dict[str, Any]:
        """
        Compute higher-timeframe trend status across synthetic 5m and 15m timeframes.
        """
        if len(candles_1m) < 10:
            return {
                "htf_trend": "NEUTRAL",
                "trend_strength": 0.0,
                "trend_5m": "NEUTRAL",
                "trend_15m": "NEUTRAL",
                "candles_5m_count": 0,
                "candles_15m_count": 0,
            }

        candles_5m = self.resample_1m_candles(candles_1m, timeframe_minutes=5)
        candles_15m = self.resample_1m_candles(candles_1m, timeframe_minutes=15)

        # 5m Trend Analysis
        trend_5m = "NEUTRAL"
        if len(candles_5m) >= 3:
            c5_closes = [c.close for c in candles_5m]
            ema_fast = self.compute_ema(c5_closes, period=5)
            ema_slow = self.compute_ema(c5_closes, period=13)
            latest_c5 = candles_5m[-1]

            if ema_fast[-1] > ema_slow[-1] and latest_c5.close > latest_c5.open:
                trend_5m = "BULLISH"
            elif ema_fast[-1] < ema_slow[-1] and latest_c5.close < latest_c5.open:
                trend_5m = "BEARISH"

        # 15m Trend Analysis
        trend_15m = "NEUTRAL"
        if len(candles_15m) >= 3:
            c15_closes = [c.close for c in candles_15m]
            ema_fast = self.compute_ema(c15_closes, period=3)
            ema_slow = self.compute_ema(c15_closes, period=6)
            latest_c15 = candles_15m[-1]

            if ema_fast[-1] > ema_slow[-1] and latest_c15.close > latest_c15.open:
                trend_15m = "BULLISH"
            elif ema_fast[-1] < ema_slow[-1] and latest_c15.close < latest_c15.open:
                trend_15m = "BEARISH"
        elif len(candles_15m) == 2:
            latest_c15 = candles_15m[-1]
            if candles_15m[-1].close > candles_15m[0].close and latest_c15.close > latest_c15.open:
                trend_15m = "BULLISH"
            elif candles_15m[-1].close < candles_15m[0].close and latest_c15.close < latest_c15.open:
                trend_15m = "BEARISH"

        # Composite Macro Trend
        if trend_5m == "BULLISH" and trend_15m == "BULLISH":
            macro_trend = "STRONG_BULLISH"
            strength = 85.0
        elif trend_5m == "BEARISH" and trend_15m == "BEARISH":
            macro_trend = "STRONG_BEARISH"
            strength = 85.0
        elif trend_5m == "BULLISH" or trend_15m == "BULLISH":
            macro_trend = "BULLISH"
            strength = 60.0
        elif trend_5m == "BEARISH" or trend_15m == "BEARISH":
            macro_trend = "BEARISH"
            strength = 60.0
        else:
            macro_trend = "NEUTRAL"
            strength = 50.0

        return {
            "htf_trend": macro_trend,
            "trend_strength": strength,
            "trend_5m": trend_5m,
            "trend_15m": trend_15m,
            "candles_5m_count": len(candles_5m),
            "candles_15m_count": len(candles_15m),
        }

    @staticmethod
    def compute_tick_flow_ratio(
        ticks: List[Dict[str, Any]], window_seconds: float = 60.0, current_ts: float | None = None
    ) -> float:
        """
        Compute the ratio of upward ticks to total ticks over a rolling lookback window.
        Returns a percentage value 0.0 to 100.0 (50.0 is balanced).
        """
        if not ticks or len(ticks) < 2:
            return 50.0

        now = current_ts if current_ts is not None else float(ticks[-1].get("t", 0.0) or ticks[-1].get("timestamp", 0.0))
        cutoff = now - window_seconds

        window_ticks = [
            t for t in ticks
            if float(t.get("t", 0.0) or t.get("timestamp", 0.0)) >= cutoff
        ]

        if len(window_ticks) < 2:
            return 50.0

        up_count = 0
        down_count = 0

        for i in range(1, len(window_ticks)):
            p_prev = float(window_ticks[i - 1].get("p", 0.0) or window_ticks[i - 1].get("price", 0.0))
            p_curr = float(window_ticks[i].get("p", 0.0) or window_ticks[i].get("price", 0.0))

            if p_curr > p_prev:
                up_count += 1
            elif p_curr < p_prev:
                down_count += 1

        total_directional = up_count + down_count
        if total_directional == 0:
            return 50.0

        return round((up_count / total_directional) * 100.0, 1)

    def evaluate_directional_confluence(
        self,
        asset: str,
        direction: str,
        candles_1m: List[Any],
        recent_ticks: List[Dict[str, Any]] | None = None,
        current_ts: float | None = None,
    ) -> Dict[str, Any]:
        """
        Evaluate full directional confluence combining synthetic HTF trend and rolling tick flow.
        """
        dir_upper = direction.upper()
        htf_data = self.compute_htf_trend(candles_1m)
        tick_flow_60s = self.compute_tick_flow_ratio(recent_ticks or [], window_seconds=60.0, current_ts=current_ts)
        # L1 resolution: scoring deliberately uses ONLY the 60s micro-flow window (the
        # horizon-matched signal). The 300s macro-flow is computed for reporting/telemetry
        # in the result dict below and must NOT be added to the confluence score without
        # recalibrating the calibrated_bayesian_floor thresholds.
        tick_flow_300s = self.compute_tick_flow_ratio(recent_ticks or [], window_seconds=300.0, current_ts=current_ts)

        macro_trend = htf_data["htf_trend"]
        is_call = dir_upper == "CALL"

        # Confluence Scoring (-100 to +100)
        score = 0.0

        # HTF Trend contribution (+40 / -40)
        if "BULLISH" in macro_trend:
            score += 40.0 if is_call else -40.0
        elif "BEARISH" in macro_trend:
            score += -40.0 if is_call else 40.0

        # Tick Flow contribution (+60 / -60)
        # 50% is neutral; 65% is strong up; 35% is strong down
        tick_delta_60 = (tick_flow_60s - 50.0) * 2.0  # Range -100 to +100
        score += (tick_delta_60 * 0.6) if is_call else (-tick_delta_60 * 0.6)

        score = max(-100.0, min(100.0, round(score, 1)))

        # Alignment classification
        if score >= 35.0:
            status = "STRONG_ALIGNMENT"
            calibrated_floor = 0.520  # Lower Bayesian threshold (52.0%) due to strong confluence
            veto = False
            veto_reason = None
        elif score >= 0.0:
            status = "ALIGNED"
            calibrated_floor = 0.535  # Standard calibrated Bayesian threshold (53.5%)
            veto = False
            veto_reason = None
        elif score >= -40.0:
            status = "COUNTER_TREND"
            calibrated_floor = 0.555  # Higher Bayesian threshold (55.5%) required for counter-trend
            veto = False
            veto_reason = None
        else:
            status = "DIVERGENT"
            calibrated_floor = 0.560
            # Veto if tick flow is actively collapsing against direction
            if (is_call and tick_flow_60s < 38.0) or (not is_call and tick_flow_60s > 62.0):
                veto = True
                veto_reason = f"Adverse micro tick flow ({tick_flow_60s}%) opposing {dir_upper} setup"
            else:
                veto = False
                veto_reason = None

        return {
            "asset": asset,
            "direction": dir_upper,
            "confluence_status": status,
            "confluence_score": score,
            "htf_trend": macro_trend,
            "trend_5m": htf_data["trend_5m"],
            "trend_15m": htf_data["trend_15m"],
            "tick_flow_60s": tick_flow_60s,
            "tick_flow_300s": tick_flow_300s,
            "calibrated_bayesian_floor": calibrated_floor,
            "veto": veto,
            "veto_reason": veto_reason,
        }
