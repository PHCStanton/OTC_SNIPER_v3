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
import math
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
# REV2 A2: 3-week half-life (within the specified 2–4 week range).
DEFAULT_RECENCY_HALF_LIFE_DAYS = 21.0
SECONDS_PER_DAY = 86400.0


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


def _require_non_neg_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PriorStoreValidationError(f"{field} must be a non-negative number, got {value!r}")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise PriorStoreValidationError(f"{field} must be a finite non-negative number, got {value!r}")
    return number


def recency_weight(
    age_days: float,
    half_life_days: float = DEFAULT_RECENCY_HALF_LIFE_DAYS,
) -> float:
    """Exponential recency weight. Half-life days must be > 0. Age < 0 is treated as 0."""
    half = _require_non_neg_number(half_life_days, "half_life_days")
    if half <= 0:
        raise PriorStoreValidationError("half_life_days must be > 0")
    age = _require_non_neg_number(max(0.0, float(age_days)), "age_days")
    return 0.5 ** (age / half)


def empty_recency(half_life_days: float = DEFAULT_RECENCY_HALF_LIFE_DAYS, as_of_unix: float = 0.0) -> Dict[str, Any]:
    return {
        "half_life_days": float(half_life_days),
        "as_of_unix": float(as_of_unix),
        "total_weighted_wins": 0.0,
        "total_weighted_losses": 0.0,
        "feature_counts": {},
    }


def normalize_recency_block(data: Any) -> Dict[str, Any]:
    """Validate the optional recency overlay. Fail loud on corrupt payloads."""
    if not isinstance(data, Mapping):
        raise PriorStoreValidationError("recency must be an object")
    half = _require_non_neg_number(
        data.get("half_life_days", DEFAULT_RECENCY_HALF_LIFE_DAYS),
        "recency.half_life_days",
    )
    if half <= 0:
        raise PriorStoreValidationError("recency.half_life_days must be > 0")
    as_of = _require_non_neg_number(data.get("as_of_unix", 0), "recency.as_of_unix")
    tw = _require_non_neg_number(data.get("total_weighted_wins", 0), "recency.total_weighted_wins")
    tl = _require_non_neg_number(data.get("total_weighted_losses", 0), "recency.total_weighted_losses")
    raw_fc = data.get("feature_counts") or {}
    if not isinstance(raw_fc, Mapping):
        raise PriorStoreValidationError("recency.feature_counts must be an object")
    feature_counts: Dict[str, Dict[str, float]] = {}
    for key, counts in raw_fc.items():
        if not isinstance(key, str) or not key.strip():
            raise PriorStoreValidationError(f"recency feature key must be a non-empty string, got {key!r}")
        if not isinstance(counts, Mapping):
            raise PriorStoreValidationError(f"recency.feature_counts[{key!r}] must be an object")
        win = _require_non_neg_number(counts.get("win", 0), f"recency.feature_counts[{key}].win")
        loss = _require_non_neg_number(counts.get("loss", 0), f"recency.feature_counts[{key}].loss")
        feature_counts[key.strip()] = {"win": win, "loss": loss}
    return {
        "half_life_days": half,
        "as_of_unix": as_of,
        "total_weighted_wins": tw,
        "total_weighted_losses": tl,
        "feature_counts": feature_counts,
    }


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

    result: Dict[str, Any] = {
        "total_wins": total_wins,
        "total_losses": total_losses,
        "total_trades": total_trades,
        "feature_counts": feature_counts,
    }
    if data.get("recency") is not None:
        result["recency"] = normalize_recency_block(data.get("recency"))
    return result


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

    out: Dict[str, Any] = {"won": won, "features": normalized_features}
    if trade.get("weight") is not None:
        out["weight"] = _require_non_neg_number(trade.get("weight"), "weight")
    if trade.get("age_days") is not None:
        out["age_days"] = _require_non_neg_number(trade.get("age_days"), "age_days")
    if trade.get("entry_time") is not None:
        out["entry_time"] = _require_non_neg_number(trade.get("entry_time"), "entry_time")
    return out


def _trade_recency_weight(
    trade: Mapping[str, Any],
    *,
    half_life_days: float,
    as_of_unix: Optional[float],
) -> float:
    if "weight" in trade:
        return float(trade["weight"])
    if "age_days" in trade:
        return recency_weight(float(trade["age_days"]), half_life_days)
    if "entry_time" in trade and as_of_unix is not None:
        age_days = max(0.0, (float(as_of_unix) - float(trade["entry_time"])) / SECONDS_PER_DAY)
        return recency_weight(age_days, half_life_days)
    return 1.0


def _scale_recency(recency: Mapping[str, Any], factor: float) -> Dict[str, Any]:
    scaled_fc = {
        key: {"win": float(counts["win"]) * factor, "loss": float(counts["loss"]) * factor}
        for key, counts in recency.get("feature_counts", {}).items()
    }
    return {
        "half_life_days": float(recency["half_life_days"]),
        "as_of_unix": float(recency.get("as_of_unix") or 0.0),
        "total_weighted_wins": float(recency.get("total_weighted_wins") or 0.0) * factor,
        "total_weighted_losses": float(recency.get("total_weighted_losses") or 0.0) * factor,
        "feature_counts": scaled_fc,
    }


