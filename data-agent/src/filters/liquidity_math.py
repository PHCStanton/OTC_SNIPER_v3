"""
Sigmoid Liquidity & Tick Density Mathematical Calculations.

Aligns 1:1 with the core OTC SNIPER MarketContextEngine and Backtesting UnifiedEngine.
Centered on the empirical Pocket Option OTC tick rate of ~120 ticks/min (≈0.5 s/tick).
Prevents hard-saturation at 100% and provides headroom for broker tick bursts.
"""

from __future__ import annotations

import math
from typing import Tuple

# Empirical constants calibrated for Pocket Option OTC baseline (~120 ticks/min)
LIQ_MIDPOINT: float = 120.0   # ticks/min mapped to exactly 50.0%
LIQ_STEEPNESS: float = 4.0    # sigmoid transition sharpness
DEFAULT_WARMUP_TICKS: int = 30

# Discrete liquidity classification thresholds
LOW_LIQUIDITY_THRESHOLD: float = 30.0    # < 30.0% (corresponds to < ~60 ticks/min)
HIGH_LIQUIDITY_THRESHOLD: float = 70.0   # >= 70.0% (corresponds to > ~180 ticks/min)


def calculate_sigmoid_liquidity(
    tick_frequency: float,
    buffer_len: int = 30,
    min_warmup_buffer: int = DEFAULT_WARMUP_TICKS,
) -> Tuple[float, str]:
    """
    Compute Sigmoid Liquidity Score (0.0 to 100.0) and discrete Liquidity Level.

    Formula:
        x = (freq - 120.0) / 120.0
        liq_base = 1.0 / (1.0 + exp(-4.0 * x))
        buffer_ratio = min(1.0, buffer_len / min_warmup_buffer)
        liq_score = (liq_base * buffer_ratio) * 100.0

    Mapping:
        freq = 0   -> ~0.0% (or ~2% base before buffer ratio)
        freq = 60  -> ~26.9%  (LOW)
        freq = 120 -> 50.0%   (MEDIUM - normal Pocket Option OTC)
        freq = 130 -> ~53.3%  (MEDIUM - optimal winning profile)
        freq = 180 -> ~73.1%  (HIGH)
        freq = 300 -> ~88.1%  (HIGH - headroom preserved, no clamp)

    Returns:
        tuple[float, str]: (liquidity_score_pct, liquidity_level)
                           where liquidity_level is 'LOW', 'MEDIUM', or 'HIGH'.
    """
    freq = float(tick_frequency or 0.0)
    if freq <= 0.0:
        return 0.0, "LOW"

    # Normalized deviation from midpoint
    x = (freq - LIQ_MIDPOINT) / LIQ_MIDPOINT
    
    # Sigmoid function
    try:
        liq_base = 1.0 / (1.0 + math.exp(-LIQ_STEEPNESS * x))
    except OverflowError:
        liq_base = 0.0 if x < 0 else 1.0

    # Warmup buffer dampening to avoid premature HIGH score on initial startup
    buf_len = max(0, int(buffer_len))
    warmup_target = max(1, int(min_warmup_buffer))
    buffer_ratio = min(1.0, buf_len / warmup_target)

    score_pct = round(liq_base * buffer_ratio * 100.0, 1)

    if score_pct >= HIGH_LIQUIDITY_THRESHOLD:
        level = "HIGH"
    elif score_pct >= LOW_LIQUIDITY_THRESHOLD:
        level = "MEDIUM"
    else:
        level = "LOW"

    return score_pct, level


def classify_liquidity_level(score: float) -> str:
    """Classify a numeric liquidity score into LOW, MEDIUM, or HIGH."""
    val = float(score or 0.0)
    if val >= HIGH_LIQUIDITY_THRESHOLD:
        return "HIGH"
    if val >= LOW_LIQUIDITY_THRESHOLD:
        return "MEDIUM"
    return "LOW"
