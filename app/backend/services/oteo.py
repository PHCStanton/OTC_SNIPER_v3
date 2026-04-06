"""
OTEO Indicator — OTC Tick Exhaustion Oscillator
Primary implementation for OTC SNIPER v3.

Score 0–100. >75 = high-probability reversion trade.
Warms up after ≥50 ticks (~50 seconds). No external history required.
"""
from dataclasses import dataclass
import time as _time
from collections import deque
from typing import Any, Dict, Union

import numpy as np


@dataclass(frozen=True)
class OTEOConfig:
    buffer_size: int = 300
    warmup_ticks: int = 50
    pressure_window: int = 24
    macro_window: int = 120
    baseline_exclusion: int = 20
    full_maturity_baseline: int = 200
    volatility_window: int = 100
    cooldown_ticks: int = 30
    score_center: float = 0.85
    score_slope: float = 3.5
    min_abs_z_score: float = 0.35
    min_pressure_pct: float = 12.0


class OTEO:
    """
    OTC Tick Exhaustion Oscillator.
    """

    def __init__(self, config: OTEOConfig | None = None):
        self.config = config or OTEOConfig()
        self.ticks: deque = deque(maxlen=self.config.buffer_size)
        self.timestamps: deque = deque(maxlen=self.config.buffer_size)
        self._cooldown_remaining = 0
        self._last_signal_direction: str | None = None
        self._last_signal_confidence: str | None = None

    def seed_tick(self, price: float, timestamp: float | None = None) -> None:
        numeric_price = float(price)
        if not np.isfinite(numeric_price):
            return
        self.ticks.append(numeric_price)
        self.timestamps.append(timestamp if timestamp is not None else _time.time())

    def _weighted_pressure(self, prices: list[float], timestamps: list[float], window: int) -> tuple[float, float]:
        if len(prices) < 2:
            return 0.0, 0.0

        effective_window = min(window, len(prices) - 1)
        recent_prices = prices[-(effective_window + 1):]
        recent_timestamps = timestamps[-(effective_window + 1):]

        deltas = np.diff(np.asarray(recent_prices, dtype=float))
        if deltas.size == 0:
            return 0.0, 0.0

        weights = np.arange(1, deltas.size + 1, dtype=float)
        normalizer = float(weights.sum()) or 1.0
        elapsed = max(float(recent_timestamps[-1] - recent_timestamps[0]), 0.1)

        weighted_delta = float(np.dot(weights, deltas) / normalizer)
        pressure = weighted_delta * deltas.size / elapsed

        absolute_motion = float(np.dot(weights, np.abs(deltas)) / normalizer)
        pressure_pct = 0.0 if absolute_motion <= 1e-12 else 100.0 * weighted_delta / absolute_motion
        pressure_pct = max(-100.0, min(100.0, pressure_pct))
        return pressure, pressure_pct

    def _z_score(self, prices: list[float], price: float) -> tuple[float, float]:
        baseline = prices[:-self.config.baseline_exclusion] if len(prices) > self.config.baseline_exclusion else prices
        mu = float(np.mean(baseline))
        sigma = float(np.std(baseline)) or 0.0001
        return (price - mu) / sigma, sigma

    def update_tick(self, price: float, timestamp: float = None) -> Union[Dict[str, Any], float]:
        numeric_price = float(price)
        if not np.isfinite(numeric_price):
            return 50.0

        self.seed_tick(numeric_price, timestamp=timestamp)

        if len(self.ticks) < self.config.warmup_ticks:
            return 50.0

        prices = list(self.ticks)
        timestamps = list(self.timestamps)

        velocity, pressure_pct = self._weighted_pressure(prices, timestamps, self.config.pressure_window)
        slow_velocity, _ = self._weighted_pressure(prices, timestamps, self.config.macro_window)
        trend_aligned = (velocity > 0 and slow_velocity > 0) or (velocity < 0 and slow_velocity < 0)

        z_score, sigma = self._z_score(prices, numeric_price)
        aligned_product = max(0.0, velocity * z_score)

        if len(prices) >= self.config.volatility_window:
            rolling_vol = float(np.std(prices[-self.config.volatility_window:]))
            vol_ratio = rolling_vol / max(sigma, 0.0001)
            adaptive_center = self.config.score_center * max(0.5, min(2.0, vol_ratio))
        else:
            adaptive_center = self.config.score_center

        raw_score = 100.0 * (1.0 - 1.0 / (1.0 + np.exp(-self.config.score_slope * (aligned_product - adaptive_center))))
        baseline_size = max(0, len(prices) - self.config.baseline_exclusion)
        maturity = min(1.0, baseline_size / float(self.config.full_maturity_baseline))
        score = raw_score * maturity

        direction = "NEUTRAL"
        if aligned_product > 0 and abs(z_score) >= self.config.min_abs_z_score and abs(pressure_pct) >= self.config.min_pressure_pct:
            direction = "CALL" if velocity < 0 else "PUT"

        confidence = "HIGH" if score > 75 else "MEDIUM" if score > 55 else "LOW"
        if direction == "NEUTRAL":
            confidence = "LOW"
        elif trend_aligned and confidence == "HIGH":
            confidence = "MEDIUM"

        cooldown_active = self._cooldown_remaining > 0
        if cooldown_active:
            self._cooldown_remaining -= 1

        same_direction_repeat = direction in {"CALL", "PUT"} and direction == self._last_signal_direction
        actionable = (
            direction in {"CALL", "PUT"}
            and confidence in {"HIGH", "MEDIUM"}
            and not (cooldown_active and same_direction_repeat)
            and (not same_direction_repeat or confidence != self._last_signal_confidence)
        )

        if actionable:
            self._last_signal_direction = direction
            self._last_signal_confidence = confidence
            if confidence == "HIGH":
                self._cooldown_remaining = self.config.cooldown_ticks
        elif confidence == "LOW" or direction == "NEUTRAL":
            self._last_signal_direction = None
            self._last_signal_confidence = None

        return {
            "oteo_score": round(score, 1),
            "recommended": direction,
            "confidence": confidence,
            "velocity": round(velocity, 6),
            "pressure_pct": round(pressure_pct, 1),
            "z_score": round(z_score, 2),
            "maturity": round(maturity, 2),
            "slow_velocity": round(slow_velocity, 6),
            "trend_aligned": trend_aligned,
            "actionable": actionable,
            "stretch_alignment": round(aligned_product, 6),
        }
