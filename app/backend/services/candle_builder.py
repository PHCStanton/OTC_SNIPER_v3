"""
Multi-timeframe OHLC candle builder from raw ticks.
Independent of MarketContextEngine — maintains its own candle stream.
"""
from collections import deque
from dataclasses import dataclass

@dataclass
class MicroCandle:
    open: float
    high: float
    low: float
    close: float
    open_time: float
    close_time: float
    tick_count: int

class CandleBuilder:
    """Builds OHLC candles from raw ticks at a configurable period."""
    
    def __init__(self, period_seconds: int = 30, max_candles: int = 50):
        self.period_seconds = period_seconds
        self.max_candles = max_candles
        self.closed_candles: deque[MicroCandle] = deque(maxlen=max_candles)
        self._current: MicroCandle | None = None
        self._current_boundary: float = 0.0

    def update(self, price: float, timestamp: float) -> MicroCandle | None:
        """Feed a tick. Returns a MicroCandle if one just closed, else None."""
        boundary = timestamp - (timestamp % self.period_seconds)
        
        if self._current is None:
            # First tick ever
            self._current = MicroCandle(
                open=price, high=price, low=price, close=price,
                open_time=timestamp, close_time=timestamp, tick_count=1
            )
            self._current_boundary = boundary
            return None
        
        if boundary > self._current_boundary:
            # New candle period — close the current candle
            closed = self._current
            self.closed_candles.append(closed)
            self._current = MicroCandle(
                open=price, high=price, low=price, close=price,
                open_time=timestamp, close_time=timestamp, tick_count=1
            )
            self._current_boundary = boundary
            return closed
        
        # Same period — update current candle
        self._current.high = max(self._current.high, price)
        self._current.low = min(self._current.low, price)
        self._current.close = price
        self._current.close_time = timestamp
        self._current.tick_count += 1
        return None

    def get_closes(self) -> list[float]:
        """Returns close prices of all closed candles."""
        return [c.close for c in self.closed_candles]

    def get_highs(self) -> list[float]:
        return [c.high for c in self.closed_candles]

    def get_lows(self) -> list[float]:
        return [c.low for c in self.closed_candles]

    def reset(self) -> None:
        self.closed_candles.clear()
        self._current = None
        self._current_boundary = 0.0
