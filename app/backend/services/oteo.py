"""
OTEO Indicator — OTC Tick Exhaustion Oscillator
Primary implementation for OTC SNIPER v3.

Score 0–100. >75 = high-probability reversion trade.
Warms up after ≥50 ticks (~50 seconds). No external history required.
"""
import time as _time
import numpy as np
from collections import deque
from typing import Dict, Any, Union


class OTEO:
    """
    OTC Tick Exhaustion Oscillator.
    """

    def __init__(self):
        self.ticks: deque = deque(maxlen=300)       # live prices
        self.timestamps: deque = deque(maxlen=300)  # parallel timestamps
        self._cooldown_remaining: int = 0
        self.COOLDOWN_TICKS: int = 30

    def update_tick(self, price: float, timestamp: float = None) -> Union[Dict[str, Any], float]:
        """
        Process a new tick price and return a scoring result.
        Returns:
            dict  — scoring result once warmed up (≥50 ticks).
            float — 50.0 neutral default during warmup period.
        """
        # Guard against NaN / Inf prices
        if not np.isfinite(price):
            return 50.0

        self.ticks.append(price)
        self.timestamps.append(timestamp if timestamp is not None else _time.time())

        # Warmup requires ≥50 ticks
        if len(self.ticks) < 50:
            return 50.0

        # Optimization: Single list conversion per tick
        all_ticks = list(self.ticks)
        recent = all_ticks[-50:]

        # 1. Velocity — time-aware (price change / elapsed seconds)
        ts_list = list(self.timestamps)
        time_delta = max(ts_list[-1] - ts_list[-50], 0.1)  # floor at 0.1s
        velocity = (recent[-1] - recent[0]) / time_delta

        # Macro trend (200-tick window)
        if len(all_ticks) >= 200:
            slow_velocity = (all_ticks[-1] - all_ticks[-200]) / max(time_delta * 4, 0.4)
        else:
            slow_velocity = 0.0

        # Multi-timeframe confirmation
        trend_aligned = (velocity > 0 and slow_velocity > 0) or (velocity < 0 and slow_velocity < 0)

        # 2. Z-score from tick buffer baseline
        # Baseline = all ticks except the most recent 20 (avoids self-reference)
        baseline = all_ticks[:-20] if len(all_ticks) > 20 else all_ticks
        mu = np.mean(baseline)
        sigma = float(np.std(baseline)) or 0.0001
        z_score = (price - mu) / sigma

        # 3. OTEO score — sigmoid of velocity × z-score product
        product = abs(velocity) * abs(z_score)

        # Volatility-adaptive thresholds
        if len(all_ticks) >= 100:
            rolling_vol = float(np.std(all_ticks[-100:]))
            baseline_vol = sigma
            vol_ratio = rolling_vol / max(baseline_vol, 0.0001)
            adaptive_center = 0.85 * max(0.5, min(2.0, vol_ratio))
        else:
            adaptive_center = 0.85

        raw_score = 100 * (1 - 1 / (1 + np.exp(-3.5 * (product - adaptive_center))))

        # Maturity weighting — dampens early scores when baseline is small.
        maturity = min(1.0, len(baseline) / 200.0)
        score = raw_score * maturity

        direction = "CALL" if velocity < 0 else "PUT"   # trade opposite momentum
        confidence = "HIGH" if score > 75 else "MEDIUM" if score > 55 else "LOW"

        # Suppress HIGH if trend-aligned
        if trend_aligned and confidence == "HIGH":
            confidence = "MEDIUM"

        # Apply cooldown
        if self._cooldown_remaining > 0:
            self._cooldown_remaining -= 1
            if confidence == "HIGH":
                confidence = "MEDIUM"

        if confidence == "HIGH" and self._cooldown_remaining == 0:
            self._cooldown_remaining = self.COOLDOWN_TICKS

        return {
            "oteo_score": round(score, 1),
            "recommended": direction,
            "confidence": confidence,
            "velocity": round(velocity, 6),
            "z_score": round(z_score, 2),
            "maturity": round(maturity, 2),
            "slow_velocity": round(slow_velocity, 6),
            "trend_aligned": trend_aligned,
        }
