from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Candle:
    start_ts: int
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class Level2Config:
    candle_seconds: int = 60
    max_candles: int = 240
    adx_period: int = 14
    cci_period: int = 7
    cci_extreme_threshold: float = 100.0
    micro_pivot_span: int = 2
    macro_pivot_span: int = 4
    micro_lookback: int = 18
    macro_lookback: int = 60
    support_proximity_atr: float = 0.45
    resistance_proximity_atr: float = 0.45
    distant_structure_atr: float = 1.35


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _bucket_timestamp(timestamp: float, candle_seconds: int) -> int:
    return int(timestamp // candle_seconds) * candle_seconds


def _proximity_atr(price: float, level: float | None, atr: float | None) -> float | None:
    if level is None or atr is None or atr <= 0:
        return None
    return abs(price - level) / atr


def _last_confirmed_pivot(candles: list[Candle], span: int, lookback: int, pivot_type: str) -> float | None:
    if len(candles) < (span * 2 + 1):
        return None

    relevant = candles[-lookback:] if len(candles) > lookback else candles
    latest_level = None
    for index in range(span, len(relevant) - span):
        window = relevant[index - span:index + span + 1]
        center = relevant[index]
        if pivot_type == "high":
            if center.high == max(candle.high for candle in window):
                latest_level = center.high
        else:
            if center.low == min(candle.low for candle in window):
                latest_level = center.low
    return latest_level


def _compute_adx(candles: list[Candle], period: int) -> dict[str, float | None]:
    if len(candles) < period + 2:
        return {"atr": None, "adx": None, "plus_di": None, "minus_di": None, "adx_slope": None}

    trs: list[float] = []
    plus_dm_values: list[float] = []
    minus_dm_values: list[float] = []

    for index in range(1, len(candles)):
        previous = candles[index - 1]
        current = candles[index]

        high_diff = current.high - previous.high
        low_diff = previous.low - current.low
        plus_dm = high_diff if high_diff > low_diff and high_diff > 0 else 0.0
        minus_dm = low_diff if low_diff > high_diff and low_diff > 0 else 0.0

        true_range = max(
            current.high - current.low,
            abs(current.high - previous.close),
            abs(current.low - previous.close),
        )

        trs.append(true_range)
        plus_dm_values.append(plus_dm)
        minus_dm_values.append(minus_dm)

    if len(trs) < period:
        return {"atr": None, "adx": None, "plus_di": None, "minus_di": None, "adx_slope": None}

    atr = sum(trs[:period]) / period
    plus_dm_smoothed = sum(plus_dm_values[:period]) / period
    minus_dm_smoothed = sum(minus_dm_values[:period]) / period

    adx_series: list[float] = []
    plus_di = 0.0
    minus_di = 0.0

    for index in range(period, len(trs)):
        atr = ((atr * (period - 1)) + trs[index]) / period
        plus_dm_smoothed = ((plus_dm_smoothed * (period - 1)) + plus_dm_values[index]) / period
        minus_dm_smoothed = ((minus_dm_smoothed * (period - 1)) + minus_dm_values[index]) / period

        if atr <= 0:
            plus_di = 0.0
            minus_di = 0.0
            dx = 0.0
        else:
            plus_di = 100.0 * (plus_dm_smoothed / atr)
            minus_di = 100.0 * (minus_dm_smoothed / atr)
            denominator = plus_di + minus_di
            dx = 0.0 if denominator <= 0 else 100.0 * abs(plus_di - minus_di) / denominator

        if not adx_series:
            adx_series.append(dx)
        else:
            adx_series.append(((adx_series[-1] * (period - 1)) + dx) / period)

    if not adx_series:
        return {"atr": atr, "adx": None, "plus_di": plus_di, "minus_di": minus_di, "adx_slope": None}

    adx = adx_series[-1]
    adx_slope = adx_series[-1] - adx_series[-3] if len(adx_series) >= 3 else 0.0
    return {"atr": atr, "adx": adx, "plus_di": plus_di, "minus_di": minus_di, "adx_slope": adx_slope}


def _typical_price(candle: Candle) -> float:
    return (candle.high + candle.low + candle.close) / 3.0


def _compute_cci(candles: list[Candle], period: int) -> dict[str, float | None]:
    if len(candles) < period:
        return {"cci": None, "cci_slope": None}

    typical_prices = [_typical_price(candle) for candle in candles]
    cci_series: list[float] = []

    for index in range(period - 1, len(typical_prices)):
        window = typical_prices[index - period + 1:index + 1]
        sma = sum(window) / period
        mean_deviation = sum(abs(price - sma) for price in window) / period
        if mean_deviation <= 1e-12:
            cci = 0.0
        else:
            cci = (typical_prices[index] - sma) / (0.015 * mean_deviation)
        cci_series.append(cci)

    if not cci_series:
        return {"cci": None, "cci_slope": None}

    cci = cci_series[-1]
    cci_slope = cci_series[-1] - cci_series[-3] if len(cci_series) >= 3 else 0.0
    return {"cci": cci, "cci_slope": cci_slope}


class MarketContextEngine:
    def __init__(self, config: Level2Config | None = None):
        self.config = config or Level2Config()
        self._closed_candles: list[Candle] = []
        self._current_candle: Candle | None = None

    def seed_tick(self, price: float, timestamp: float) -> None:
        self.update_tick(price, timestamp)

    def update_tick(self, price: float, timestamp: float) -> dict[str, Any]:
        candle_start = _bucket_timestamp(timestamp, self.config.candle_seconds)

        if self._current_candle is None:
            self._current_candle = Candle(candle_start, price, price, price, price)
        elif candle_start == self._current_candle.start_ts:
            self._current_candle.high = max(self._current_candle.high, price)
            self._current_candle.low = min(self._current_candle.low, price)
            self._current_candle.close = price
        else:
            self._closed_candles.append(self._current_candle)
            if len(self._closed_candles) > self.config.max_candles:
                self._closed_candles = self._closed_candles[-self.config.max_candles:]
            self._current_candle = Candle(candle_start, price, price, price, price)

        candles = [*self._closed_candles]
        if self._current_candle is not None:
            candles.append(self._current_candle)

        metrics = _compute_adx(candles, self.config.adx_period)
        atr = metrics["atr"]
        adx = metrics["adx"]
        plus_di = metrics["plus_di"]
        minus_di = metrics["minus_di"]
        adx_slope = metrics["adx_slope"]
        cci_metrics = _compute_cci(candles, self.config.cci_period)
        cci = cci_metrics["cci"]
        cci_slope = cci_metrics["cci_slope"]

        closed_candles = self._closed_candles
        micro_support = _last_confirmed_pivot(closed_candles, self.config.micro_pivot_span, self.config.micro_lookback, "low")
        micro_resistance = _last_confirmed_pivot(closed_candles, self.config.micro_pivot_span, self.config.micro_lookback, "high")
        macro_support = _last_confirmed_pivot(closed_candles, self.config.macro_pivot_span, self.config.macro_lookback, "low")
        macro_resistance = _last_confirmed_pivot(closed_candles, self.config.macro_pivot_span, self.config.macro_lookback, "high")

        if macro_support is None and closed_candles:
            macro_support = min(candle.low for candle in closed_candles[-self.config.macro_lookback:])
        if macro_resistance is None and closed_candles:
            macro_resistance = max(candle.high for candle in closed_candles[-self.config.macro_lookback:])

        micro_support_proximity = _proximity_atr(price, micro_support, atr)
        micro_resistance_proximity = _proximity_atr(price, micro_resistance, atr)
        macro_support_proximity = _proximity_atr(price, macro_support, atr)
        macro_resistance_proximity = _proximity_atr(price, macro_resistance, atr)

        support_proximity_candidates = [value for value in [micro_support_proximity, macro_support_proximity] if value is not None]
        resistance_proximity_candidates = [value for value in [micro_resistance_proximity, macro_resistance_proximity] if value is not None]
        nearest_support_atr = min(support_proximity_candidates) if support_proximity_candidates else None
        nearest_resistance_atr = min(resistance_proximity_candidates) if resistance_proximity_candidates else None

        if adx is None:
            adx_regime = "unavailable"
        elif adx < 18:
            adx_regime = "weak"
        elif adx < 28:
            adx_regime = "moderate"
        else:
            adx_regime = "strong"

        di_delta = (plus_di or 0.0) - (minus_di or 0.0)
        if di_delta > 5.0:
            trend_direction = "up"
        elif di_delta < -5.0:
            trend_direction = "down"
        else:
            trend_direction = "flat"

        support_alignment = nearest_support_atr is not None and nearest_support_atr <= self.config.support_proximity_atr
        resistance_alignment = nearest_resistance_atr is not None and nearest_resistance_atr <= self.config.resistance_proximity_atr
        structure_atr_candidates = [value for value in [nearest_support_atr, nearest_resistance_atr] if value is not None]
        nearest_structure_atr = min(structure_atr_candidates) if structure_atr_candidates else None

        if cci is None:
            cci_state = "unavailable"
        elif cci <= -self.config.cci_extreme_threshold:
            cci_state = "oversold"
        elif cci >= self.config.cci_extreme_threshold:
            cci_state = "overbought"
        else:
            cci_state = "neutral"

        return {
            "ready": len(closed_candles) >= max(self.config.adx_period + 2, self.config.cci_period, self.config.micro_pivot_span * 3 + 2),
            "candle_count": len(closed_candles),
            "atr": round(float(atr), 6) if atr is not None else None,
            "adx": round(float(adx), 2) if adx is not None else None,
            "plus_di": round(float(plus_di), 2) if plus_di is not None else None,
            "minus_di": round(float(minus_di), 2) if minus_di is not None else None,
            "adx_slope": round(float(adx_slope), 2) if adx_slope is not None else None,
            "cci": round(float(cci), 2) if cci is not None else None,
            "cci_slope": round(float(cci_slope), 2) if cci_slope is not None else None,
            "cci_state": cci_state,
            "adx_regime": adx_regime,
            "trend_direction": trend_direction,
            "micro_support": round(float(micro_support), 6) if micro_support is not None else None,
            "micro_resistance": round(float(micro_resistance), 6) if micro_resistance is not None else None,
            "macro_support": round(float(macro_support), 6) if macro_support is not None else None,
            "macro_resistance": round(float(macro_resistance), 6) if macro_resistance is not None else None,
            "nearest_support_atr": round(float(nearest_support_atr), 3) if nearest_support_atr is not None else None,
            "nearest_resistance_atr": round(float(nearest_resistance_atr), 3) if nearest_resistance_atr is not None else None,
            "nearest_structure_atr": round(float(nearest_structure_atr), 3) if nearest_structure_atr is not None else None,
            "support_alignment": support_alignment,
            "resistance_alignment": resistance_alignment,
            "adx_falling": bool(adx_slope is not None and adx_slope < 0),
            "reversal_friendly": adx is not None and (adx < 28 or (adx_slope is not None and adx_slope < -0.5)),
        }


def _confidence_rank(confidence: str) -> int:
    return {"LOW": 0, "MEDIUM": 1, "HIGH": 2}.get(confidence, 0)


def _confidence_from_rank(rank: int) -> str:
    return ["LOW", "MEDIUM", "HIGH"][max(0, min(2, int(rank)))]


def apply_level2_policy(oteo_result: dict[str, Any], market_context: dict[str, Any], enabled: bool) -> dict[str, Any]:
    result = dict(oteo_result)
    result["base_oteo_score"] = oteo_result["oteo_score"]
    result["base_confidence"] = oteo_result["confidence"]
    result["base_actionable"] = oteo_result["actionable"]
    result["level2_enabled"] = enabled
    result["market_context"] = market_context

    if not enabled or not market_context.get("ready"):
        result["level2_score_adjustment"] = 0.0
        result["level2_suppressed_reason"] = None
        return result

    direction = str(oteo_result.get("recommended") or "").upper()
    if direction not in {"CALL", "PUT"}:
        result["level2_score_adjustment"] = 0.0
        result["level2_suppressed_reason"] = None
        return result

    score_adjustment = 0.0
    suppress_reason = None

    support_alignment = bool(market_context.get("support_alignment"))
    resistance_alignment = bool(market_context.get("resistance_alignment"))
    trend_direction = market_context.get("trend_direction")
    adx_regime = market_context.get("adx_regime")
    nearest_structure_atr = market_context.get("nearest_structure_atr")
    adx_falling = bool(market_context.get("adx_falling"))
    cci = market_context.get("cci")
    cci_slope = market_context.get("cci_slope")
    cci_state = market_context.get("cci_state")

    if direction == "CALL":
        if support_alignment:
            score_adjustment += 8.0
        if resistance_alignment:
            score_adjustment -= 4.0
        if cci_state == "oversold":
            score_adjustment += 4.0
            if isinstance(cci_slope, (int, float)) and cci_slope > 0:
                score_adjustment += 2.0
        elif cci_state == "overbought":
            score_adjustment -= 5.0
        if trend_direction == "down":
            if adx_regime == "strong" and not support_alignment:
                suppress_reason = "strong_downtrend_without_support"
            elif adx_regime == "strong":
                score_adjustment -= 8.0
        elif trend_direction == "up" and adx_regime in {"moderate", "strong"}:
            score_adjustment += 4.0
    else:
        if resistance_alignment:
            score_adjustment += 8.0
        if support_alignment:
            score_adjustment -= 4.0
        if cci_state == "overbought":
            score_adjustment += 4.0
            if isinstance(cci_slope, (int, float)) and cci_slope < 0:
                score_adjustment += 2.0
        elif cci_state == "oversold":
            score_adjustment -= 5.0
        if trend_direction == "up":
            if adx_regime == "strong" and not resistance_alignment:
                suppress_reason = "strong_uptrend_without_resistance"
            elif adx_regime == "strong":
                score_adjustment -= 8.0
        elif trend_direction == "down" and adx_regime in {"moderate", "strong"}:
            score_adjustment += 4.0

    if nearest_structure_atr is not None and nearest_structure_atr > 1.35:
        score_adjustment -= 5.0

    if isinstance(cci, (int, float)) and abs(cci) < 35:
        score_adjustment -= 2.0

    if adx_falling and (support_alignment or resistance_alignment):
        score_adjustment += 3.0

    adjusted_score = round(_clamp(float(oteo_result["oteo_score"]) + score_adjustment, 0.0, 100.0), 1)
    adjusted_rank = _confidence_rank(str(oteo_result["confidence"]))

    if score_adjustment >= 7.0:
        adjusted_rank += 1
    elif score_adjustment <= -7.0:
        adjusted_rank -= 1

    adjusted_confidence = _confidence_from_rank(adjusted_rank)
    adjusted_actionable = bool(oteo_result["actionable"]) or score_adjustment >= 8.0

    if adjusted_score <= 55.0:
        adjusted_confidence = "LOW"
        adjusted_actionable = False
    elif adjusted_score >= 80.0 and adjusted_confidence == "MEDIUM":
        adjusted_confidence = "HIGH"

    if suppress_reason:
        adjusted_confidence = "LOW"
        adjusted_actionable = False

    result["oteo_score"] = adjusted_score
    result["confidence"] = adjusted_confidence
    result["actionable"] = adjusted_actionable and adjusted_confidence in {"MEDIUM", "HIGH"}
    result["level2_score_adjustment"] = round(score_adjustment, 1)
    result["level2_suppressed_reason"] = suppress_reason
    return result
