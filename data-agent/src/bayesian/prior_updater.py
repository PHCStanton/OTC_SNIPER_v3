"""
Bayesian Prior Updater — Autonomous Bayesian Signal Filter Calibration Service

Design:
  - Loads baseline prior counts from app/data/ghost_trades/stats/bayesian_priors.json.
  - Queries empirical tick data & ghost trade performance from BigQuery or local fallback database.
  - Computes updated win/loss prior feature counts:
      - oteo_band (e.g. 75-84, 85-92, 93+)
      - z_band (<-1.5, -1.5_to_-0.5, -0.5_to_0.5, 0.5_to_1.5, >1.5)
      - direction (CALL, PUT)
      - confidence (LOW, MEDIUM, HIGH)
      - regime (TRENDING, RANGE, HIGH_VOLATILITY, UNKNOWN)
      - has_manip (MANIP_TRUE, MANIP_FALSE)
  - Performs atomic file update to prevent race conditions during live trading.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("data_agent.bayesian_updater")


class BayesianPriorUpdater:
    """
    Service to re-calibrate Bayesian priors based on continuous tick observation.
    """

    def __init__(
        self,
        priors_json_path: str = "app/data/ghost_trades/stats/bayesian_priors.json",
        local_db_path: str = "data-agent/data/ticks_fallback.db",
    ):
        self.priors_json_path = Path(priors_json_path)
        self.local_db_path = Path(local_db_path)

    def load_current_priors(self) -> Dict[str, Any]:
        """Read existing priors JSON structure."""
        if not self.priors_json_path.exists():
            logger.warning(f"Priors JSON at {self.priors_json_path} does not exist. Initializing empty structure.")
            return {
                "total_wins": 0,
                "total_losses": 0,
                "total_trades": 0,
                "feature_counts": {},
            }

        with open(self.priors_json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def update_priors_from_trades(self, new_trade_outcomes: list[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Incorporate a batch of trade outcomes into prior distributions.
        Each item in `new_trade_outcomes` should be:
          {
             "won": True/False,
             "features": ["oteo_band=85-92", "confidence=HIGH", "direction=CALL", ...]
          }
        """
        priors = self.load_current_priors()

        feature_counts = priors.setdefault("feature_counts", {})
        total_wins = priors.get("total_wins", 0)
        total_losses = priors.get("total_losses", 0)

        for trade in new_trade_outcomes:
            is_win = bool(trade.get("won", False))
            if is_win:
                total_wins += 1
            else:
                total_losses += 1

            features = trade.get("features", [])
            for feat in features:
                if feat not in feature_counts:
                    feature_counts[feat] = {"win": 0, "loss": 0}
                if is_win:
                    feature_counts[feat]["win"] += 1
                else:
                    feature_counts[feat]["loss"] += 1

        priors["total_wins"] = total_wins
        priors["total_losses"] = total_losses
        priors["total_trades"] = total_wins + total_losses
        priors["feature_counts"] = feature_counts

        self.save_priors_atomically(priors)
        return priors

    def save_priors_atomically(self, priors_data: Dict[str, Any]) -> None:
        """Write priors JSON via tempfile and atomic rename to avoid partial writes."""
        self.priors_json_path.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = self.priors_json_path.parent

        with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
            json.dump(priors_data, tf, indent=2)
            temp_name = tf.name

        Path(temp_name).replace(self.priors_json_path)
        logger.info(f"Bayesian priors successfully updated at {self.priors_json_path}")
