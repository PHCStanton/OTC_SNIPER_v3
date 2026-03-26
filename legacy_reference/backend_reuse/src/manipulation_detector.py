"""
Manipulation Detector — OTC SNIPER
Detects market manipulation patterns: Push & Snap, Pinning.
"""
import numpy as np
from collections import deque


class ManipulationDetector:
    """
    Detects OTC market manipulation tactics from live tick data.

    Patterns detected:
      - Push & Snap: Abnormal velocity spike vs rolling average.
      - Pinning:     Price clustering at a tight level over recent ticks.

    Args:
        timestamp (float): Unix timestamp of the tick (reserved for future
                           expiry-spike detection logic).
        price (float):     Current tick price.

    Returns:
        dict: Flags dict, e.g. {"push_snap": True} or {} if clean.
    """

    def __init__(self):
        self.velocities: deque = deque(maxlen=300)   # ~5 min buffer
        self.price_history: deque = deque(maxlen=300)

    def update(self, timestamp: float, price: float) -> dict:
        # Guard against NaN / Inf prices to prevent downstream calculation errors
        if not np.isfinite(price):
            return {}

        self.price_history.append(price)
        if len(self.price_history) < 2:
            return {}

        vel = (price - self.price_history[-2]) / 0.1   # velocity per 100ms
        self.velocities.append(vel)

        avg_vel = np.mean(self.velocities) if self.velocities else 0.0
        flags = {}

        # 1. Push & Snap: velocity spike vs rolling average
        #    Use abs(avg_vel) so a negative rolling average doesn't invert the threshold.
        if abs(vel) > 3 * max(abs(avg_vel), 0.0001):
            flags["push_snap"] = True

        # 2. Pinning: price clustering at a tight level
        recent_prices = list(self.price_history)[-20:]
        if len(set(round(p, 5) for p in recent_prices)) <= 2:
            flags["pinning"] = True

        # TODO: Expiry-spike detection (requires contract end time via timestamp)

        return flags
