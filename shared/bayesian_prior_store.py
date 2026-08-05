"""
Cross-process transactional store for bayesian_priors.json.

Owns schema validation, sidecar file lock, read-modify-write under lock,
temp write + fsync + atomic replace. Usable by data-agent and the OTC_SNIPER
app without either depending on the other's service internals.

Transaction protocol:
  acquire lock
    -> read latest JSON
    -> validate schema
    -> apply update
    -> write temp in same directory
    -> flush + fsync temp
    -> atomic replace target
  release lock
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Union

logger = logging.getLogger("shared.bayesian_prior_store")

PathLike = Union[str, Path]

DEFAULT_LOCK_TIMEOUT_SEC = 10.0
READ_RETRY_ATTEMPTS = 8
READ_RETRY_BASE_DELAY_SEC = 0.02


class PriorStoreError(Exception):
    """Base error for Bayesian prior store operations."""


class PriorStoreLockTimeout(PriorStoreError):
    """Could not acquire the sidecar lock within the timeout."""


class PriorStoreCorruptError(PriorStoreError):
    """Existing priors file is corrupt or unreadable; refusing silent reset."""


class PriorStoreValidationError(PriorStoreError):
    """Priors payload or trade input failed schema validation."""


class PriorStorePersistenceError(PriorStoreError):
    """Atomic write / replace failed after lock acquisition."""


def empty_priors() -> Dict[str, Any]:
    return {
        "total_wins": 0,
        "total_losses": 0,
        "total_trades": 0,
        "feature_counts": {},
    }


def _require_non_neg_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        # Reject bool (subclass of int) and non-ints; accept true int only.
        # Also allow numeric strings? No — fail closed.
        if isinstance(value, float) and value.is_integer() and value >= 0:
            value = int(value)
        else:
            raise PriorStoreValidationError(f"{field} must be a non-negative integer, got {value!r}")
    if value < 0:
        raise PriorStoreValidationError(f"{field} must be non-negative, got {value}")
    return int(value)


def normalize_priors(data: Any) -> Dict[str, Any]:
    """Validate and normalize a priors document. Raises on corruption/invalid schema."""
    if not isinstance(data, Mapping):
        raise PriorStoreValidationError("priors root must be a JSON object")

    total_wins = _require_non_neg_int(data.get("total_wins", 0), "total_wins")
    total_losses = _require_non_neg_int(data.get("total_losses", 0), "total_losses")
    total_trades_raw = data.get("total_trades", total_wins + total_losses)
    total_trades = _require_non_neg_int(total_trades_raw, "total_trades")

    if total_trades != total_wins + total_losses:
        raise PriorStoreValidationError(
            f"impossible totals: total_trades={total_trades} != "
            f"total_wins+total_losses={total_wins + total_losses}"
        )

    raw_fc = data.get("feature_counts", {})
    if raw_fc is None:
        raw_fc = {}
    if not isinstance(raw_fc, Mapping):
        raise PriorStoreValidationError("feature_counts must be an object")

    feature_counts: Dict[str, Dict[str, int]] = {}
    for key, counts in raw_fc.items():
        if not isinstance(key, str) or not key.strip():
            raise PriorStoreValidationError(f"feature key must be a non-empty string, got {key!r}")
        if not isinstance(counts, Mapping):
            raise PriorStoreValidationError(f"feature_counts[{key!r}] must be an object")
        win = _require_non_neg_int(counts.get("win", 0), f"feature_counts[{key}].win")
        loss = _require_non_neg_int(counts.get("loss", 0), f"feature_counts[{key}].loss")
        feature_counts[key.strip()] = {"win": win, "loss": loss}

    return {
        "total_wins": total_wins,
        "total_losses": total_losses,
        "total_trades": total_trades,
        "feature_counts": feature_counts,
    }


def validate_trade_outcome(trade: Any) -> Dict[str, Any]:
    """Validate a single trade outcome for prior updates. won must be a real bool."""
    if not isinstance(trade, Mapping):
        raise PriorStoreValidationError("trade outcome must be an object")

    if "won" not in trade:
        raise PriorStoreValidationError("trade outcome missing required field 'won'")
    won = trade["won"]
    if not isinstance(won, bool):
        raise PriorStoreValidationError(
            f"won must be a JSON boolean, got {type(won).__name__}: {won!r}"
        )

    features = trade.get("features", [])
    if features is None:
        features = []
    if not isinstance(features, list):
        raise PriorStoreValidationError("features must be a list of strings")

    normalized_features: List[str] = []
    for feat in features:
        if not isinstance(feat, str) or not feat.strip():
            raise PriorStoreValidationError(
                f"each feature must be a non-empty string, got {feat!r}"
            )
        normalized_features.append(feat.strip())

    return {"won": won, "features": normalized_features}


def apply_trade_outcomes(
    priors: Mapping[str, Any],
    trades: List[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Return a new priors dict with trade outcomes applied (pure)."""
    base = normalize_priors(priors)
    total_wins = base["total_wins"]
    total_losses = base["total_losses"]
    feature_counts = {
        k: {"win": v["win"], "loss": v["loss"]}
        for k, v in base["feature_counts"].items()
    }

    for raw in trades:
        trade = validate_trade_outcome(raw)
        if trade["won"]:
            total_wins += 1
            bucket = "win"
        else:
            total_losses += 1
            bucket = "loss"

        for feat in trade["features"]:
            if feat not in feature_counts:
                feature_counts[feat] = {"win": 0, "loss": 0}
            feature_counts[feat][bucket] += 1

    return normalize_priors(
        {
            "total_wins": total_wins,
            "total_losses": total_losses,
            "total_trades": total_wins + total_losses,
            "feature_counts": feature_counts,
        }
    )


