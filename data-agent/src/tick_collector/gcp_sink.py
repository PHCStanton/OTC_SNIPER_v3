"""
GCP Tick Sink — BigQuery/GCS storage with durable local SQLite fallback.

Design (Phase 2):
  - Synchronous ingress via short-held threading.Lock + snapshot swap.
  - Each buffered item gets a stable local ingestion_id (raw tick payload not mutated).
  - Local SQLite commit is the durability boundary; GCP runs only after local success.
  - Blocking SQLite I/O runs in asyncio.to_thread so the event loop stays responsive.
  - Failed local writes restore the exact snapshot ahead of newer ticks and do not
    advance total_flushed.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

logger = logging.getLogger("data_agent.gcp_sink")

# Dynamic import check for GCP libraries
HAS_GCP = False
try:
    from google.cloud import bigquery, storage

    HAS_GCP = True
except ImportError:
    bigquery = None
    storage = None

SHUTDOWN_FLUSH_MAX_ATTEMPTS = 3
SHUTDOWN_FLUSH_RETRY_DELAY_SEC = 0.15


@dataclass(frozen=True)
class BufferedTick:
    """In-memory tick envelope. Raw API payload is stored without mutation."""

    ingestion_id: str
    tick: Dict[str, Any]
    buffered_at: float

    @classmethod
    def create(cls, tick: Mapping[str, Any]) -> "BufferedTick":
        # Shallow copy isolates buffer from caller mutation; does not alter the original.
        return cls(
            ingestion_id=str(uuid.uuid4()),
            tick=dict(tick),
            buffered_at=time.time(),
        )

    def as_row(self) -> Dict[str, Any]:
        """SQLite/BQ row fields derived from the preserved raw tick."""
        return {
            "ingestion_id": self.ingestion_id,
            "timestamp": self.tick.get("timestamp"),
            "asset": self.tick.get("asset"),
            "price": self.tick.get("price"),
            "dir": self.tick.get("dir"),
            "is_demo": self.tick.get("is_demo"),
            "received_at": self.tick.get("received_at"),
        }


class GCPTickSink:
    """
    GCP BigQuery & GCS Tick Storage Sink with resilient local storage fallback.
    """

    def __init__(
        self,
        gcp_project_id: Optional[str] = None,
        dataset_id: str = "otc_sniper_analytics",
        table_id: str = "raw_ticks",
        gcs_bucket_name: str = "otc-sniper-tick-vault",
        local_db_path: str = "data-agent/data/ticks_fallback.db",
        batch_size: int = 100,
        flush_interval_sec: float = 5.0,
        shutdown_flush_attempts: int = SHUTDOWN_FLUSH_MAX_ATTEMPTS,
    ):
        self.project_id = gcp_project_id or os.getenv("GCP_PROJECT_ID", "otc-sniper-prod")
        self.dataset_id = dataset_id
        self.table_id = table_id
        self.gcs_bucket_name = gcs_bucket_name
        self.local_db_path = Path(local_db_path)
        self.batch_size = batch_size
        self.flush_interval_sec = flush_interval_sec
        self.shutdown_flush_attempts = max(1, int(shutdown_flush_attempts))

        # Ingress buffer: protected only by threading.Lock (sync callbacks / any thread).
        self._buffer: List[BufferedTick] = []
        self._buffer_lock = threading.Lock()

        # Serializes concurrent flush coroutines; does NOT protect ingress.
        self._flush_mutex = asyncio.Lock()
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None

        self._bq_client = None
        self._gcs_client = None
        self._total_flushed = 0
        self._flush_failures = 0
        self._flush_retries = 0
        self._last_flush_error: Optional[str] = None

        self.local_db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_local_db()
        self._init_gcp_clients()

    def _init_local_db(self) -> None:
        """Create/migrate local SQLite schema (idempotent)."""
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ticks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ingestion_id TEXT,
                        timestamp REAL,
                        asset TEXT,
                        price REAL,
                        dir TEXT,
                        is_demo INTEGER,
                        received_at REAL,
                        synced_gcp INTEGER DEFAULT 0
                    )
                    """
                )
                # Migrate pre-Phase-2 DBs that lack ingestion_id.
                cols = {
                    row[1]
                    for row in conn.execute("PRAGMA table_info(ticks)").fetchall()
                }
                if "ingestion_id" not in cols:
                    conn.execute("ALTER TABLE ticks ADD COLUMN ingestion_id TEXT")
                conn.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_ticks_ingestion_id
                    ON ticks(ingestion_id)
                    WHERE ingestion_id IS NOT NULL
                    """
                )
                conn.commit()
            logger.info("Local SQLite fallback DB initialized at %s", self.local_db_path)
        except Exception as err:
            logger.error("Failed to initialize local SQLite database: %s", err)
            raise

    def _init_gcp_clients(self) -> None:
        """Attempt to instantiate GCP BigQuery & GCS clients."""
        if not HAS_GCP:
            logger.warning(
                "GCP libraries (google-cloud-bigquery) not installed. "
                "Operating in Local-Fallback Mode."
            )
            return

        try:
            self._bq_client = bigquery.Client(project=self.project_id)
            self._gcs_client = storage.Client(project=self.project_id)
            logger.info(
                "GCP BigQuery & GCS clients initialized for project: %s", self.project_id
            )
        except Exception as err:
            logger.warning(
                "Could not connect to GCP: %s. Operating in Local-Fallback Mode.", err
            )

    def push_tick(self, tick: Dict[str, Any]) -> None:
        """Synchronously append a tick envelope to the in-memory buffer (thread-safe)."""
        buffered = BufferedTick.create(tick)
        with self._buffer_lock:
            self._buffer.append(buffered)

    def _take_snapshot(self) -> List[BufferedTick]:
        """Atomically swap out the current buffer. No I/O while holding the lock."""
        with self._buffer_lock:
            batch, self._buffer = self._buffer, []
        return batch

    def _restore_snapshot_before_newer_ticks(self, batch: Sequence[BufferedTick]) -> None:
        """
        Re-queue a failed snapshot ahead of any ticks that arrived after the swap.
        Preserves relative order: failed batch first, then newer ingress.
        """
        with self._buffer_lock:
            self._buffer = list(batch) + self._buffer
        self._flush_retries += 1

    def _buffer_len(self) -> int:
        with self._buffer_lock:
            return len(self._buffer)

    @property
    def metrics(self) -> Dict[str, Any]:
        """Return sink operational metrics."""
        return {
            "buffer_size": self._buffer_len(),
            "total_flushed": self._total_flushed,
            "flush_failures": self._flush_failures,
            "flush_retries": self._flush_retries,
            "last_flush_error": self._last_flush_error,
            "has_gcp_connection": self._bq_client is not None,
            "local_db_path": str(self.local_db_path),
        }

    async def start(self) -> None:
        """Start the background periodic flush task."""
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info(
            "GCPTickSink started (flush interval: %ss).", self.flush_interval_sec
        )

    async def stop(self) -> None:
        """
        Stop the sink and perform a bounded final local flush.
        Propagates terminal persistence failure so shutdown is visibly unsuccessful.
        """
        logger.info("Stopping GCPTickSink and flushing remaining ticks...")
        self._running = False
        if self._flush_task:
            # Prefer cooperative exit; cancel only if the loop is stuck in sleep.
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None

        last_error: Optional[BaseException] = None
        for attempt in range(self.shutdown_flush_attempts):
            try:
                await self.flush()
                if self._buffer_len() == 0:
                    return
                # Ticks arrived during flush; retry within bound.
                last_error = RuntimeError(
                    f"Buffer still non-empty after shutdown flush attempt {attempt + 1}"
                )
            except Exception as err:
                last_error = err
                logger.error(
                    "Shutdown flush attempt %s/%s failed: %s",
                    attempt + 1,
                    self.shutdown_flush_attempts,
                    err,
                )
            if attempt + 1 < self.shutdown_flush_attempts:
                await asyncio.sleep(SHUTDOWN_FLUSH_RETRY_DELAY_SEC)

        remaining = self._buffer_len()
        raise RuntimeError(
            f"GCPTickSink shutdown flush failed with {remaining} tick(s) still buffered. "
            f"Last error: {last_error!r}"
        )

    async def _flush_loop(self) -> None:
        """Periodic background loop triggering flushes."""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval_sec)
                if self._buffer_len() > 0:
                    try:
                        await self.flush()
                    except Exception as err:
                        # Fail loud in logs; loop continues so later retries can drain.
                        logger.error("Periodic flush failed: %s", err)
            except asyncio.CancelledError:
                break
            except Exception as err:
                logger.error("Error in sink flush loop: %s", err)

    def _write_batch_to_sqlite(self, batch: Sequence[BufferedTick]) -> None:
        """
        Persist one batch in a single SQLite transaction.
        INSERT OR IGNORE makes retries after ambiguous success idempotent via ingestion_id.
        """
        rows = [b.as_row() for b in batch]
        with sqlite3.connect(self.local_db_path) as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO ticks (
                    ingestion_id, timestamp, asset, price, dir, is_demo, received_at, synced_gcp
                )
                VALUES (
                    :ingestion_id, :timestamp, :asset, :price, :dir, :is_demo, :received_at, 0
                )
                """,
                rows,
            )
            conn.commit()

    def _stream_batch_to_bigquery(self, batch: Sequence[BufferedTick]) -> bool:
        """Best-effort BQ stream. Local durability already committed; failures leave SQLite rows."""
        if not self._bq_client:
            return False
        table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"
        # Do not send ingestion_id to BQ unless the remote schema supports it;
        # preserve the raw tick fields only.
        payload = [dict(b.tick) for b in batch]
        errors = self._bq_client.insert_rows_json(table_ref, payload)
        if errors:
            logger.error("BigQuery streaming errors: %s", errors)
            return False
        logger.debug(
            "Successfully streamed %s ticks to BigQuery (%s).", len(batch), table_ref
        )
        return True

    async def flush(self) -> None:
        """
        Flush in-memory buffer: local SQLite first (required), then optional GCP.
        Concurrent flushes are serialized by _flush_mutex; ingress remains unlocked.

        After a snapshot is taken, any exit without a known local commit restores the
        batch (including asyncio.CancelledError, which is a BaseException).
        SQLite work is shielded so cancel waits for the thread write to finish when
        possible; restore + INSERT OR IGNORE still covers ambiguous outcomes.
        """
        async with self._flush_mutex:
            batch = self._take_snapshot()
            if not batch:
                return

            local_ack = False
            try:
                # Shield: cancellation does not abort the OS thread mid-write.
                await asyncio.shield(
                    asyncio.to_thread(self._write_batch_to_sqlite, batch)
                )
                local_ack = True
            except Exception as local_err:
                self._restore_snapshot_before_newer_ticks(batch)
                self._flush_failures += 1
                self._last_flush_error = str(local_err)
                logger.error(
                    "Local SQLite flush failed (%s ticks restored to buffer): %s",
                    len(batch),
                    local_err,
                )
                raise
            except BaseException:
                # CancelledError and other non-Exception exits after snapshot.
                if not local_ack:
                    self._restore_snapshot_before_newer_ticks(batch)
                    self._last_flush_error = "flush interrupted before local durability ack"
                    logger.error(
                        "Flush interrupted; restored %s tick(s) to buffer",
                        len(batch),
                    )
                raise

            # Local durability succeeded — only now may we attempt remote delivery.
            # total_flushed means locally durable, not necessarily delivered to BQ.
            if self._bq_client:
                try:
                    await asyncio.to_thread(self._stream_batch_to_bigquery, batch)
                except Exception as bq_err:
                    logger.warning(
                        "BigQuery flush failed: %s. Ticks preserved in local database.",
                        bq_err,
                    )

            self._total_flushed += len(batch)
            self._last_flush_error = None
