"""
Pure indicator math functions for OTC SNIPER.
Stateless — each function takes a price list and returns computed values.
"""
import numpy as np

def compute_rsi(closes: list[float], period: int = 7) -> float | None:
    """Wilder RSI. Returns 0-100 or None if insufficient data."""
    if len(closes) < period + 1:
        return None
    
    # Calculate daily changes
    deltas = np.diff(closes[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    
    avg_gain = float(np.mean(gains))
    avg_loss = float(np.mean(losses))
    
    if avg_loss < 1e-12:
        return 100.0
    
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def compute_cci(highs: list[float], lows: list[float], closes: list[float], period: int = 9) -> float | None:
    """Standard CCI. Returns float or None if insufficient data."""
    if len(closes) < period:
        return None
        
    # Standard CCI typical price: (High + Low + Close) / 3
    typical = [(h + l + c) / 3.0 for h, l, c in zip(highs[-period:], lows[-period:], closes[-period:])]
    
    sma = sum(typical) / period
    mean_dev = sum(abs(tp - sma) for tp in typical) / period
    
    if mean_dev < 1e-12:
        return 0.0
        
    return (typical[-1] - sma) / (0.015 * mean_dev)

def compute_slope(series: list[float], window: int = 3) -> float:
    """Slope of last `window` values. Positive = rising, negative = falling."""
    if len(series) < 2:
        return 0.0
    effective = series[-min(window, len(series)):]
    if len(effective) < 2:
        return 0.0
    return (effective[-1] - effective[0]) / max(1, len(effective) - 1)
