"""
Manipulation Detector — OTC SNIPER v3
Detects market manipulation patterns: Push & Snap, Pinning.
"""
import numpy as np
from collections import deque
from typing import Dict, Any


class ManipulationDetector:
    """
    Detects OTC market manipulation tactics from live tick data.
    """

    def __init__(self):
        self.velocities: deque = deque(maxlen=300)
        self.price_history: deque = deque(maxlen=300)

    def update(self, timestamp: float, price: float) -> Dict[str, Any]:
        """
        Update detection state with new tick and return active flags.
        """
        # Guard against NaN / Inf prices
        if not np.isfinite(price):
            return {}

        self.price_history.append(price)
        if len(self.price_history) < 2:
            return {}

        # velocity per 100ms (approx)
        vel = (price - self.price_history[-2]) / 0.1
        self.velocities.append(vel)

        avg_vel = np.mean(self.velocities) if self.velocities else 0.0
        flags = {}

        # 1. Push & Snap: velocity spike vs rolling average
        if abs(vel) > 3 * max(abs(avg_vel), 0.0001):
            flags["push_snap"] = True

        # 2. Pinning: price clustering at a tight level Over recent 20 ticks
        recent_prices = list(self.price_history)[-20:]
        if len(set(round(p, 5) for p in recent_prices)) <= 2:
            flags["pinning"] = True

        return flags