class _SidecarFileLock:
    """Cross-platform exclusive lock using a sidecar file (not the target JSON)."""

    def __init__(self, lock_path: Path, timeout_sec: float):
        self.lock_path = lock_path
        self.timeout_sec = timeout_sec
        self._fh: Any = None

    def acquire(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.lock_path, "a+b")
        deadline = time.monotonic() + self.timeout_sec
        while True:
            try:
                self._try_lock()
                return
            except (OSError, BlockingIOError, PermissionError):
                if time.monotonic() >= deadline:
                    self._close_handle()
                    raise PriorStoreLockTimeout(
                        f"Timed out after {self.timeout_sec}s acquiring lock "
                        f"{self.lock_path}"
                    )
                time.sleep(0.05)

    def _try_lock(self) -> None:
        if self._fh is None:
            raise PriorStoreError("lock file handle is not open")
        if sys.platform == "win32":
            import msvcrt

            self._fh.seek(0)
            # Ensure at least one byte exists to lock.
            if self._fh.read(1) == b"":
                self._fh.write(b"0")
                self._fh.flush()
            self._fh.seek(0)
            msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def release(self) -> None:
        if self._fh is None:
            return
        try:
            if sys.platform == "win32":
                import msvcrt

                self._fh.seek(0)
                try:
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        finally:
            self._close_handle()

    def _close_handle(self) -> None:
        if self._fh is not None:
            try:
                self._fh.close()
            except OSError:
                pass
            self._fh = None


