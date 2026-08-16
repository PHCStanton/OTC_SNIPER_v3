from __future__ import annotations

import math
import logging
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Tuple
from collections import defaultdict

from .base import BaseExtension

logger = logging.getLogger(__name__)

# Resolve default priors file paths relative to this module — portable across machines.
_DEFAULT_PRIORS_DIR = Path(__file__).resolve().parents[3] / "data" / "ghost_trades" / "stats"
_DEFAULT_PRIORS_FILE_60S = _DEFAULT_PRIORS_DIR / "bayesian_priors.json"
_DEFAULT_PRIORS_FILE_300S = _DEFAULT_PRIORS_DIR / "bayesian_priors_300s.json"

# Shared transactional store (monorepo root on sys.path).
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from shared.bayesian_prior_store import (
        BayesianPriorStore,
        PriorStoreCorruptError,
        PriorStoreError,
    )
except ImportError:  # pragma: no cover
    BayesianPriorStore = None  # type: ignore[misc, assignment]
    PriorStoreCorruptError = Exception  # type: ignore[misc, assignment]
    PriorStoreError = Exception  # type: ignore[misc, assignment]


class BayesianSignalFilter(BaseExtension):
    """
    Cross-Asset Horizon-Aware Bayesian Signal Filter Extension.
    Evaluates Laplace-smoothed Naive Bayes probability P(Win | Market Context, Horizon)
    using isolated priors for 60s and 300s trading horizons.
    Explicitly omits raw asset ticker symbols to prevent single-day symbol bias.
    """

    def __init__(self, settings: Dict[str, Any]):
        defaults = {
            "enabled": False,
            "min_win_probability": 0.55,
        }
        defaults.update(settings)
        super().__init__(defaults)

        self.min_win_probability = float(self.settings.get("min_win_probability", 0.55))
        self.alpha = 1.0  # Laplace smoothing
        
        # Horizon prior files
        self.priors_file: Path = Path(settings.get("priors_file", _DEFAULT_PRIORS_FILE_60S))
        self.priors_file_300s: Path = Path(settings.get("priors_file_300s", _DEFAULT_PRIORS_FILE_300S))

        # In-process lock serializes memory refresh; file lock is process-wide (store).
        self._lock = threading.Lock()

        # Horizon isolated in-memory stores
        self._prior_stores: Dict[int, BayesianPriorStore] = {}
        self._priors_state: Dict[int, Dict[str, Any]] = {
            60: {"total_wins": 0, "total_losses": 0, "feature_counts": defaultdict(lambda: {"win": 0, "loss": 0})},
            300: {"total_wins": 0, "total_losses": 0, "feature_counts": defaultdict(lambda: {"win": 0, "loss": 0})},
        }

        if BayesianPriorStore is None:
            raise RuntimeError(
                "shared.bayesian_prior_store is not importable; "
                "ensure monorepo root is on PYTHONPATH"
            )

        self._prior_stores[60] = BayesianPriorStore(self.priors_file)
        self._prior_stores[300] = BayesianPriorStore(self.priors_file_300s)
        self._load_all_priors()

    # Backwards-compatible properties for 60s baseline
    @property
    def total_wins(self) -> int:
        return self._priors_state[60]["total_wins"]

    @total_wins.setter
    def total_wins(self, val: int) -> None:
        self._priors_state[60]["total_wins"] = val

    @property
    def total_losses(self) -> int:
        return self._priors_state[60]["total_losses"]

    @total_losses.setter
    def total_losses(self, val: int) -> None:
        self._priors_state[60]["total_losses"] = val

    @property
    def feature_counts(self) -> defaultdict:
        return self._priors_state[60]["feature_counts"]

    @feature_counts.setter
    def feature_counts(self, val: defaultdict) -> None:
        self._priors_state[60]["feature_counts"] = val

    @property
    def _prior_store(self) -> BayesianPriorStore:
        return self._prior_stores[60]

    # ------------------------------------------------------------------
    # Persistence (delegated to shared BayesianPriorStore)
    # ------------------------------------------------------------------

    def _apply_committed_state(self, data: Dict[str, Any], horizon: int = 60) -> None:
        """Refresh in-memory counters for a specific horizon from a committed store snapshot."""
        state = self._priors_state[horizon]
        state["total_wins"] = int(data.get("total_wins", 0))
        state["total_losses"] = int(data.get("total_losses", 0))
        raw_fc = data.get("feature_counts", {}) or {}
        state["feature_counts"].clear()
        for k, v in raw_fc.items():
            state["feature_counts"][k] = {
                "win": int(v.get("win", 0)),
                "loss": int(v.get("loss", 0)),
            }

    def _load_all_priors(self) -> None:
        """Load pre-seeded or persistent Bayesian priors for all horizons."""
        for horizon, store in self._prior_stores.items():
            try:
                data = store.read()
                self._apply_committed_state(data, horizon=horizon)
                state = self._priors_state[horizon]
                if store.priors_path.exists():
                    logger.info(
                        "BayesianSignalFilter (%ds) initialized with priors: %d Wins, %d Losses across %d pattern keys",
                        horizon,
                        state["total_wins"],
                        state["total_losses"],
                        len(state["feature_counts"]),
                    )
            except PriorStoreCorruptError as exc:
                logger.error(
                    "Corrupt Bayesian priors file for %ds — in-memory state left empty: %s",
                    horizon,
                    exc,
                )
            except PriorStoreError as exc:
                logger.error("Failed to load Bayesian priors file for %ds: %s", horizon, exc)

    # ------------------------------------------------------------------
    # Core Bayesian Logic
    # ------------------------------------------------------------------

    def _extract_features(self, oteo_result: Dict[str, Any]) -> Dict[str, str]:
        ec = oteo_result.get("entry_context") if isinstance(oteo_result.get("entry_context"), dict) else {}
        mc = oteo_result.get("market_context") or ec.get("market_context") or {}

        oteo_score_raw = oteo_result.get("oteo_score")
        if oteo_score_raw is None:
            oteo_score_raw = ec.get("oteo_score")
        oteo_score = float(oteo_score_raw if oteo_score_raw is not None else 50.0)

        if oteo_score < 65:
            oteo_band = "<65"
        elif oteo_score < 75:
            oteo_band = "65-74"
        elif oteo_score < 85:
            oteo_band = "75-84"
        elif oteo_score < 93:
            oteo_band = "85-92"
        else:
            oteo_band = "93+"

        regime = (
            oteo_result.get("regime_label")
            or ec.get("regime_label")
            or mc.get("regime_label")
            or "UNKNOWN"
        )
        regime = str(regime).upper()

        confidence = (
            oteo_result.get("confidence")
            or ec.get("confidence")
            or "MEDIUM"
        )
        confidence = str(confidence).upper()

        # Use explicit None check — `or` would treat 0.0 as falsy and miss the value.
        z_val = oteo_result.get("z_score")
        if z_val is None:
            z_val = ec.get("z_score")
        if z_val is None:
            z_val = mc.get("z_score")

        if z_val is not None:
            try:
                zv = float(z_val)
                if zv < -1.5:
                    z_band = "<-1.5"
                elif zv < -0.5:
                    z_band = "-1.5_to_-0.5"
                elif zv <= 0.5:
                    z_band = "-0.5_to_0.5"
                elif zv <= 1.5:
                    z_band = "0.5_to_1.5"
                else:
                    z_band = ">1.5"
            except (ValueError, TypeError):
                z_band = "UNKNOWN"
        else:
            z_band = "UNKNOWN"

        manip = oteo_result.get("manipulation")
        if manip is None:
            manip = ec.get("manipulation")
        if manip is None:
            manip = mc.get("manipulation")
        has_manip = bool(manip) if isinstance(manip, (dict, list, bool)) else False

        direction = str(
            oteo_result.get("recommended")
            or oteo_result.get("direction")
            or ec.get("recommended")
            or ec.get("direction")
            or "CALL"
        ).upper()

        return {
            "oteo_band": oteo_band,
            "regime": regime,
            "confidence": confidence,
            "z_band": z_band,
            "has_manip": "MANIP_TRUE" if has_manip else "MANIP_FALSE",
            "direction": direction,
        }

    def predict_win_probability(
        self, oteo_result: Dict[str, Any], horizon_seconds: int = 60
    ) -> float:
        """Calculate Laplace-smoothed Naive Bayes probability P(Win | Market Context, Horizon)."""
        horizon = 300 if horizon_seconds == 300 else 60
        state = self._priors_state.get(horizon, self._priors_state[60])

        total_w = state["total_wins"]
        total_l = state["total_losses"]
        fcounts = state["feature_counts"]

        prior_total = total_w + total_l
        prior_win = (total_w / prior_total) if prior_total > 0 else 0.5
        prior_loss = (total_l / prior_total) if prior_total > 0 else 0.5

        log_prob_win = math.log(max(prior_win, 1e-6))
        log_prob_loss = math.log(max(prior_loss, 1e-6))

        feats = self._extract_features(oteo_result)
        for k, v in feats.items():
            key = f"{k}={v}"
            counts = fcounts.get(key, {"win": 0, "loss": 0})
            win_cnt = counts["win"]
            loss_cnt = counts["loss"]

            p_feat_win = (win_cnt + self.alpha) / (total_w + self.alpha * 2) if (total_w + self.alpha * 2) > 0 else 0.5
            p_feat_loss = (loss_cnt + self.alpha) / (total_l + self.alpha * 2) if (total_l + self.alpha * 2) > 0 else 0.5

            log_prob_win += math.log(max(p_feat_win, 1e-9))
            log_prob_loss += math.log(max(p_feat_loss, 1e-9))

        max_log = max(log_prob_win, log_prob_loss)
        prob_win_exp = math.exp(log_prob_win - max_log)
        prob_loss_exp = math.exp(log_prob_loss - max_log)

        return prob_win_exp / (prob_win_exp + prob_loss_exp)

    # ------------------------------------------------------------------
    # Extension Lifecycle Hooks
    # ------------------------------------------------------------------

    def on_tick_processed(
        self,
        asset: str,
        price: float,
        timestamp: float,
        oteo_result: Dict[str, Any],
        market_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Inject Bayesian win probability prediction into oteo_result telemetry."""
        if self.enabled:
            prob_60 = self.predict_win_probability(oteo_result, horizon_seconds=60)
            prob_300 = self.predict_win_probability(oteo_result, horizon_seconds=300)

            oteo_result["bayesian_win_probability"] = round(prob_60, 4)
            oteo_result["bayesian_win_probability_60s"] = round(prob_60, 4)
            oteo_result["bayesian_win_probability_300s"] = round(prob_300, 4)
            if "market_context" not in oteo_result or not isinstance(oteo_result["market_context"], dict):
                oteo_result["market_context"] = {}
            oteo_result["market_context"]["bayesian_win_probability"] = round(prob_60, 4)
            oteo_result["market_context"]["bayesian_win_probability_60s"] = round(prob_60, 4)
            oteo_result["market_context"]["bayesian_win_probability_300s"] = round(prob_300, 4)
        return oteo_result

    def on_consider_signal(
        self,
        asset: str,
        price: float,
        oteo_result: Dict[str, Any],
        config: Any,
    ) -> Tuple[bool, str | None]:
        """Veto Gate hook: evaluate Bayesian Win Probability floor for the target horizon."""
        enabled = self.enabled
        min_prob = self.min_win_probability
        if hasattr(config, "bayesian_filter_enabled"):
            enabled = bool(config.bayesian_filter_enabled)
        if hasattr(config, "bayesian_min_probability"):
            min_prob = float(config.bayesian_min_probability)

        if not enabled:
            return True, None

        # Inspect target expiration duration (defaults to 60s)
        target_exp = (
            oteo_result.get("override_expiration_seconds")
            or oteo_result.get("target_expiration")
            or getattr(config, "default_expiration_seconds", 60)
            or 60
        )
        try:
            target_exp_int = int(target_exp)
        except (ValueError, TypeError):
            target_exp_int = 60

        horizon = 300 if target_exp_int == 300 else 60
        state = self._priors_state.get(horizon, self._priors_state[60])

        # Fail-closed check: if priors for this horizon are empty, reject the trade explicitly
        if (state["total_wins"] + state["total_losses"]) == 0:
            reason = f"bayesian_priors_unavailable (priors file for {horizon}s empty or missing)"
            logger.info("BayesianSignalFilter REJECTED trade for %s (%ds): %s", asset, horizon, reason)
            return False, reason

        prob = self.predict_win_probability(oteo_result, horizon_seconds=horizon)
        oteo_result["bayesian_win_probability"] = round(prob, 4)

        if prob < min_prob:
            reason = f"Bayesian Win Probability ({horizon}s: {prob*100:.1f}%) below minimum floor ({min_prob*100:.1f}%)"
            logger.info("BayesianSignalFilter REJECTED trade for %s (%ds): %s", asset, horizon, reason)
            return False, reason

        return True, None

    def on_trade_outcome(self, trade_data: Dict[str, Any]) -> None:
        """Online updating: increment feature counts into the matching horizon priors store."""
        outcome = trade_data.get("outcome")
        if outcome not in ("win", "loss"):
            return

        # Duration/Horizon verification
        exp_sec = trade_data.get("expiration_seconds")
        if exp_sec is None and isinstance(trade_data.get("entry_context"), dict):
            exp_sec = trade_data["entry_context"].get("expiration_seconds")

        if exp_sec is None:
            logger.warning(
                "BayesianSignalFilter skipped trade outcome for %s: missing expiration_seconds (Fail-Closed)",
                trade_data.get("asset", "unknown"),
            )
            return

        try:
            exp_int = int(exp_sec)
        except (ValueError, TypeError):
            logger.warning(
                "BayesianSignalFilter skipped trade outcome: invalid expiration_seconds %r",
                exp_sec,
            )
            return

        if exp_int not in (60, 300):
            logger.debug(
                "BayesianSignalFilter skipped unsupported horizon outcome (%ds) for %s",
                exp_int,
                trade_data.get("asset", "unknown"),
            )
            return

        feats = self._extract_features(trade_data)
        feature_keys = [f"{k}={v}" for k, v in feats.items()]
        won = outcome == "win"

        store = self._prior_stores.get(exp_int)
        if not store:
            return

        try:
            committed = store.update_from_trades(
                [{"won": won, "features": feature_keys}]
            )
        except PriorStoreError as exc:
            logger.error("Failed to persist Bayesian trade outcome for %ds: %s", exp_int, exc)
            raise

        with self._lock:
            self._apply_committed_state(committed, horizon=exp_int)

