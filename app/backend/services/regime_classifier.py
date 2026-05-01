from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RegimeConfig:
    """Tunable thresholds for regime classification."""

    strong_momentum_adx: float = 40.0
    trend_pullback_adx_min: float = 20.0
    range_bound_adx_max: float = 20.0
    strong_momentum_di_spread: float = 15.0
    reversal_adx_slope: float = -0.3
    reversal_prior_adx_min: float = 35.0
    breakout_atr_multiplier: float = 1.5
    pullback_structure_atr: float = 0.4
    min_candles: int = 14
    persistence_candles: int = 3
    atr_rolling_window: int = 10


@dataclass
class RegimeState:
    """Current regime classification result."""

    label: str = "INSUFFICIENT_DATA"
    confidence: float = 0.0
    prior_label: str | None = None
    persistence_count: int = 0
    detail: dict[str, Any] = field(default_factory=dict)


class RegimeClassifier:
    """
    Deterministic market regime classifier.

    Called once per closed candle to classify the current market state.
    """

    def __init__(self, config: RegimeConfig | None = None):
        self.config = config or RegimeConfig()
        self._state = RegimeState()
        self._atr_history: deque[float] = deque(maxlen=self.config.atr_rolling_window)
        self._peak_adx: float = 0.0

    def classify(self, market_context: dict[str, Any]) -> dict[str, Any]:
        """Classify the current market regime from Level 2 context data."""

        candle_count = int(market_context.get("candle_count") or 0)
        adx = market_context.get("adx")
        adx_slope = market_context.get("adx_slope")
        plus_di = market_context.get("plus_di")
        minus_di = market_context.get("minus_di")
        cci = market_context.get("cci")
        cci_state = market_context.get("cci_state")
        atr = market_context.get("atr")
        nearest_structure_atr = market_context.get("nearest_structure_atr")
        micro_support = market_context.get("micro_support")
        micro_resistance = market_context.get("micro_resistance")
        reversal_friendly = bool(market_context.get("reversal_friendly", False))

        if atr is not None:
            self._atr_history.append(float(atr))

        if adx is not None:
            adx = float(adx)
            if adx > self._peak_adx:
                self._peak_adx = adx
            elif adx < self._peak_adx:
                self._peak_adx = max(adx, self._peak_adx * 0.97)

        if candle_count < self.config.min_candles or adx is None:
            return self._emit("INSUFFICIENT_DATA", 0.0, {})

        di_spread = abs(float(plus_di or 0.0) - float(minus_di or 0.0))
        has_structure = micro_support is not None and micro_resistance is not None
        avg_atr = sum(self._atr_history) / len(self._atr_history) if self._atr_history else float(atr or 1.0)
        atr_ratio = (float(atr) / avg_atr) if avg_atr > 0 and atr is not None else 1.0

        if (
            atr_ratio > self.config.breakout_atr_multiplier
            and nearest_structure_atr is not None
            and float(nearest_structure_atr) > 1.0
        ):
            confidence = min(100.0, 50.0 + (atr_ratio - 1.0) * 30.0 + di_spread)
            return self._emit(
                "BREAKOUT",
                confidence,
                {
                    "atr_ratio": round(atr_ratio, 2),
                    "di_spread": round(di_spread, 1),
                    "trigger": "ATR spike + price beyond structure",
                },
            )

        if adx > self.config.strong_momentum_adx and di_spread > self.config.strong_momentum_di_spread:
            confidence = min(100.0, 40.0 + (adx - 40.0) * 1.5 + di_spread)
            return self._emit(
                "STRONG_MOMENTUM",
                confidence,
                {
                    "adx": round(adx, 1),
                    "di_spread": round(di_spread, 1),
                    "trigger": "High ADX + strong DI spread",
                },
            )

        if adx > self.config.trend_pullback_adx_min:
            if (
                adx_slope is not None
                and float(adx_slope) < self.config.reversal_adx_slope
                and self._peak_adx > self.config.reversal_prior_adx_min
                and reversal_friendly
            ):
                confidence = min(
                    100.0,
                    50.0 + abs(float(adx_slope)) * 30.0 + (self._peak_adx - adx) * 0.8,
                )
                return self._emit(
                    "TREND_REVERSAL",
                    confidence,
                    {
                        "adx": round(adx, 1),
                        "adx_slope": round(float(adx_slope), 2),
                        "peak_adx": round(self._peak_adx, 1),
                        "trigger": "Falling ADX from peak + reversal_friendly",
                    },
                )

            near_structure = (
                nearest_structure_atr is not None
                and float(nearest_structure_atr) < self.config.pullback_structure_atr
            )
            confidence = min(100.0, 40.0 + adx * 0.8 + (15.0 if near_structure else 0.0))
            return self._emit(
                "TREND_PULLBACK",
                confidence,
                {
                    "adx": round(adx, 1),
                    "near_structure": near_structure,
                    "trigger": "Moderate ADX trend zone",
                },
            )

        if has_structure and adx <= self.config.range_bound_adx_max:
            cci_cycling = cci_state in {"oversold", "overbought"}
            atr_stable = atr_ratio < 1.3
            if atr_stable and (cci_cycling or (cci is not None and abs(float(cci)) > 50.0)):
                confidence = min(100.0, 50.0 + (20.0 - adx) * 1.5 + (15.0 if cci_cycling else 0.0))
                return self._emit(
                    "RANGE_BOUND",
                    confidence,
                    {
                        "adx": round(adx, 1),
                        "cci_state": cci_state,
                        "atr_stable": atr_stable,
                        "trigger": "Low ADX + structure + CCI cycling",
                    },
                )

            confidence = min(100.0, 30.0 + atr_ratio * 10.0)
            return self._emit(
                "CHOPPY",
                confidence,
                {
                    "adx": round(adx, 1),
                    "atr_ratio": round(atr_ratio, 2),
                    "trigger": "Low ADX + unstable ATR or no CCI cycle",
                },
            )

        confidence = min(100.0, 40.0 + max(0.0, 20.0 - adx))
        return self._emit(
            "CHOPPY",
            confidence,
            {
                "adx": round(adx, 1),
                "has_structure": has_structure,
                "trigger": "Low ADX + no S/R structure",
            },
        )

    def _emit(self, label: str, confidence: float, detail: dict[str, Any]) -> dict[str, Any]:
        """Update internal state and return the current regime snapshot."""

        prior = self._state.label
        if label == self._state.label:
            self._state.persistence_count += 1
        else:
            self._state.prior_label = prior
            self._state.persistence_count = 1

        self._state.label = label
        self._state.confidence = round(min(100.0, max(0.0, confidence)), 1)
        self._state.detail = detail

        return {
            "regime_label": label,
            "regime_confidence": self._state.confidence,
            "regime_detail": detail,
            "regime_prior": prior if prior != label else None,
            "regime_stable": self._state.persistence_count >= self.config.persistence_candles,
            "regime_persistence": self._state.persistence_count,
        }

    def reset(self) -> None:
        """Reset classifier state."""

        self._state = RegimeState()
        self._atr_history.clear()
        self._peak_adx = 0.0
