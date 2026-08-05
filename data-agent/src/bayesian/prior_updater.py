"""
Bayesian Prior Updater — Autonomous Bayesian Signal Filter Calibration Service

Design:
  - Loads baseline prior counts from app/data/ghost_trades/stats/bayesian_priors.json.
  - Incorporates trade outcomes into win/loss prior feature counts.
  - Delegates all read-modify-write transactions to the shared BayesianPriorStore
    (cross-process sidecar lock + atomic replace).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union

try:
    from shared.bayesian_prior_store import (
        BayesianPriorStore,
        PriorStoreError,
    )
except ImportError:  # pragma: no cover - path bootstrap for standalone runs
    import sys
    from pathlib import Path as _Path

    _root = _Path(__file__).resolve().parents[3]
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from shared.bayesian_prior_store import (
        BayesianPriorStore,
        PriorStoreError,
    )

logger = logging.getLogger("data_agent.bayesian_updater")

PathLike = Union[str, Path]


class BayesianPriorUpdater:
    """
    Service to re-calibrate Bayesian priors based on continuous tick observation.
    """

    def __init__(
        self,
        priors_json_path: str = "app/data/ghost_trades/stats/bayesian_priors.json",
        local_db_path: str = "data-agent/data/ticks_fallback.db",
        lock_timeout_sec: float = 10.0,
    ):
        self.priors_json_path = Path(priors_json_path)
        self.local_db_path = Path(local_db_path)
        self._store = BayesianPriorStore(
            self.priors_json_path,
            lock_timeout_sec=lock_timeout_sec,
        )

    @property
    def store(self) -> BayesianPriorStore:
        return self._store

    def load_current_priors(self) -> Dict[str, Any]:
        """Read existing priors JSON structure (retry-friendly atomic readers)."""
        try:
            return self._store.read()
        except PriorStoreError as err:
            logger.error("Failed to load Bayesian priors: %s", err)
            raise

    def update_priors_from_trades(
        self,
        new_trade_outcomes: List[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        """
        Incorporate a batch of trade outcomes into prior distributions.

        Each item in `new_trade_outcomes` should be:
          {
             "won": True/False,   # strict boolean
             "features": ["oteo_band=85-92", "confidence=HIGH", ...]
          }

        The entire transaction is delegated to BayesianPriorStore (lock + RMW).
        """
        updated = self._store.update_from_trades(list(new_trade_outcomes))
        logger.info(
            "Bayesian priors updated at %s (wins=%s losses=%s trades=%s)",
            self.priors_json_path,
            updated.get("total_wins"),
            updated.get("total_losses"),
            updated.get("total_trades"),
        )
        return updated

    def save_priors_atomically(self, priors_data: Dict[str, Any]) -> None:
        """Replace the full priors document via the shared transactional store."""
        self._store.replace_all(priors_data)
        logger.info("Bayesian priors successfully replaced at %s", self.priors_json_path)
