"""
Bayesian Protocol Specification, Storage & Lifecycle Engine.

A BayesianProtocol represents a named, immutable, horizon-stamped snapshot containing:
- Protocol metadata (id, name, horizon_seconds, source_sessions, trade_count, health)
- Priors state compatible with BayesianPriorStore (total_wins, total_losses, total_trades, feature_counts)
- Optional candidate patterns and gate presets

Storage layout:
- Library snapshots: app/data/ghost_trades/stats/protocols/<id>.json
- Active protocol pointer: app/data/ghost_trades/stats/active_protocol.json
- Working copy (live execution): app/data/ghost_trades/stats/bayesian_priors.json
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from shared.bayesian_prior_store import (
    BayesianPriorStore,
    PriorStoreError,
    PriorStoreValidationError,
    normalize_priors,
)

logger = logging.getLogger("shared.bayesian_protocol")

CURRENT_SCHEMA_VERSION = 1


class ProtocolHealth(str, Enum):
    READY = "READY"
    EXPERIMENTAL = "EXPERIMENTAL"
    UNSAFE = "UNSAFE"


class ProtocolError(Exception):
    """Base error for Bayesian protocol operations."""


class ProtocolValidationError(ProtocolError):
    """Schema or semantic validation failure."""


def compute_protocol_health(horizon_seconds: int, total_trades: int) -> ProtocolHealth:
    """
    Derive health status:
    - READY: N >= 500 and horizon in {60, 300}
    - EXPERIMENTAL: 100 <= N < 500 (or non-standard horizon with N >= 100)
    - UNSAFE: N < 100
    """
    if total_trades < 100:
        return ProtocolHealth.UNSAFE
    if horizon_seconds in (60, 300) and total_trades >= 500:
        return ProtocolHealth.READY
    return ProtocolHealth.EXPERIMENTAL


def validate_protocol_dict(data: Any) -> Dict[str, Any]:
    """Validate structure, types, and priors inside a protocol dictionary."""
    if not isinstance(data, dict):
        raise ProtocolValidationError("Protocol root must be a JSON object")

    schema_version = data.get("schema_version", CURRENT_SCHEMA_VERSION)
    if schema_version != CURRENT_SCHEMA_VERSION:
        raise ProtocolValidationError(
            f"Unsupported schema_version {schema_version}; expected {CURRENT_SCHEMA_VERSION}"
        )

    proto_id = str(data.get("id") or "").strip()
    if not proto_id:
        proto_id = f"proto_{uuid.uuid4().hex[:12]}"

    name = str(data.get("name") or "Unnamed Protocol").strip()

    horizon_raw = data.get("horizon_seconds", 60)
    try:
        horizon_seconds = int(horizon_raw)
        if horizon_seconds <= 0:
            raise ValueError
    except (ValueError, TypeError):
        raise ProtocolValidationError(f"Invalid horizon_seconds: {horizon_raw!r}")

    # Validate embedded priors
    priors_raw = data.get("priors")
    if not priors_raw:
        raise ProtocolValidationError("Protocol must contain a non-empty 'priors' object")

    try:
        normalized_priors = normalize_priors(priors_raw)
    except PriorStoreValidationError as e:
        raise ProtocolValidationError(f"Invalid embedded priors: {e}") from e

    total_trades = normalized_priors["total_trades"]

    # Derive or check health
    health = compute_protocol_health(horizon_seconds, total_trades)

    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "id": proto_id,
        "name": name,
        "horizon_seconds": horizon_seconds,
        "source_sessions": list(data.get("source_sessions") or []),
        "trade_count": total_trades,
        "date_range": data.get("date_range"),
        "notes": str(data.get("notes") or ""),
        "created_utc": data.get("created_utc") or datetime.now(timezone.utc).isoformat(),
        "health": health.value,
        "priors": normalized_priors,
        "patterns": list(data.get("patterns") or []),
        "gates": dict(data.get("gates") or {"min_win_probability": 0.55}),
    }


class BayesianProtocolManager:
    """Manages reading, saving, listing, and activating Bayesian protocols."""

    def __init__(self, stats_dir: Path):
        self.stats_dir = stats_dir
        self.protocols_dir = stats_dir / "protocols"
        self.active_pointer_file = stats_dir / "active_protocol.json"
        self.live_priors_file = stats_dir / "bayesian_priors.json"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.stats_dir.mkdir(parents=True, exist_ok=True)
        self.protocols_dir.mkdir(parents=True, exist_ok=True)

    def list_protocols(self) -> List[Dict[str, Any]]:
        """List all saved protocol snapshots in the library."""
        self._ensure_dirs()
        protocols = []
        active_info = self.get_active_protocol_info()
        active_id = active_info.get("id") if active_info else None

        for p_path in sorted(self.protocols_dir.glob("*.json")):
            try:
                data = json.loads(p_path.read_text(encoding="utf-8"))
                validated = validate_protocol_dict(data)
                # Compute summary metrics
                pwins = validated["priors"]["total_wins"]
                ptotal = validated["priors"]["total_trades"]
                wr = round((pwins / ptotal * 100.0), 1) if ptotal > 0 else 0.0

                summary = {
                    "id": validated["id"],
                    "name": validated["name"],
                    "horizon_seconds": validated["horizon_seconds"],
                    "trade_count": validated["trade_count"],
                    "win_rate": wr,
                    "health": validated["health"],
                    "created_utc": validated["created_utc"],
                    "notes": validated["notes"],
                    "patterns_count": len(validated["patterns"]),
                    "is_active": (validated["id"] == active_id),
                    "file_name": p_path.name,
                }
                protocols.append(summary)
            except Exception as e:
                logger.warning("Failed to load protocol file %s: %s", p_path.name, e)

        # Sort with active on top, then by created_utc descending
        protocols.sort(key=lambda p: (1 if p["is_active"] else 0, p["created_utc"]), reverse=True)
        return protocols

    def get_protocol(self, proto_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full protocol document by ID."""
        safe_id = re.sub(r"[^\w\-.]", "_", proto_id)
        target = self.protocols_dir / f"{safe_id}.json"
        if not target.exists():
            # Try searching by id field inside files
            for p_path in self.protocols_dir.glob("*.json"):
                try:
                    data = json.loads(p_path.read_text(encoding="utf-8"))
                    if data.get("id") == proto_id:
                        return validate_protocol_dict(data)
                except Exception:
                    pass
            return None

        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            return validate_protocol_dict(data)
        except Exception as e:
            logger.error("Error reading protocol %s: %s", proto_id, e)
            raise ProtocolError(f"Corrupt protocol file: {e}")

    def save_protocol(self, protocol_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and save a protocol snapshot into the library."""
        validated = validate_protocol_dict(protocol_dict)
        safe_id = re.sub(r"[^\w\-.]", "_", validated["id"])
        target = self.protocols_dir / f"{safe_id}.json"

        target.write_text(
            json.dumps(validated, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Saved protocol '%s' (%s) to %s", validated["name"], validated["id"], target)
        return validated

    def delete_protocol(self, proto_id: str) -> bool:
        """Delete a protocol snapshot from the library."""
        active_info = self.get_active_protocol_info()
        if active_info and active_info.get("id") == proto_id:
            raise ProtocolError("Cannot delete the currently ACTIVE protocol. Activate another protocol first.")

        safe_id = re.sub(r"[^\w\-.]", "_", proto_id)
        target = self.protocols_dir / f"{safe_id}.json"
        if target.exists():
            target.unlink()
            logger.info("Deleted protocol %s", proto_id)
            return True

        for p_path in self.protocols_dir.glob("*.json"):
            try:
                data = json.loads(p_path.read_text(encoding="utf-8"))
                if data.get("id") == proto_id:
                    p_path.unlink()
                    logger.info("Deleted protocol %s at %s", proto_id, p_path.name)
                    return True
            except Exception:
                pass
        return False

    def activate_protocol(
        self, proto_id: str, allow_experimental: bool = True
    ) -> Dict[str, Any]:
        """
        Activate a protocol:
        1. Validate protocol exists and health is not UNSAFE.
        2. Create timestamped backup of current live priors.
        3. Transactionally replace bayesian_priors.json with the protocol's priors.
        4. Update active_protocol.json pointer.
        """
        protocol = self.get_protocol(proto_id)
        if not protocol:
            raise ProtocolValidationError(f"Protocol '{proto_id}' not found in library.")

        health = protocol["health"]
        if health == ProtocolHealth.UNSAFE.value:
            raise ProtocolValidationError(
                f"Cannot activate protocol '{protocol['name']}': health is UNSAFE (trade_count < 100)."
            )
        if health == ProtocolHealth.EXPERIMENTAL.value and not allow_experimental:
            raise ProtocolValidationError(
                f"Protocol '{protocol['name']}' is EXPERIMENTAL (N={protocol['trade_count']}); explicit confirmation required."
            )

        # 1. Backup existing live priors if present
        if self.live_priors_file.exists():
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            bak = self.stats_dir / f"bayesian_priors_{ts}.json.bak"
            shutil.copy2(self.live_priors_file, bak)
            logger.info("Created backup of working priors at %s", bak)

        # 2. Transactionally replace live priors
        store = BayesianPriorStore(self.live_priors_file)
        store.replace_all(protocol["priors"])

        # 3. Write active pointer
        active_pointer = {
            "id": protocol["id"],
            "name": protocol["name"],
            "horizon_seconds": protocol["horizon_seconds"],
            "trade_count": protocol["trade_count"],
            "health": protocol["health"],
            "activated_utc": datetime.now(timezone.utc).isoformat(),
        }
        self.active_pointer_file.write_text(
            json.dumps(active_pointer, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        logger.info("Successfully activated protocol '%s' (%s)", protocol["name"], protocol["id"])
        return active_pointer

    def get_active_protocol_info(self) -> Optional[Dict[str, Any]]:
        """Retrieve current active protocol pointer if configured."""
        if not self.active_pointer_file.exists():
            return None
        try:
            return json.loads(self.active_pointer_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Failed to read active_protocol.json: %s", e)
            return None

    def import_from_json(self, raw_content: str | bytes) -> Dict[str, Any]:
        """
        Import a protocol from raw JSON. Supports:
        1. Full BayesianProtocol schema.
        2. Legacy staged export bundles (wraps into BayesianProtocol automatically).
        """
        if isinstance(raw_content, bytes):
            raw_content = raw_content.decode("utf-8")

        parsed = json.loads(raw_content)

        # Check if this is a legacy bundle
        if "staged_id" in parsed and "bayesian_deltas" in parsed:
            # Wrap legacy export bundle
            b_deltas = parsed.get("bayesian_deltas", {})
            f_deltas = b_deltas.get("feature_deltas", {})
            tw = int(b_deltas.get("total_wins_delta", 0))
            tl = int(b_deltas.get("total_losses_delta", 0))
            session_id = parsed.get("session_id", "imported_session")

            wrapped = {
                "schema_version": 1,
                "id": f"proto_{parsed.get('staged_id') or uuid.uuid4().hex[:8]}",
                "name": f"Imported: {session_id}",
                "horizon_seconds": 60,
                "source_sessions": [session_id],
                "trade_count": tw + tl,
                "created_utc": parsed.get("timestamp") or datetime.now(timezone.utc).isoformat(),
                "notes": f"Imported from staging bundle {parsed.get('staged_id', '')}",
                "priors": {
                    "total_wins": tw,
                    "total_losses": tl,
                    "total_trades": tw + tl,
                    "feature_counts": f_deltas,
                },
                "patterns": parsed.get("selected_patterns") or [],
                "gates": {"min_win_probability": 0.55},
            }
            return self.save_protocol(wrapped)

        # Standard protocol import
        return self.save_protocol(parsed)
