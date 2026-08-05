"""
Market context provider contract for filter evaluation.

Production default: use only explicitly present, valid analytic fields on the tick.
Never fabricate market scores. A future live analytics producer can replace this
implementation without changing REST endpoint shapes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Protocol, runtime_checkable


# Analytic fields that gates may consume. has_manipulation is metadata only.
ANALYTIC_NUMERIC_KEYS = (
    "bayesian_posterior_prob",
    "volatility_score",
    "liquidity_score",
    "manipulation_severity",
)
ANALYTIC_BOOL_KEYS = ("has_manipulation",)


@dataclass(frozen=True)
class ContextResult:
    available: bool
    source: str
    values: Mapping[str, Any]
    reason: str | None = None


@runtime_checkable
class MarketContextProvider(Protocol):
    def get_context(self, tick: Mapping[str, Any], asset: str) -> ContextResult:
        ...


def as_finite_float(value: Any) -> Optional[float]:
    """Parse a finite float; reject bool, None, NaN, and non-numeric types."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            return None
        return number
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            number = float(text)
        except ValueError:
            return None
        if number != number or number in (float("inf"), float("-inf")):
            return None
        return number
    return None


def as_strict_bool(value: Any) -> Optional[bool]:
    """Accept only real booleans (not 0/1 or strings)."""
    if isinstance(value, bool):
        return value
    return None


class TickFieldContextProvider:
    """
    Default production provider: pull valid analytic fields from the tick only.

    Does not invent scores. Nested tick['market_context'] is consulted for the
    same keys when top-level fields are absent.
    """

    def get_context(self, tick: Mapping[str, Any], asset: str) -> ContextResult:
        if not isinstance(tick, Mapping):
            return ContextResult(
                available=False,
                source="unavailable",
                values={},
                reason="tick is not a mapping",
            )

        nested = tick.get("market_context")
        nested_map: Mapping[str, Any] = nested if isinstance(nested, Mapping) else {}

        values: dict[str, Any] = {}
        invalid: list[str] = []

        for key in ANALYTIC_NUMERIC_KEYS:
            raw = tick[key] if key in tick else nested_map.get(key) if key in nested_map else None
            if raw is None and key not in tick and key not in nested_map:
                continue
            if raw is None and (key in tick or key in nested_map):
                invalid.append(key)
                continue
            parsed = as_finite_float(raw)
            if parsed is None:
                invalid.append(key)
                continue
            values[key] = parsed

        for key in ANALYTIC_BOOL_KEYS:
            raw = tick[key] if key in tick else nested_map.get(key) if key in nested_map else None
            if raw is None and key not in tick and key not in nested_map:
                continue
            parsed = as_strict_bool(raw)
            if parsed is None:
                invalid.append(key)
                continue
            values[key] = parsed

        if invalid:
            return ContextResult(
                available=False,
                source="tick_invalid",
                values={},
                reason=f"invalid analytic field(s): {', '.join(invalid)}",
            )

        if not values:
            return ContextResult(
                available=False,
                source="unavailable",
                values={},
                reason="no analytic context fields present on tick",
            )

        return ContextResult(
            available=True,
            source="tick",
            values=values,
            reason=None,
        )


class StaticContextProvider:
    """Test/injection helper that returns a fixed ContextResult (or per-call factory)."""

    def __init__(self, result: ContextResult):
        self._result = result

    def get_context(self, tick: Mapping[str, Any], asset: str) -> ContextResult:
        return self._result