def apply_trade_outcomes(
    priors: Mapping[str, Any],
    trades: List[Mapping[str, Any]],
    *,
    as_of_unix: Optional[float] = None,
    half_life_days: Optional[float] = None,
) -> Dict[str, Any]:
    """Return a new priors dict with trade outcomes applied (pure).

    Integer counts stay unweighted (backward compatible). When a recency overlay
    already exists, or any trade carries weight/age_days/entry_time, the overlay
    is decayed toward ``as_of_unix`` and the new evidence is added at its
    recency weight (REV2 A2).
    """
    base = normalize_priors(priors)
    total_wins = base["total_wins"]
    total_losses = base["total_losses"]
    feature_counts = {
        k: {"win": v["win"], "loss": v["loss"]}
        for k, v in base["feature_counts"].items()
    }

    validated: List[Dict[str, Any]] = [validate_trade_outcome(raw) for raw in trades]

    for trade in validated:
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

    result: Dict[str, Any] = {
        "total_wins": total_wins,
        "total_losses": total_losses,
        "total_trades": total_wins + total_losses,
        "feature_counts": feature_counts,
    }

    should_touch_recency = base.get("recency") is not None or any(
        "weight" in t or "age_days" in t or "entry_time" in t for t in validated
    )
    if should_touch_recency:
        existing = base.get("recency") or empty_recency(
            half_life_days or DEFAULT_RECENCY_HALF_LIFE_DAYS,
            as_of_unix or 0.0,
        )
        half = float(
            half_life_days
            if half_life_days is not None
            else existing.get("half_life_days") or DEFAULT_RECENCY_HALF_LIFE_DAYS
        )
        recency = dict(existing)
        recency["half_life_days"] = half
        if as_of_unix is not None:
            prev_as_of = float(recency.get("as_of_unix") or 0.0)
            if prev_as_of > 0:
                elapsed_days = max(0.0, (float(as_of_unix) - prev_as_of) / SECONDS_PER_DAY)
                recency = _scale_recency(recency, recency_weight(elapsed_days, half))
            recency["as_of_unix"] = float(as_of_unix)
            recency["half_life_days"] = half

        tw = float(recency.get("total_weighted_wins") or 0.0)
        tl = float(recency.get("total_weighted_losses") or 0.0)
        rfc: Dict[str, Dict[str, float]] = {
            k: {"win": float(v["win"]), "loss": float(v["loss"])}
            for k, v in (recency.get("feature_counts") or {}).items()
        }
        for trade in validated:
            weight = _trade_recency_weight(trade, half_life_days=half, as_of_unix=as_of_unix)
            if trade["won"]:
                tw += weight
                bucket = "win"
            else:
                tl += weight
                bucket = "loss"
            for feat in trade["features"]:
                if feat not in rfc:
                    rfc[feat] = {"win": 0.0, "loss": 0.0}
                rfc[feat][bucket] += weight
        recency["total_weighted_wins"] = tw
        recency["total_weighted_losses"] = tl
        recency["feature_counts"] = rfc
        result["recency"] = recency

    return normalize_priors(result)


def build_recency_priors(
    trades: List[Mapping[str, Any]],
    *,
    as_of_unix: float,
    half_life_days: float = DEFAULT_RECENCY_HALF_LIFE_DAYS,
) -> Dict[str, Any]:
    """Rebuild priors from a dated trade list with recency weighting (pure)."""
    return apply_trade_outcomes(
        empty_priors(),
        trades,
        as_of_unix=as_of_unix,
        half_life_days=half_life_days,
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
        # M8 fix: in-memory read cache invalidated on (mtime_ns, size) change.
        # Cross-process safe: any external write changes the stat key and forces a
        # fresh disk read; local atomic writes refresh the cache directly.
        self._read_cache: Optional[Dict[str, Any]] = None
        self._cache_key: Optional[tuple[int, int]] = None

    def _stat_key(self) -> Optional[tuple[int, int]]:
        try:
            st = self.priors_path.stat()
            return (st.st_mtime_ns, st.st_size)
        except OSError:
            return None

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
            self._read_cache = None
            self._cache_key = None
            return empty_priors()

        # M8 fix: serve from cache when the file has not changed on disk.
        stat_key = self._stat_key()
        if (
            self._read_cache is not None
            and stat_key is not None
            and stat_key == self._cache_key
        ):
            return dict(self._read_cache)

        last_err: Optional[BaseException] = None
        for attempt in range(READ_RETRY_ATTEMPTS):
            try:
                # Read full text then close promptly so Windows writers can replace.
                text = self.priors_path.read_text(encoding="utf-8")
                raw = json.loads(text)
                normalized = normalize_priors(raw)
                self._read_cache = normalized
                self._cache_key = self._stat_key()
                return dict(normalized)
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
            # M8 fix: keep the read cache coherent after a local atomic write.
            self._read_cache = dict(normalized)
            self._cache_key = self._stat_key()
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

    def update_from_trades(
        self,
        trades: List[Mapping[str, Any]],
        *,
        as_of_unix: Optional[float] = None,
        half_life_days: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Full RMW transaction: lock → read → apply trades → fsync replace → unlock."""
        if not isinstance(trades, list):
            raise PriorStoreValidationError("trades must be a list")
        # Validate inputs before taking the lock so bad payloads fail fast.
        for trade in trades:
            validate_trade_outcome(trade)

        with self._exclusive_lock():
            current = self._read_under_lock()
            updated = apply_trade_outcomes(
                current,
                trades,
                as_of_unix=as_of_unix,
                half_life_days=half_life_days,
            )
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
