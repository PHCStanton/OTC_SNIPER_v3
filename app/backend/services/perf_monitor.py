"""
Performance Monitor Service — OTC SNIPER v3
Tracks event-loop lag, tick queue length, processing duration percentiles, and flow rates.
"""
import asyncio
import logging
import time
import statistics
from collections import deque
from typing import List, Optional

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    Measures event loop lag and collects processing stats for tick updates.
    """

    def __init__(self, sio_server=None, interval_seconds: float = 5.0):
        self.sio = sio_server
        self.interval = interval_seconds
        self._active = False
        self._task: Optional[asyncio.Task] = None
        
        # Metrics
        self.loop_lag = 0.0
        self.processing_durations: deque = deque(maxlen=200)
        self.tick_count = 0
        self.emit_count = 0
        self.dropped_count = 0
        
        # References to query queue state
        self._queue: Optional[asyncio.Queue] = None

    def set_queue(self, queue: asyncio.Queue):
        """Bind the streaming service queue for telemetry."""
        self._queue = queue

    def record_tick(self, duration: float):
        """Record the duration of a single tick processing event."""
        self.tick_count += 1
        self.processing_durations.append(duration)

    def record_emit(self):
        """Record a Socket.IO emission event."""
        self.emit_count += 1

    def record_drop(self):
        """Record a dropped tick due to queue capacity limits."""
        self.dropped_count += 1

    def start(self):
        """Start the background telemetry monitoring loop."""
        if self._active:
            return
        self._active = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("PerformanceMonitor telemetry loop started.")

    def stop(self):
        """Stop the background telemetry monitoring loop."""
        self._active = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("PerformanceMonitor telemetry loop stopped.")

    async def _monitor_loop(self):
        while self._active:
            try:
                # 1. Measure Event Loop Lag
                start_time = time.time()
                await asyncio.sleep(self.interval)
                elapsed = time.time() - start_time
                self.loop_lag = max(0.0, elapsed - self.interval)

                # 2. Compute Processing Durations
                p50 = 0.0
                p95 = 0.0
                avg_dur = 0.0
                if self.processing_durations:
                    sorted_durs = sorted(self.processing_durations)
                    n = len(sorted_durs)
                    p50 = sorted_durs[int(n * 0.50)]
                    p95 = sorted_durs[int(n * 0.95)]
                    avg_dur = statistics.mean(self.processing_durations)

                queue_len = self._queue.qsize() if self._queue else 0

                # 3. Compile Stats
                stats = {
                    "loop_lag_ms": round(self.loop_lag * 1000, 2),
                    "queue_length": queue_len,
                    "ticks_processed_interval": self.tick_count,
                    "ticks_emitted_interval": self.emit_count,
                    "ticks_dropped_interval": self.dropped_count,
                    "p50_duration_ms": round(p50 * 1000, 3),
                    "p95_duration_ms": round(p95 * 1000, 3),
                    "avg_duration_ms": round(avg_dur * 1000, 3),
                }

                # Reset interval-based counters
                self.tick_count = 0
                self.emit_count = 0
                self.dropped_count = 0

                logger.debug("Performance Telemetry: %s", stats)

                # 4. Emit to Socket.IO if server is present
                if self.sio:
                    await self.sio.emit("performance_telemetry", stats)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in performance monitor telemetry loop: %s", e)
                await asyncio.sleep(self.interval)