class BayesianPriorStore:
    """Transactional prior file store with cross-process exclusive locking."""

    def __init__(
        self,
        priors_path: PathLike,
        *,
        lock_timeout_sec: float = DEFAULT_LOCK_TIMEOUT_SEC,
        lock_path: Optional[PathLike] = None,
    ):
        self.priors_path = Path(priors_path)
        self.lock_timeout_sec = float(lock_timeout_sec)
        if lock_path is not None:
            self.lock_path = Path(lock_path)
        else:
            self.lock_path = Path(str(self.priors_path) + ".lock")

    @contextmanager
    def _exclusive_lock(self) -> Iterator[None]:
        lock = _SidecarFileLock(self.lock_path, self.lock_timeout_sec)
        lock.acquire()
        try:
            yield
        finally:
            lock.release()

    def read(self, *, require_valid: bool = True) -> Dict[str, Any]:
        """
        Read latest priors with bounded retry (atomic-replace friendly).

        Missing file → empty priors.
        Permanently corrupt file → PriorStoreCorruptError (never silent empty overwrite).
        """
        if not self.priors_path.exists():
            return empty_priors()

        last_err: Optional[BaseException] = None
        for attempt in range(READ_RETRY_ATTEMPTS):
            try:
                # Read full text then close promptly so Windows writers can replace.
                text = self.priors_path.read_text(encoding="utf-8")
                raw = json.loads(text)
                return normalize_priors(raw)
            except PriorStoreValidationError as err:
                # Schema-invalid content is permanent corruption for this file.
                raise PriorStoreCorruptError(
                    f"Priors file failed validation: {self.priors_path}: {err}"
                ) from err
            except json.JSONDecodeError as err:
                last_err = err
            except PermissionError as err:
                last_err = err
            except OSError as err:
                last_err = err
            time.sleep(READ_RETRY_BASE_DELAY_SEC * (attempt + 1))

        if require_valid:
            raise PriorStoreCorruptError(
                f"Failed to read valid priors from {self.priors_path} "
                f"after {READ_RETRY_ATTEMPTS} attempts: {last_err}"
            )
        raise PriorStoreCorruptError(str(last_err))

    def _read_under_lock(self) -> Dict[str, Any]:
        if not self.priors_path.exists():
            return empty_priors()
        try:
            text = self.priors_path.read_text(encoding="utf-8")
            raw = json.loads(text)
            return normalize_priors(raw)
        except PriorStoreValidationError as err:
            raise PriorStoreCorruptError(
                f"Priors file failed validation under lock: {self.priors_path}: {err}"
            ) from err
        except json.JSONDecodeError as err:
            raise PriorStoreCorruptError(
                f"Priors file contains invalid JSON: {self.priors_path}: {err}"
            ) from err
        except OSError as err:
            raise PriorStorePersistenceError(
                f"Failed reading priors under lock: {err}"
            ) from err

    def _write_atomic_under_lock(self, priors: Mapping[str, Any]) -> None:
        normalized = normalize_priors(priors)
        self.priors_path.parent.mkdir(parents=True, exist_ok=True)
        temp_name: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                dir=self.priors_path.parent,
                delete=False,
                encoding="utf-8",
                prefix=".bayesian_priors_",
                suffix=".tmp",
            ) as tf:
                json.dump(normalized, tf, indent=2)
                tf.write("\n")
                tf.flush()
                os.fsync(tf.fileno())
                temp_name = tf.name

            # Windows may deny replace while a concurrent reader has the target open.
            # Retry under the exclusive lock until readers release (plan: bounded retry).
            self._atomic_replace_with_retry(Path(temp_name), self.priors_path)
            temp_name = None  # successfully moved
        except PriorStoreError:
            if temp_name:
                try:
                    Path(temp_name).unlink(missing_ok=True)
                except OSError:
                    pass
            raise
        except Exception as err:
            if temp_name:
                try:
                    Path(temp_name).unlink(missing_ok=True)
                except OSError:
                    pass
            raise PriorStorePersistenceError(
                f"Failed to atomically persist priors to {self.priors_path}: {err}"
            ) from err

    @staticmethod
    def _atomic_replace_with_retry(
        src: Path,
        dest: Path,
        *,
        attempts: int = 40,
        base_delay_sec: float = 0.025,
    ) -> None:
        last_err: Optional[BaseException] = None
        for attempt in range(attempts):
            try:
                src.replace(dest)
                return
            except PermissionError as err:
                last_err = err
            except OSError as err:
                # WinError 5 Access is denied often surfaces as OSError on some Pythons.
                winerr = getattr(err, "winerror", None)
                if winerr == 5 or err.errno in (13, 11, 16):
                    last_err = err
                else:
                    raise
            time.sleep(base_delay_sec * (1.0 + 0.15 * attempt))
        raise PriorStorePersistenceError(
            f"Failed to atomically replace {dest} after {attempts} attempts: {last_err}"
        )

    def update_from_trades(self, trades: List[Mapping[str, Any]]) -> Dict[str, Any]:
        """Full RMW transaction: lock → read → apply trades → fsync replace → unlock."""
        if not isinstance(trades, list):
            raise PriorStoreValidationError("trades must be a list")
        # Validate inputs before taking the lock so bad payloads fail fast.
        for trade in trades:
            validate_trade_outcome(trade)

        with self._exclusive_lock():
            current = self._read_under_lock()
            updated = apply_trade_outcomes(current, trades)
            self._write_atomic_under_lock(updated)
            return updated

    def mutate(
        self,
        mutator: Callable[[Dict[str, Any]], Mapping[str, Any]],
    ) -> Dict[str, Any]:
        """
        Lock → read → mutator(current) → validate → write → unlock.
        Mutator must return a full priors mapping.
        """
        with self._exclusive_lock():
            current = self._read_under_lock()
            try:
                candidate = mutator(dict(current))
            except PriorStoreError:
                raise
            except Exception as err:
                raise PriorStoreValidationError(f"mutation failed: {err}") from err
            normalized = normalize_priors(candidate)
            self._write_atomic_under_lock(normalized)
            return normalized

    def replace_all(self, priors: Mapping[str, Any]) -> Dict[str, Any]:
        """Validate and replace the entire priors document under lock."""
        normalized = normalize_priors(priors)
        with self._exclusive_lock():
            self._write_atomic_under_lock(normalized)
            return normalized
