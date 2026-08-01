from __future__ import annotations

import json
import math
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Tuple
from collections import defaultdict

from .base import BaseExtension

logger = logging.getLogger(__name__)

# Resolve priors file path relative to this module — portable across machines.
_DEFAULT_PRIORS_FILE = Path(__file__).resolve().parents[3] / "data" / "ghost_trades" / "stats" / "bayesian_priors.json"


class BayesianSignalFilter(BaseExtension):
    """
    Cross-Asset Bayesian Signal Filter Extension.
    Evaluates Laplace-smoothed Naive Bayes probability P(Win | Market Context)
    using pure cross-asset market features (OTEO Score, Regime, Z-Score, Confidence, Manipulation).
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
        # R3: relative path — portable across machines and deployments.
        self.priors_file: Path = settings.get("priors_file", _DEFAULT_PRIORS_FILE)

        # R4: lock guards all online-update mutations (on_trade_outcome).
        self._lock = threading.Lock()

        self.total_wins = 0
        self.total_losses = 0
        self.feature_counts: defaultdict = defaultdict(lambda: {"win": 0, "loss": 0})
        self._load_priors()

        # R1: warn explicitly when operating without any prior observations.
        if self.total_wins + self.total_losses == 0:
            logger.warning(
                "BayesianSignalFilter operating with EMPTY priors — "
                "all predictions will be ~0.50 until trade outcomes are recorded."
            )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_priors(self) -> None:
        """Load pre-seeded or persistent Bayesian priors from JSON file."""
        if self.priors_file.exists():
            try:
                with open(self.priors_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.total_wins = int(data.get("total_wins", 0))
                    self.total_losses = int(data.get("total_losses", 0))
                    raw_fc = data.get("feature_counts", {})
                    self.feature_counts.clear()
                    for k, v in raw_fc.items():
                        self.feature_counts[k] = {"win": int(v.get("win", 0)), "loss": int(v.get("loss", 0))}
                logger.info(
                    "BayesianSignalFilter initialized with priors: %d Wins, %d Losses across %d pattern keys",
                    self.total_wins,
                    self.total_losses,
                    len(self.feature_counts),
                )
            except Exception as exc:
                logger.error("Failed to load Bayesian priors file: %s", exc)

    def _save_priors(self) -> None:
        """Persist updated priors back to file."""
        try:
            self.priors_file.parent.mkdir(parents=True, exist_ok=True)
            priors_data = {
                "total_wins": self.total_wins,
                "total_losses": self.total_losses,
                "total_trades": self.total_wins + self.total_losses,
                "feature_counts": dict(self.feature_counts),
            }
            with open(self.priors_file, "w", encoding="utf-8") as f:
                json.dump(priors_data, f, indent=2)
        except Exception as exc:
            logger.error("Failed to save Bayesian priors: %s", exc)

    # ------------------------------------------------------------------
    # Core Bayesian Logic
    # ------------------------------------------------------------------

    def _extract_features(self, oteo_result: Dict[str, Any]) -> Dict[str, str]:
        mc = oteo_result.get("market_context") or {}

        oteo_score = float(oteo_result.get("oteo_score") or 50.0)
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

        regime = oteo_result.get("regime_label") or mc.get("regime_label") or "UNKNOWN"
        regime = str(regime).upper()

        confidence = oteo_result.get("confidence") or "MEDIUM"
        confidence = str(confidence).upper()

        # Use explicit None check — `or` would treat 0.0 as falsy and miss the value.
        z_val = oteo_result.get("z_score")
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

        manip = oteo_result.get("manipulation") or mc.get("manipulation")
        has_manip = bool(manip) if isinstance(manip, (dict, list, bool)) else False
        direction = str(oteo_result.get("recommended") or oteo_result.get("direction") or "CALL").upper()

        return {
            "oteo_band": oteo_band,
            "regime": regime,
            "confidence": confidence,
            "z_band": z_band,
            "has_manip": "MANIP_TRUE" if has_manip else "MANIP_FALSE",
            "direction": direction,
        }

    def predict_win_probability(self, oteo_result: Dict[str, Any]) -> float:
        feats = self._extract_features(oteo_result)

        prior_total = self.total_wins + self.total_losses
        prior_win = (self.total_wins / prior_total) if prior_total > 0 else 0.5
        prior_loss = (self.total_losses / prior_total) if prior_total > 0 else 0.5

        log_prob_win = math.log(max(prior_win, 1e-6))
        log_prob_loss = math.log(max(prior_loss, 1e-6))

        for k, v in feats.items():
            key = f"{k}={v}"
            # R2: use .get() to avoid defaultdict auto-vivification of phantom keys
            # on mere read access, which would pollute the priors file with zero-count entries.
            counts = self.feature_counts.get(key, {"win": 0, "loss": 0})
            win_cnt = counts["win"]
            loss_cnt = counts["loss"]

            p_feat_win = (win_cnt + self.alpha) / (self.total_wins + self.alpha * 2)
            p_feat_loss = (loss_cnt + self.alpha) / (self.total_losses + self.alpha * 2)

            log_prob_win += math.log(p_feat_win)
            log_prob_loss += math.log(p_feat_loss)

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
            prob = self.predict_win_probability(oteo_result)
            oteo_result["bayesian_win_probability"] = round(prob, 4)
            if "market_context" not in oteo_result or not isinstance(oteo_result["market_context"], dict):
                oteo_result["market_context"] = {}
            oteo_result["market_context"]["bayesian_win_probability"] = round(prob, 4)
        return oteo_result

    def on_consider_signal(
        self,
        asset: str,
        price: float,
        oteo_result: Dict[str, Any],
        config: Any,
    ) -> Tuple[bool, str | None]:
        """Veto Gate hook: evaluate Bayesian Win Probability floor.

        Note: self.enabled and self.min_win_probability are kept in sync by
        AutoGhostService.update_config() before this hook fires. The config
        attributes are only read here as a safety net for direct callers that
        bypass the service layer (e.g., tests using DummyConfig).
        """
        # R5: read config as a fallback only — do NOT mutate self.enabled here
        # to avoid redundant state writes (auto_ghost already syncs state).
        enabled = self.enabled
        min_prob = self.min_win_probability
        if hasattr(config, "bayesian_filter_enabled"):
            enabled = bool(config.bayesian_filter_enabled)
        if hasattr(config, "bayesian_min_probability"):
            min_prob = float(config.bayesian_min_probability)

        if not enabled:
            return True, None

        # R6: reuse the probability already computed by on_tick_processed if
        # available — avoids redundant feature extraction and log-space math.
        prob = oteo_result.get("bayesian_win_probability")
        if prob is None:
            prob = self.predict_win_probability(oteo_result)
            oteo_result["bayesian_win_probability"] = round(prob, 4)

        if prob < min_prob:
            reason = f"Bayesian Win Probability ({prob*100:.1f}%) below minimum floor ({min_prob*100:.1f}%)"
            logger.info("BayesianSignalFilter REJECTED trade for %s: %s", asset, reason)
            return False, reason

        return True, None

    def on_trade_outcome(self, trade_data: Dict[str, Any]) -> None:
        """Online updating: increment feature counts as live ghost trades resolve.

        R4: all mutations are protected by a threading.Lock to prevent race
        conditions when multiple assets resolve simultaneously.
        """
        outcome = trade_data.get("outcome")
        if outcome not in ("win", "loss"):
            return

        feats = self._extract_features(trade_data)

        with self._lock:
            if outcome == "win":
                self.total_wins += 1
            else:
                self.total_losses += 1

            for k, v in feats.items():
                self.feature_counts[f"{k}={v}"][outcome] += 1

        self._save_priors()
