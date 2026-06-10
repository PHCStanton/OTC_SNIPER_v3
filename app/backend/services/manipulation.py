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
        self._push_snap_trigger_time: float = 0.0
        self._push_snap_initial_severity: float = 0.0

    def update(self, timestamp: float, price: float) -> Dict[str, float]:
        """
        Update detection state with new tick and return active severity scores.
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

        # MAV calculation (average of absolute values) to prevent cancellation
        mav = np.mean([abs(v) for v in self.velocities]) if self.velocities else 0.0
        flags = {}

        # 1. Push & Snap: velocity spike vs MAV with exponential decay
        ratio = abs(vel) / max(mav, 0.0001)
        if ratio > 3.0:
            self._push_snap_trigger_time = timestamp
            # Scale severity: spike of 3.0 -> 0.3 severity, spike of 10.0+ -> 1.0 severity
            self._push_snap_initial_severity = max(0.3, min(1.0, ratio / 10.0))

        # Check decay window (exponential decay over time with tau = 5.0 seconds)
        time_elapsed = timestamp - self._push_snap_trigger_time
        if time_elapsed >= 0.0:
            severity = self._push_snap_initial_severity * np.exp(-time_elapsed / 5.0)
            if severity > 0.01:
                flags["push_snap"] = round(float(severity), 3)

        # 2. Pinning: price clustering at a tight level Over recent 20 ticks
        recent_prices = list(self.price_history)[-20:]
        if len(recent_prices) >= 20:
            price_range = max(recent_prices) - min(recent_prices)
            avg_price = np.mean(recent_prices)
            threshold = avg_price * 0.00005
            
            # Continuous severity from 0.0 (at threshold border) to 1.0 (perfect flatline)
            if price_range < threshold:
                pinning_severity = 1.0 - (price_range / threshold)
                if pinning_severity > 0.01:
                    flags["pinning"] = round(float(pinning_severity), 3)

        return flags
