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
        self._last_timestamp: float = 0.0
        self._push_snap_until: float = 0.0

    def update(self, timestamp: float, price: float) -> Dict[str, Any]:
        """
        Update detection state with new tick and return active flags.
        """
        # Guard against NaN / Inf prices
        if not np.isfinite(price):
            return {}

        self.price_history.append(price)
        if len(self.price_history) < 2:
            self._last_timestamp = timestamp
            return {}

        # calculate actual velocity per tick interval
        dt = max(timestamp - self._last_timestamp, 0.001)  # floor to 1ms
        vel = (price - self.price_history[-2]) / dt
        self._last_timestamp = timestamp
        self.velocities.append(vel)

        avg_vel = np.mean(self.velocities) if self.velocities else 0.0
        flags = {}

        # 1. Push & Snap: velocity spike vs rolling average
        # Memory added: if a massive spike happens, block for 15 seconds to let shock absorb
        if abs(vel) > 3 * max(abs(avg_vel), 0.0001):
            self._push_snap_until = timestamp + 15.0
            
        if timestamp < self._push_snap_until:
            flags["push_snap"] = True

        # 2. Pinning: price clustering at a tight level Over recent 20 ticks
        # Loosened: Check if the entire range (max - min) of the last 20 ticks is abnormally small
        recent_prices = list(self.price_history)[-20:]
        if len(recent_prices) >= 20:
            price_range = max(recent_prices) - min(recent_prices)
            avg_price = np.mean(recent_prices)
            # If the price hasn't moved more than 0.005% of its value in 20 ticks, it's pinned
            if price_range < (avg_price * 0.00005):
                flags["pinning"] = True

        return flags
