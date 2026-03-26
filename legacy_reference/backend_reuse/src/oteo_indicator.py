"""
OTEO Indicator — OTC Tick Exhaustion Oscillator
Primary implementation used by the streaming server.

Score 0–100. >75 = high-probability reversion trade.
Warms up after ≥50 ticks (~50 seconds). No external history required.

Z-score is computed from the tick buffer baseline (all ticks except the most
recent 20) to avoid self-reference.

A1 Improvements (2026-03-21):
  - O-1: Time-aware velocity using a timestamps deque (no longer fixed /5.0).
  - O-2: Maturity weighting dampens early scores when baseline is small.
  - O-3: Single list(self.ticks) conversion per tick (was 3 separate copies).
"""
import time as _time
import numpy as np
from collections import deque


class OTEO:
    """
    OTC Tick Exhaustion Oscillator.

    Call `update_tick(price, timestamp)` for each live price tick.
    Produces real scores after ≥50 ticks (~50 seconds at 1 tick/sec).
    """

    def __init__(self):
        self.ticks: deque = deque(maxlen=300)       # live prices
        self.timestamps: deque = deque(maxlen=300)  # A1-O1: parallel timestamps
        self._cooldown_remaining: int = 0  # B3: Cooldown
        self.COOLDOWN_TICKS: int = 30      # B3: Configurable cooldown ticks

    def update_tick(self, price: float, timestamp: float = None) -> dict | float:
        """
        Process a new tick price and return a scoring result.

        Args:
            price:     Current price (must be finite).
            timestamp: Unix timestamp of the tick. Defaults to time.time() if
                       not provided (used for time-aware velocity calculation).

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

        # A1-O3: Single list conversion — reused for all calculations below
        all_ticks = list(self.ticks)
        recent = all_ticks[-50:]

        # 1. Velocity — A1-O1: time-aware (price change / elapsed seconds)
        if len(self.timestamps) >= 50:
            ts_list = list(self.timestamps)
            time_delta = max(ts_list[-1] - ts_list[-50], 0.1)  # floor at 0.1s
        else:
            time_delta = 5.0  # fallback when timestamps unavailable

        velocity = (recent[-1] - recent[0]) / time_delta

        # B1: Slow velocity — 200-tick window (macro trend)
        if len(all_ticks) >= 200:
            slow_velocity = (all_ticks[-1] - all_ticks[-200]) / max(time_delta * 4, 0.4)
        else:
            slow_velocity = 0.0  # not enough data for macro trend

        # B1: Multi-timeframe confirmation
        trend_aligned = (velocity > 0 and slow_velocity > 0) or (velocity < 0 and slow_velocity < 0)

        # 2. Z-score from tick buffer baseline
        #    Baseline = all ticks except the most recent 20 (avoids self-reference)
        baseline = all_ticks[:-20] if len(all_ticks) > 20 else all_ticks
        mu = np.mean(baseline)
        sigma = float(np.std(baseline)) or 0.0001
        z_score = (price - mu) / sigma

        # 3. OTEO score — sigmoid of velocity × z-score product
        product = abs(velocity) * abs(z_score)

        # B4: Volatility-adaptive thresholds
        if len(all_ticks) >= 100:
            rolling_vol = float(np.std(all_ticks[-100:]))
            baseline_vol = sigma
            vol_ratio = rolling_vol / max(baseline_vol, 0.0001)
            adaptive_center = 0.85 * max(0.5, min(2.0, vol_ratio))  # clamp between 0.425 and 1.70
        else:
            adaptive_center = 0.85  # fallback

        raw_score = 100 * (1 - 1 / (1 + np.exp(-3.5 * (product - adaptive_center))))

        # A1-O2: Maturity weighting — dampens early scores when baseline is small.
        # Baseline grows from 30 ticks (at warmup boundary) to 280 ticks (full buffer).
        # maturity reaches 1.0 at 200 baseline ticks (~250 total ticks).
        maturity = min(1.0, len(baseline) / 200.0)
        score = raw_score * maturity

        direction = "CALL" if velocity < 0 else "PUT"   # trade opposite momentum
        confidence = "HIGH" if score > 75 else "MEDIUM" if score > 55 else "LOW"

        # B1: Suppress HIGH if trend-aligned
        if trend_aligned and confidence == "HIGH":
            confidence = "MEDIUM"

        # B3: Apply cooldown
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
            "maturity": round(maturity, 2),  # A1-O2: exposed for signal logger + frontend
            "slow_velocity": round(slow_velocity, 6),  # B1
            "trend_aligned": trend_aligned,  # B1
        }

    def update_history(self, close_price: float) -> None:
        """
        No-op kept for backward compatibility.

        Previously accepted 1-minute close prices for z-score baseline.
        OTEO now computes z-score from the live tick buffer alone (FIX-3).
        """
