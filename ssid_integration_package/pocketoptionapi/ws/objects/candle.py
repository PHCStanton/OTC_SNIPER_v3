"""Canonical candle data model for Pocket Option API."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Candle:
    """Single OHLC candle immutable value object."""

    time: int
    open: float
    high: float
    low: float
    close: float

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def candle_type(self) -> str:
        if self.is_bullish:
            return "green"
        if self.is_bearish:
            return "red"
        return "doji"

    def to_dict(self) -> dict:
        return {
            "time": self.time,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
        }

    def to_list(self) -> list:
        return [self.time, self.open, self.high, self.low, self.close]

    @classmethod
    def from_dict(cls, data: dict) -> "Candle":
        return cls(
            time=int(data["time"]),
            open=float(data["open"]),
            high=float(data["high"]),
            low=float(data["low"]),
            close=float(data["close"]),
        )

    @classmethod
    def from_list(cls, data: list) -> "Candle":
        if len(data) != 5:
            raise ValueError(f"Expected 5 elements, got {len(data)}: {data}")
        return cls(
            time=int(data[0]),
            open=float(data[1]),
            high=float(data[3]),
            low=float(data[4]),
            close=float(data[2]),
        )


class CandleCollection:
    """In-memory candle cache keyed by symbol and timeframe."""

    def __init__(self):
        self._candles: Dict[str, List[Candle]] = {}

    def _key(self, symbol: str, timeframe: int) -> str:
        return f"{symbol}_{timeframe}"

    def store(self, symbol: str, timeframe: int, candles: List[Candle]) -> None:
        key = self._key(symbol, timeframe)
        self._candles[key] = sorted(candles, key=lambda c: c.time)

    def get(self, symbol: str, timeframe: int, count: int = 100) -> List[Candle]:
        key = self._key(symbol, timeframe)
        candles = self._candles.get(key, [])
        return candles[-count:]

    def clear(self, symbol: Optional[str] = None, timeframe: Optional[int] = None) -> None:
        if symbol is not None and timeframe is not None:
            self._candles.pop(self._key(symbol, timeframe), None)
            return
        self._candles.clear()