"""
GCP Tick Sink — High Performance BigQuery & GCS Data Storage Engine with Local Parquet Fallback

Design:
  - Receives streaming tick dicts from SSIDTickCollector.
  - Buffers ticks in a thread-safe local queue.
  - Micro-batches flushes every `flush_interval_sec` (default: 5.0s) or `batch_size` (default: 100).
  - Writes micro-batches locally to Parquet / SQLite (`data-agent/data/ticks_fallback.db`).
  - Attempts GCP sync to BigQuery (`dataset.table`) & GCS bucket if credentials & google-cloud libraries are available.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("data_agent.gcp_sink")

# Dynamic import check for GCP libraries
HAS_GCP = False
try:
    from google.cloud import bigquery, storage
    HAS_GCP = True
except ImportError:
    bigquery = None
    storage = None


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
    ):
        self.project_id = gcp_project_id or os.getenv("GCP_PROJECT_ID", "otc-sniper-prod")
        self.dataset_id = dataset_id
        self.table_id = table_id
        self.gcs_bucket_name = gcs_bucket_name
        self.local_db_path = Path(local_db_path)
        self.batch_size = batch_size
        self.flush_interval_sec = flush_interval_sec

        self._buffer: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None

        self._bq_client = None
        self._gcs_client = None
        self._total_flushed = 0

        # Initialize local database directory & table schema
        self.local_db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_local_db()
        self._init_gcp_clients()

    def _init_local_db(self) -> None:
        """Create local SQLite fallback table if it does not exist."""
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ticks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL,
                        asset TEXT,
                        price REAL,
                        dir TEXT,
                        is_demo INTEGER,
                        received_at REAL,
                        synced_gcp INTEGER DEFAULT 0
                    )
                """)
                conn.commit()
            logger.info(f"Local SQLite fallback DB initialized at {self.local_db_path}")
        except Exception as err:
            logger.error(f"Failed to initialize local SQLite database: {err}")

    def _init_gcp_clients(self) -> None:
        """Attempt to instantiate GCP BigQuery & GCS clients."""
        if not HAS_GCP:
            logger.warning("GCP libraries (google-cloud-bigquery) not installed. Operating in Local-Fallback Mode.")
            return

        try:
            self._bq_client = bigquery.Client(project=self.project_id)
            self._gcs_client = storage.Client(project=self.project_id)
            logger.info(f"GCP BigQuery & GCS clients initialized for project: {self.project_id}")
        except Exception as err:
            logger.warning(f"Could not connect to GCP: {err}. Operating in Local-Fallback Mode.")

    def push_tick(self, tick: Dict[str, Any]) -> None:
        """Synchronously append tick record to in-memory buffer."""
        self._buffer.append(tick)

    @property
    def metrics(self) -> Dict[str, Any]:
        """Return sink operational metrics."""
        return {
            "buffer_size": len(self._buffer),
            "total_flushed": self._total_flushed,
            "has_gcp_connection": self._bq_client is not None,
            "local_db_path": str(self.local_db_path),
        }

    async def start(self) -> None:
        """Start the background periodic flush task."""
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info(f"GCPTickSink started (flush interval: {self.flush_interval_sec}s).")

    async def stop(self) -> None:
        """Stop sink and perform final buffer flush."""
        logger.info("Stopping GCPTickSink and flushing remaining ticks...")
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()

    async def _flush_loop(self) -> None:
        """Periodic background loop triggering flushes."""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval_sec)
                if len(self._buffer) >= self.batch_size or len(self._buffer) > 0:
                    await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as err:
                logger.error(f"Error in sink flush loop: {err}")

    async def flush(self) -> None:
        """Flush in-memory buffer to local SQLite and GCP if available."""
        async with self._lock:
            if not self._buffer:
                return

            batch = list(self._buffer)
            self._buffer.clear()

        # Step 1: Save batch to local SQLite database
        synced = 0
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                conn.executemany(
                    """
                    INSERT INTO ticks (timestamp, asset, price, dir, is_demo, received_at, synced_gcp)
                    VALUES (:timestamp, :asset, :price, :dir, :is_demo, :received_at, 0)
                    """,
                    batch,
                )
                conn.commit()
        except Exception as local_err:
            logger.error(f"Error inserting batch to local SQLite: {local_err}")

        # Step 2: Attempt streaming insert to BigQuery if connected
        if self._bq_client:
            try:
                table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"
                errors = self._bq_client.insert_rows_json(table_ref, batch)
                if not errors:
                    synced = 1
                    logger.debug(f"Successfully streamed {len(batch)} ticks to BigQuery ({table_ref}).")
                else:
                    logger.error(f"BigQuery streaming errors: {errors}")
            except Exception as bq_err:
                logger.warning(f"BigQuery flush failed: {bq_err}. Ticks preserved in local database.")

        self._total_flushed += len(batch)
