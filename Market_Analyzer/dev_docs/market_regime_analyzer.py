# Market_Analyzer/market_regime_analyzer.py
"""
Market Regime Analyzer — Phase 1 Core Engine
============================================
Classifies market conditions from 1-minute candle data into 5 regimes:
  STRONG_TREND      — High ADX, clear directional movement, best for momentum strategies.
  TREND_PULLBACK    — Main trend intact, short-term counter-move detected.
  RANGE_BOUND       — Price oscillating between S/R, mean-reversion setups viable.
  CHOP_WHIPSAW      — High reversal density, low directional efficiency — AVOID.
  INSUFFICIENT_DATA — Not enough candles for reliable regime computation.

Design principles (adapted from Market_Condition_Analyzer_Plan_26-04-16.md):
  - No AI dependency.
  - Fast-fail on bad input.
  - Fully vectorized with numpy for backtest-scale performance.
  - Conservative stance: when uncertain, lean toward CHOP or INSUFFICIENT_DATA.
  - Works on candle OHLCV objects — no raw tick data required.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# Enums & Data Structures
# ---------------------------------------------------------------------------

class MarketRegime(Enum):
    STRONG_TREND      = "STRONG_TREND"
    TREND_PULLBACK    = "TREND_PULLBACK"
    RANGE_BOUND       = "RANGE_BOUND"
    CHOP_WHIPSAW      = "CHOP_WHIPSAW"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class RegimeResult:
    """
    Full output for a single regime classification.
    Suitable for attaching to every trade record in the backtester.
    """
    regime:            MarketRegime
    confidence:        float          # 0.0 – 1.0
    tradability_score: int            # 0 – 100  (mirrors OTC Sniper plan scoring)
    trend_direction:   str            # "UP" | "DOWN" | "NEUTRAL"
    flags:             List[str]      = field(default_factory=list)
    metrics:           dict           = field(default_factory=dict)

    # ── Convenience ──────────────────────────────────────────────────────
    @property
    def is_tradable(self) -> bool:
        return self.tradability_score >= 40

    @property
    def label(self) -> str:
        return self.regime.value


# ---------------------------------------------------------------------------
# Pre-computed series container
# ---------------------------------------------------------------------------

@dataclass
class RegimeSeries:
    """
    Holds a pre-computed array of RegimeResult objects — one per candle.
    Built once at the start of a backtest run; indexed cheaply thereafter.
    """
    results: List[RegimeResult]
    candle_count: int

    def at(self, candle_index: int) -> RegimeResult:
        """Return the regime for the candle at candle_index (0-based)."""
        if candle_index < 0 or candle_index >= self.candle_count:
            return _insufficient_data_result()
        return self.results[candle_index]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _insufficient_data_result() -> RegimeResult:
    return RegimeResult(
        regime=MarketRegime.INSUFFICIENT_DATA,
        confidence=1.0,
        tradability_score=0,
        trend_direction="NEUTRAL",
        flags=["INSUFFICIENT_DATA"],
        metrics={},
    )


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _extract_arrays(candles):
    """Extract numpy price arrays from a list of Candle objects."""
    highs  = np.array([c.high  for c in candles], dtype=np.float64)
    lows   = np.array([c.low   for c in candles], dtype=np.float64)
    closes = np.array([c.close for c in candles], dtype=np.float64)
    opens  = np.array([c.open  for c in candles], dtype=np.float64)
    return highs, lows, closes, opens


# ---------------------------------------------------------------------------
# Indicator Calculations (all vectorized)
# ---------------------------------------------------------------------------

def compute_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                period: int = 14) -> np.ndarray:
    """
    Average True Range — full rolling series.
    Returns array of same length as inputs; first (period) values are NaN.
    """
    n = len(closes)
    if n < 2:
        return np.full(n, np.nan)

    prev_closes = np.empty(n)
    prev_closes[0] = closes[0]
    prev_closes[1:] = closes[:-1]

    tr = np.maximum(
        highs - lows,
        np.maximum(
            np.abs(highs - prev_closes),
            np.abs(lows  - prev_closes)
        )
    )

    atr = np.full(n, np.nan)
    if n >= period:
        atr[period - 1] = np.mean(tr[:period])
        for i in range(period, n):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

    return atr


def compute_adx(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                period: int = 14):
    """
    Wilder's ADX (+DI, -DI).
    Returns (adx_series, plus_di_series, minus_di_series) — all same length.
    Values before (2*period) are NaN.
    """
    n = len(closes)
    if n < 2:
        nan = np.full(n, np.nan)
        return nan, nan, nan

    # True Range
    prev_closes = np.empty(n)
    prev_closes[0] = closes[0]
    prev_closes[1:] = closes[:-1]

    tr = np.maximum(
        highs - lows,
        np.maximum(np.abs(highs - prev_closes), np.abs(lows - prev_closes))
    )

    # Directional movement
    up_move   = highs[1:]  - highs[:-1]
    down_move = lows[:-1]  - lows[1:]

    plus_dm  = np.where((up_move > down_move) & (up_move > 0), up_move,  0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    # Pad to original length
    plus_dm  = np.concatenate([[0.0], plus_dm])
    minus_dm = np.concatenate([[0.0], minus_dm])

    # Wilder smoothing
    def wilder_smooth(arr: np.ndarray, p: int) -> np.ndarray:
        out = np.full(n, np.nan)
        if n >= p:
            out[p - 1] = np.sum(arr[:p])
            for i in range(p, n):
                out[i] = out[i - 1] - (out[i - 1] / p) + arr[i]
        return out

    smooth_tr   = wilder_smooth(tr,       period)
    smooth_pdm  = wilder_smooth(plus_dm,  period)
    smooth_mdm  = wilder_smooth(minus_dm, period)

    plus_di  = np.where(smooth_tr > 0, 100 * smooth_pdm / smooth_tr, 0.0)
    minus_di = np.where(smooth_tr > 0, 100 * smooth_mdm / smooth_tr, 0.0)

    # DX → ADX
    di_sum  = plus_di + minus_di
    dx      = np.where(di_sum > 0, 100 * np.abs(plus_di - minus_di) / di_sum, 0.0)

    adx = np.full(n, np.nan)
    start = 2 * period - 1
    if n > start:
        adx[start] = np.nanmean(dx[period - 1: start + 1])
        for i in range(start + 1, n):
            adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period

    return adx, plus_di, minus_di


def compute_directional_efficiency(closes: np.ndarray, window: int = 20) -> np.ndarray:
    """
    Directional Efficiency = |net_move| / total_path over `window` candles.
    Range 0–1. 1 = perfect trend, 0 = pure random walk / chop.
    Returns a rolling series (NaN for first `window` elements).
    """
    n = len(closes)
    result = np.full(n, np.nan)
    for i in range(window, n):
        segment = closes[i - window: i + 1]
        net_move  = abs(segment[-1] - segment[0])
        path_sum  = np.sum(np.abs(np.diff(segment)))
        result[i] = net_move / path_sum if path_sum > 0 else 0.0
    return result


def compute_reversal_density(closes: np.ndarray, window: int = 10) -> np.ndarray:
    """
    Number of direction changes (sign flips in tick-to-tick closes) per `window` candles.
    Normalized to [0, 1] where 1 = reversal every candle.
    Returns rolling series.
    """
    n = len(closes)
    result = np.full(n, np.nan)
    if n < 2:
        return result

    moves = np.sign(np.diff(closes))          # +1, 0, -1
    # Count sign changes (ignore zeros)
    for i in range(window, n):
        seg = moves[i - window: i]
        seg_nz = seg[seg != 0]
        if len(seg_nz) < 2:
            result[i] = 0.0
        else:
            flips = np.sum(seg_nz[1:] != seg_nz[:-1])
            result[i] = flips / (len(seg_nz) - 1)
    return result


def compute_range_score(highs: np.ndarray, lows: np.ndarray,
                         closes: np.ndarray, window: int = 20) -> np.ndarray:
    """
    Measures how well price oscillates inside a bound range.
    Score 0–1:  1 = perfect range (price contained, multiple touches),
                0 = directional breakout.
    Uses: channel_width vs ATR ratio and close-to-boundary proximity.
    Returns rolling series.
    """
    n = len(closes)
    result = np.full(n, np.nan)
    atr_series = compute_atr(highs, lows, closes, period=min(14, window // 2))

    for i in range(window, n):
        h_seg = highs[i - window: i + 1]
        l_seg = lows[i - window:  i + 1]
        c_seg = closes[i - window: i + 1]
        atr   = atr_series[i]

        if np.isnan(atr) or atr == 0:
            result[i] = 0.0
            continue

        high_bound = np.max(h_seg)
        low_bound  = np.min(l_seg)
        band_width = high_bound - low_bound

        # Price contained in a meaningful but not huge band
        if band_width == 0:
            result[i] = 0.0
            continue

        # Band should be >1 ATR (real range) but <4 ATR (not a trend)
        band_atr_ratio = band_width / atr
        containment_score = _clamp(1 - abs(band_atr_ratio - 2.0) / 4.0)

        # Check how often price touches near upper/lower bounds
        upper_zone = high_bound - atr * 0.3
        lower_zone = low_bound  + atr * 0.3
        near_upper = np.sum(c_seg >= upper_zone)
        near_lower = np.sum(c_seg <= lower_zone)
        touch_score = _clamp((near_upper + near_lower) / (window * 0.4))

        result[i] = _clamp((containment_score + touch_score) / 2.0)

    return result


def detect_pullback_series(closes: np.ndarray,
                            trend_period: int = 30,
                            pullback_period: int = 5) -> np.ndarray:
    """
    Boolean array: True at index i if a pullback against the main trend is detected.
    Main trend: EMA(trend_period) slope.
    Pullback: recent (pullback_period) closes move against the trend direction.
    """
    n = len(closes)
    result = np.zeros(n, dtype=bool)
    if n < trend_period + pullback_period:
        return result

    # Simple EMA via pandas-style loop
    ema = np.full(n, np.nan)
    alpha = 2.0 / (trend_period + 1)
    ema[trend_period - 1] = np.mean(closes[:trend_period])
    for i in range(trend_period, n):
        ema[i] = closes[i] * alpha + ema[i - 1] * (1 - alpha)

    for i in range(trend_period + pullback_period, n):
        if np.isnan(ema[i]) or np.isnan(ema[i - pullback_period]):
            continue

        ema_slope = ema[i] - ema[i - pullback_period]
        recent_move = closes[i] - closes[i - pullback_period]

        # Pullback: macro trend up, recent short move down (or vice versa)
        if ema_slope > 0 and recent_move < -abs(ema_slope) * 0.3:
            result[i] = True
        elif ema_slope < 0 and recent_move > abs(ema_slope) * 0.3:
            result[i] = True

    return result


def compute_trend_direction(plus_di: np.ndarray, minus_di: np.ndarray,
                             index: int) -> str:
    """Derive trend direction from DI values at a given index."""
    pdv = plus_di[index]
    mdv = minus_di[index]
    if np.isnan(pdv) or np.isnan(mdv):
        return "NEUTRAL"
    if pdv > mdv * 1.1:
        return "UP"
    elif mdv > pdv * 1.1:
        return "DOWN"
    return "NEUTRAL"


# ---------------------------------------------------------------------------
# Scoring model (mirrors OTC Sniper plan §1.4)
# ---------------------------------------------------------------------------

def _compute_tradability_score(adx_val: float, dir_eff: float,
                                rev_density: float, range_score: float,
                                regime: MarketRegime) -> int:
    """
    Rule-based tradability score 0–100.
    Weights:
      directional_efficiency : +30 pts max  (high weight)
      reversal_density       : -25 pts max  (high negative weight)
      adx                    : +25 pts max
      range_score            : ±10 pts      (neutral weight)
      base                   :  50 pts
    """
    score = 50.0

    # Directional efficiency  (0–1 → ±30)
    score += (dir_eff - 0.5) * 60       # 0.5 baseline

    # Reversal density (0–1 → up to -25)
    score -= rev_density * 25

    # ADX  (0–60+ → up to +25 for strong trend)
    adx_normalized = _clamp(adx_val / 50.0)
    score += adx_normalized * 25

    # Range score for RANGE_BOUND: moderate bonus
    if regime == MarketRegime.RANGE_BOUND:
        score += (range_score - 0.5) * 20

    # Regime-level overrides
    if regime == MarketRegime.INSUFFICIENT_DATA:
        return 0
    if regime == MarketRegime.CHOP_WHIPSAW:
        score = min(score, 30)          # Cap chop at 30

    return int(_clamp(score, 0, 100))


# ---------------------------------------------------------------------------
# Core Classifier
# ---------------------------------------------------------------------------

def _classify_single(
    adx_val:     float,
    plus_di_val: float,
    minus_di_val:float,
    dir_eff:     float,
    rev_density: float,
    rng_score:   float,
    pullback:    bool,
    n_candles:   int,
    min_candles: int,
) -> tuple:
    """
    Rule-based decision tree returning (MarketRegime, confidence, flags).
    Thresholds tuned for 1-minute OTC binary options data.
    """
    flags = []

    # ── Guard: warmup ────────────────────────────────────────────────────
    if n_candles < min_candles or np.isnan(adx_val):
        return MarketRegime.INSUFFICIENT_DATA, 1.0, ["INSUFFICIENT_DATA"]

    nan_safe_dir = dir_eff   if not np.isnan(dir_eff)    else 0.0
    nan_safe_rev = rev_density if not np.isnan(rev_density) else 0.5
    nan_safe_rng = rng_score if not np.isnan(rng_score)  else 0.0

    # ── Flag collection ──────────────────────────────────────────────────
    if nan_safe_rev > 0.65:
        flags.append("HIGH_REVERSAL_DENSITY")
    if nan_safe_dir < 0.30:
        flags.append("LOW_DIRECTIONAL_EFFICIENCY")
    if adx_val < 15:
        flags.append("VERY_LOW_ADX")
    if adx_val > 40:
        flags.append("STRONG_ADX")
    if pullback:
        flags.append("PULLBACK_DETECTED")
    if nan_safe_rng > 0.60:
        flags.append("RANGE_STRUCTURE")

    # ── Decision tree ────────────────────────────────────────────────────

    # 1. CHOP_WHIPSAW — highest priority, most dangerous
    if nan_safe_rev > 0.65 and nan_safe_dir < 0.30:
        confidence = _clamp((nan_safe_rev - 0.5) * 3)
        return MarketRegime.CHOP_WHIPSAW, confidence, flags

    # 2. STRONG_TREND — ADX-driven
    if adx_val >= 25 and nan_safe_dir >= 0.45:
        if pullback:
            # Trend pullback detected
            confidence = _clamp((adx_val - 20) / 30)
            return MarketRegime.TREND_PULLBACK, confidence, flags
        else:
            confidence = _clamp((adx_val - 25) / 25 * 0.7 + nan_safe_dir * 0.3)
            return MarketRegime.STRONG_TREND, confidence, flags

    # 3. TREND_PULLBACK without high ADX (early-stage trend)
    if pullback and adx_val >= 18 and nan_safe_dir >= 0.35:
        confidence = _clamp((adx_val - 18) / 20 * 0.6 + nan_safe_dir * 0.4)
        return MarketRegime.TREND_PULLBACK, confidence, flags

    # 4. RANGE_BOUND — channel detected
    if nan_safe_rng >= 0.55 and adx_val < 25:
        confidence = _clamp((nan_safe_rng - 0.5) * 2)
        return MarketRegime.RANGE_BOUND, confidence, flags

    # 5. Weak chop (moderate reversal, low efficiency) but not threshold-breaching
    if nan_safe_rev > 0.50 or nan_safe_dir < 0.40:
        # Lean conservative toward CHOP
        confidence = _clamp((0.60 - nan_safe_dir) + (nan_safe_rev - 0.40))
        flags.append("MARGINAL_CHOP")
        return MarketRegime.CHOP_WHIPSAW, max(0.3, confidence), flags

    # 6. Fallback: RANGE_BOUND
    return MarketRegime.RANGE_BOUND, 0.4, flags


# ---------------------------------------------------------------------------
# Main Analyzer Class
# ---------------------------------------------------------------------------

class MarketRegimeAnalyzer:
    """
    Primary interface for market regime classification.

    Usage in backtest:
        analyzer = MarketRegimeAnalyzer()
        regime_series = analyzer.precompute_regime_series(all_candles)
        ...
        for i in range(50, len(candles)):
            result = regime_series.at(i)
            # result.regime, result.tradability_score, result.flags ...
    """

    def __init__(
        self,
        adx_period:      int = 14,
        primary_window:  int = 20,    # Primary lookback for efficiency/reversal density
        secondary_window:int = 30,    # Secondary lookback for range scoring
        pullback_period: int = 5,
        min_candles:     int = 35,    # Below this → INSUFFICIENT_DATA
    ):
        self.adx_period       = adx_period
        self.primary_window   = primary_window
        self.secondary_window = secondary_window
        self.pullback_period  = pullback_period
        self.min_candles      = min_candles

    # ── Public: batch pre-compute ─────────────────────────────────────────

    def precompute_regime_series(self, candles) -> "RegimeSeries":
        """
        Pre-compute regime for every candle in the series.
        Vectorized: all indicators are computed once over the full array.
        Returns a RegimeSeries that can be cheaply indexed per trade.
        """
        n = len(candles)
        if n == 0:
            return RegimeSeries(results=[], candle_count=0)

        highs, lows, closes, _ = _extract_arrays(candles)

        # Vectorized indicator series
        adx_s, pdi_s, mdi_s = compute_adx(highs, lows, closes, self.adx_period)
        dir_eff_s   = compute_directional_efficiency(closes, self.primary_window)
        rev_den_s   = compute_reversal_density(closes, self.primary_window)
        rng_score_s = compute_range_score(highs, lows, closes, self.secondary_window)
        pullback_s  = detect_pullback_series(
            closes,
            trend_period=self.secondary_window,
            pullback_period=self.pullback_period
        )

        results = []
        for i in range(n):
            regime, confidence, flags = _classify_single(
                adx_val=      adx_s[i]     if not np.isnan(adx_s[i])     else float("nan"),
                plus_di_val=  pdi_s[i]     if not np.isnan(pdi_s[i])     else 0.0,
                minus_di_val= mdi_s[i]     if not np.isnan(mdi_s[i])     else 0.0,
                dir_eff=      dir_eff_s[i],
                rev_density=  rev_den_s[i],
                rng_score=    rng_score_s[i],
                pullback=     bool(pullback_s[i]),
                n_candles=    i + 1,
                min_candles=  self.min_candles,
            )

            trend_dir = compute_trend_direction(pdi_s, mdi_s, i)

            adx_v    = adx_s[i]    if not np.isnan(adx_s[i])    else 0.0
            dir_v    = dir_eff_s[i] if not np.isnan(dir_eff_s[i]) else 0.0
            rev_v    = rev_den_s[i] if not np.isnan(rev_den_s[i]) else 0.0
            rng_v    = rng_score_s[i] if not np.isnan(rng_score_s[i]) else 0.0

            t_score = _compute_tradability_score(adx_v, dir_v, rev_v, rng_v, regime)

            metrics = {
                "adx":                  round(adx_v,  2),
                "plus_di":              round(float(pdi_s[i]) if not np.isnan(pdi_s[i]) else 0.0, 2),
                "minus_di":             round(float(mdi_s[i]) if not np.isnan(mdi_s[i]) else 0.0, 2),
                "directional_efficiency": round(dir_v, 4),
                "reversal_density":     round(rev_v, 4),
                "range_score":          round(rng_v, 4),
                "pullback":             bool(pullback_s[i]),
            }

            results.append(RegimeResult(
                regime=regime,
                confidence=round(confidence, 3),
                tradability_score=t_score,
                trend_direction=trend_dir,
                flags=flags,
                metrics=metrics,
            ))

        return RegimeSeries(results=results, candle_count=n)

    # ── Public: single-candle classify (for live trading use) ─────────────

    def classify_regime(self, candles) -> RegimeResult:
        """
        Classify the regime at the current (latest) candle.
        Computes indicators over the full provided slice and returns the last result.
        Suitable for real-time single-candle classification.
        """
        series = self.precompute_regime_series(candles)
        if series.candle_count == 0:
            return _insufficient_data_result()
        return series.at(series.candle_count - 1)


# ---------------------------------------------------------------------------
# Tick-Level Quality Enrichment (optional, lightweight)
# ---------------------------------------------------------------------------

def compute_tick_quality(ticks: list, candle_open_ts: float,
                          candle_close_ts: float) -> dict:
    """
    Compute sub-candle tick quality metrics for a given candle's time window.
    Optional: enriches regime result with finer-grained signal quality.

    Args:
        ticks:           Raw tick list [{'t': timestamp, 'p': price, ...}]
        candle_open_ts:  Unix timestamp of candle open
        candle_close_ts: Unix timestamp of candle close

    Returns dict with:
        tick_count, reversal_density, zero_move_ratio, tick_volatility
    """
    candle_ticks = [
        t for t in ticks
        if candle_open_ts <= t.get("t", 0) < candle_close_ts
    ]
    if len(candle_ticks) < 2:
        return {"tick_count": len(candle_ticks), "reversal_density": 0.0,
                "zero_move_ratio": 0.0, "tick_volatility": 0.0}

    prices = np.array([t["p"] for t in candle_ticks], dtype=np.float64)
    moves  = np.diff(prices)

    # Reversal density
    signs   = np.sign(moves)
    nz      = signs[signs != 0]
    rev_den = float(np.sum(nz[1:] != nz[:-1]) / (len(nz) - 1)) if len(nz) > 1 else 0.0

    # Zero-move ratio
    zero_ratio = float(np.sum(moves == 0.0) / len(moves))

    # Tick volatility
    returns    = moves / prices[:-1]
    tick_vol   = float(np.std(returns)) if len(returns) > 1 else 0.0

    return {
        "tick_count":       len(candle_ticks),
        "reversal_density": round(rev_den,  4),
        "zero_move_ratio":  round(zero_ratio, 4),
        "tick_volatility":  round(tick_vol, 8),
    }
