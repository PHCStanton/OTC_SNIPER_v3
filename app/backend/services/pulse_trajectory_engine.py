from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger("app.backend.services.pulse_trajectory_engine")

CHECKPOINT_INTERVALS = [30, 60, 120, 180, 300]

# H1 fix: post-settlement observation window. Short-horizon (60s) losing pulse trades
# remain registered for checkpoint sampling until this horizon elapses so late
# checkpoints (120s/180s/300s) can upgrade the attribution at final settlement.
OBSERVATION_WINDOW_SECONDS = max(CHECKPOINT_INTERVALS)
MAX_OBSERVATION_TRADES = 200  # bounded eviction cap


@dataclass
class ActivePulseTrade:
    trade_id: str
    asset: str
    direction: str  # "call" or "put"
    entry_price: float
    opened_at: float
    expiration_seconds: int
    entry_context: Dict[str, Any] = field(default_factory=dict)
    checkpoints: Dict[int, Optional[float]] = field(
        default_factory=lambda: {interval: None for interval in CHECKPOINT_INTERVALS}
    )
    checkpoint_timestamps: Dict[int, Optional[float]] = field(
        default_factory=lambda: {interval: None for interval in CHECKPOINT_INTERVALS}
    )
    mfe: float = 0.0  # Max favorable excursion (in price units > 0)
    mae: float = 0.0  # Max adverse excursion (in price units > 0)
    min_price_seen: float = 0.0
    max_price_seen: float = 0.0

    def __post_init__(self):
        self.min_price_seen = self.entry_price
        self.max_price_seen = self.entry_price
        self.direction = self.direction.lower()


class PulseTrajectoryEngine:
    """
    Tracks real-time price trajectories for AI Pulse forecasted trades,
    captures intermediate checkpoints at [30s, 60s, 120s, 180s, 300s],
    computes MFE/MAE excursions, and performs diagnostic post-mortems.
    """

    _instance: Optional[PulseTrajectoryEngine] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> PulseTrajectoryEngine:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self._active_trades: Dict[str, ActivePulseTrade] = {}  # trade_id -> ActivePulseTrade
        self._settled_trajectories: Deque[Dict[str, Any]] = deque(maxlen=500)
        # H1 fix: settled short-horizon losses awaiting final classification
        self._observation_trades: Dict[str, Dict[str, Any]] = {}
        self._trade_lock = threading.Lock()

    def register_pulse_trade(
        self,
        trade_id: str,
        asset: str,
        direction: str,
        entry_price: float,
        opened_at: float | None = None,
        expiration_seconds: int = 60,
        entry_context: Dict[str, Any] | None = None,
    ) -> None:
        """Register a newly opened AI Pulse trade for trajectory tracking."""
        if not trade_id or entry_price <= 0:
            return

        opened = opened_at if (opened_at and opened_at > 0) else time.time()
        trade = ActivePulseTrade(
            trade_id=trade_id,
            asset=asset,
            direction=direction,
            entry_price=entry_price,
            opened_at=opened,
            expiration_seconds=int(expiration_seconds or 60),
            entry_context=entry_context or {},
        )
        with self._trade_lock:
            self._active_trades[trade_id] = trade
        logger.info("PulseTrajectoryEngine registered active AI Pulse trade %s (%s %s @ %.5f)", trade_id, asset, direction, entry_price)

    def record_tick(self, asset: str, price: float, timestamp: float | None = None) -> None:
        """Update active pulse trades on incoming tick for the given asset."""
        # H1 fix: also process ticks while observation-window trades await final classification
        if price <= 0 or (not self._active_trades and not self._observation_trades):
            return

        ts = timestamp if (timestamp and timestamp > 0) else time.time()

        with self._trade_lock:
            for trade in list(self._active_trades.values()):
                if trade.asset != asset:
                    continue

                elapsed = ts - trade.opened_at
                if elapsed < 0:
                    continue

                # Update price extrema
                if price < trade.min_price_seen:
                    trade.min_price_seen = price
                if price > trade.max_price_seen:
                    trade.max_price_seen = price

                # Calculate excursion relative to direction
                is_call = trade.direction == "call"
                if is_call:
                    fav = price - trade.entry_price
                    adv = trade.entry_price - price
                else:
                    fav = trade.entry_price - price
                    adv = price - trade.entry_price

                if fav > trade.mfe:
                    trade.mfe = fav
                if adv > trade.mae:
                    trade.mae = adv

                # Fill checkpoints
                for interval in CHECKPOINT_INTERVALS:
                    if trade.checkpoints[interval] is None and elapsed >= interval:
                        trade.checkpoints[interval] = price
                        trade.checkpoint_timestamps[interval] = ts

        # H1 fix: continue checkpoint sampling for settled short-horizon losses in the
        # observation window; finalize their attribution once the window completes.
        with self._trade_lock:
            finalized_ids: List[str] = []
            for obs_id, obs in list(self._observation_trades.items()):
                obs_trade = obs["trade"]
                if obs_trade.asset != asset:
                    continue

                elapsed = ts - obs_trade.opened_at
                if elapsed < 0:
                    continue

                if price < obs_trade.min_price_seen:
                    obs_trade.min_price_seen = price
                if price > obs_trade.max_price_seen:
                    obs_trade.max_price_seen = price

                is_call = obs_trade.direction == "call"
                fav = (price - obs_trade.entry_price) if is_call else (obs_trade.entry_price - price)
                adv = (obs_trade.entry_price - price) if is_call else (price - obs_trade.entry_price)
                if fav > obs_trade.mfe:
                    obs_trade.mfe = fav
                if adv > obs_trade.mae:
                    obs_trade.mae = adv

                for interval in CHECKPOINT_INTERVALS:
                    if obs_trade.checkpoints[interval] is None and elapsed >= interval:
                        obs_trade.checkpoints[interval] = price
                        obs_trade.checkpoint_timestamps[interval] = ts

                if elapsed >= OBSERVATION_WINDOW_SECONDS:
                    finalized_ids.append(obs_id)

        # Finalize outside the lock — _finalize_observation acquires it itself.
        for obs_id in finalized_ids:
            self._finalize_observation(obs_id)

    def _finalize_observation(self, trade_id: str) -> None:
        """Re-classify a settled short-horizon loss once its observation window completes."""
        obs = self._observation_trades.pop(trade_id, None)
        if not obs:
            return

        trade: ActivePulseTrade = obs["trade"]
        exit_p = obs["exit_price"]
        norm_outcome = obs["outcome"]
        is_call = trade.direction == "call"

        eval_checkpoints: Dict[str, Dict[str, Any]] = {}
        for interval in CHECKPOINT_INTERVALS:
            cp_price = trade.checkpoints.get(interval)
            if cp_price is not None:
                fav = (cp_price > trade.entry_price) if is_call else (cp_price < trade.entry_price)
                diff = (cp_price - trade.entry_price) if is_call else (trade.entry_price - cp_price)
                eval_checkpoints[f"{interval}s"] = {
                    "price": cp_price,
                    "favorable": fav,
                    "diff": round(diff, 6),
                }
            else:
                eval_checkpoints[f"{interval}s"] = {
                    "price": None,
                    "favorable": None,
                    "diff": 0.0,
                }

        attribution, recommendation, recommended_horizon = self._classify_attribution(
            trade, eval_checkpoints, norm_outcome
        )

        final_report: Dict[str, Any] = {
            "trade_id": trade_id,
            "asset": trade.asset,
            "direction": trade.direction.upper(),
            "entry_price": trade.entry_price,
            "exit_price": exit_p,
            "outcome": norm_outcome,
            "expiration_seconds": trade.expiration_seconds,
            "opened_at": trade.opened_at,
            "settled_at": obs["settled_at"],
            "mfe": round(trade.mfe, 6),
            "mae": round(trade.mae, 6),
            "checkpoints": eval_checkpoints,
            "attribution": attribution,
            "recommendation": recommendation,
            "recommended_horizon": recommended_horizon,
            "regime": trade.entry_context.get("regime_label") or trade.entry_context.get("regime", "UNKNOWN"),
            "pulse_confidence": trade.entry_context.get("pulse_confidence"),
            "attribution_finalized": True,
            "initial_attribution": obs.get("initial_attribution"),
        }

        with self._trade_lock:
            for i, existing in enumerate(self._settled_trajectories):
                if existing.get("trade_id") == trade_id:
                    self._settled_trajectories[i] = final_report
                    break
            else:
                self._settled_trajectories.append(final_report)

        logger.info(
            "PulseTrajectoryEngine finalized observation for %s: attribution=%s (initial=%s)",
            trade_id,
            attribution,
            obs.get("initial_attribution"),
        )

    @staticmethod
    def _classify_attribution(
        trade: ActivePulseTrade,
        eval_checkpoints: Dict[str, Dict[str, Any]],
        norm_outcome: str,
    ) -> tuple[str, str, Optional[int]]:
        """Shared post-mortem classification rules for initial and final settlement."""
        attribution = "DIRECTIONAL_FAIL"
        recommendation = "Setup invalidated by broad market direction."
        recommended_horizon: Optional[int] = None

        cp_60_fav = eval_checkpoints["60s"]["favorable"]
        cp_180_fav = eval_checkpoints["180s"]["favorable"]
        cp_300_fav = eval_checkpoints["300s"]["favorable"]

        if norm_outcome == "win":
            attribution = "CLEAN_WIN"
            recommendation = f"Optimal execution horizon at {trade.expiration_seconds}s."
            recommended_horizon = trade.expiration_seconds
        else:
            # Trade lost
            if trade.expiration_seconds == 60 and (cp_180_fav is True or cp_300_fav is True):
                attribution = "PREMATURE_EXPIRATION"
                recommendation = "Direction proved correct over structural window. Recommend extending horizon to 300s for this regime."
                recommended_horizon = 300
            elif trade.expiration_seconds == 300 and cp_60_fav is True:
                attribution = "MOMENTUM_EXHAUSTION"
                recommendation = "Target was achieved quickly before reversing. Recommend clamping horizon to 60s for high velocity setups."
                recommended_horizon = 60
            elif trade.mae > 0 and trade.mfe <= (trade.mae * 0.1):
                attribution = "STRUCTURAL_TRAP"
                recommendation = "Immediate adverse movement with no pullback. Recommend tightening manipulation and spike filters."
                recommended_horizon = None
            else:
                attribution = "DIRECTIONAL_FAIL"
                recommendation = "General directional failure across all sampled intervals."
                recommended_horizon = None

        return attribution, recommendation, recommended_horizon

    def settle_pulse_trade(
        self,
        trade_id: str,
        exit_price: float | None,
        outcome: str,
        settled_at: float | None = None,
    ) -> Optional[Dict[str, Any]]:
        """Settle an AI Pulse trade, classify post-mortem trajectory attribution, and return diagnosis."""
        with self._trade_lock:
            trade = self._active_trades.pop(trade_id, None)

        if not trade:
            return None

        exit_p = exit_price if (exit_price is not None and exit_price > 0) else trade.entry_price
        norm_outcome = outcome.lower() if outcome else "void"
        is_call = trade.direction == "call"

        # Evaluate checkpoint outcomes (was price favorable at interval T?)
        eval_checkpoints: Dict[str, Dict[str, Any]] = {}
        for interval in CHECKPOINT_INTERVALS:
            cp_price = trade.checkpoints.get(interval)
            if cp_price is not None:
                fav = (cp_price > trade.entry_price) if is_call else (cp_price < trade.entry_price)
                diff = (cp_price - trade.entry_price) if is_call else (trade.entry_price - cp_price)
                eval_checkpoints[f"{interval}s"] = {
                    "price": cp_price,
                    "favorable": fav,
                    "diff": round(diff, 6),
                }
            else:
                eval_checkpoints[f"{interval}s"] = {
                    "price": None,
                    "favorable": None,
                    "diff": 0.0,
                }

        # Post-Mortem Classification Rules
        attribution = "DIRECTIONAL_FAIL"
        recommendation = "Setup invalidated by broad market direction."
        recommended_horizon: Optional[int] = None

        cp_60_fav = eval_checkpoints["60s"]["favorable"]
        cp_180_fav = eval_checkpoints["180s"]["favorable"]
        cp_300_fav = eval_checkpoints["300s"]["favorable"]

        if norm_outcome == "win":
            attribution = "CLEAN_WIN"
            recommendation = f"Optimal execution horizon at {trade.expiration_seconds}s."
            recommended_horizon = trade.expiration_seconds
        else:
            # Trade lost
            if trade.expiration_seconds == 60 and (cp_180_fav is True or cp_300_fav is True):
                attribution = "PREMATURE_EXPIRATION"
                recommendation = "Direction proved correct over structural window. Recommend extending horizon to 300s for this regime."
                recommended_horizon = 300
            elif trade.expiration_seconds == 300 and cp_60_fav is True:
                attribution = "MOMENTUM_EXHAUSTION"
                recommendation = "Target was achieved quickly before reversing. Recommend clamping horizon to 60s for high velocity setups."
                recommended_horizon = 60
            elif trade.mae > 0 and trade.mfe <= (trade.mae * 0.1):
                attribution = "STRUCTURAL_TRAP"
                recommendation = "Immediate adverse movement with no pullback. Recommend tightening manipulation and spike filters."
                recommended_horizon = None
            else:
                attribution = "DIRECTIONAL_FAIL"
                recommendation = "General directional failure across all sampled intervals."
                recommended_horizon = None

        trajectory_report: Dict[str, Any] = {
            "trade_id": trade_id,
            "asset": trade.asset,
            "direction": trade.direction.upper(),
            "entry_price": trade.entry_price,
            "exit_price": exit_p,
            "outcome": norm_outcome,
            "expiration_seconds": trade.expiration_seconds,
            "opened_at": trade.opened_at,
            "settled_at": settled_at or time.time(),
            "mfe": round(trade.mfe, 6),
            "mae": round(trade.mae, 6),
            "checkpoints": eval_checkpoints,
            "attribution": attribution,
            "recommendation": recommendation,
            "recommended_horizon": recommended_horizon,
            "regime": trade.entry_context.get("regime_label") or trade.entry_context.get("regime", "UNKNOWN"),
            "pulse_confidence": trade.entry_context.get("pulse_confidence"),
        }

        with self._trade_lock:
            self._settled_trajectories.append(trajectory_report)

        # H1 fix: short-horizon losses enter the post-settlement observation window so
        # late checkpoints (120s/180s/300s) can upgrade the attribution at final settlement.
        if norm_outcome == "loss" and trade.expiration_seconds < OBSERVATION_WINDOW_SECONDS:
            with self._trade_lock:
                # Bounded eviction cap — drop the oldest observation when full
                if len(self._observation_trades) >= MAX_OBSERVATION_TRADES:
                    oldest_id = next(iter(self._observation_trades))
                    self._observation_trades.pop(oldest_id, None)
                self._observation_trades[trade_id] = {
                    "trade": trade,
                    "exit_price": exit_p,
                    "outcome": norm_outcome,
                    "settled_at": settled_at or time.time(),
                    "initial_attribution": attribution,
                }

        logger.info(
            "PulseTrajectoryEngine settled %s: outcome=%s attribution=%s (rec: %s)",
            trade_id,
            norm_outcome,
            attribution,
            recommendation,
        )
        return trajectory_report

    def get_trajectory_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent settled pulse trade trajectories."""
        with self._trade_lock:
            return list(self._settled_trajectories)[-limit:]

    def get_trajectory_analytics(self) -> Dict[str, Any]:
        """Aggregate attribution distribution and horizon recommendations."""
        with self._trade_lock:
            trajs = list(self._settled_trajectories)

        total = len(trajs)
        if total == 0:
            return {
                "total_trades": 0,
                "clean_wins": 0,
                "premature_expirations": 0,
                "momentum_exhaustions": 0,
                "structural_traps": 0,
                "directional_fails": 0,
                "win_rate": 0.0,
                "horizon_recommendations": {"60s": 0, "300s": 0},
                "recent_trajectories": [],
            }

        counts = {
            "CLEAN_WIN": 0,
            "PREMATURE_EXPIRATION": 0,
            "MOMENTUM_EXHAUSTION": 0,
            "STRUCTURAL_TRAP": 0,
            "DIRECTIONAL_FAIL": 0,
        }
        rec_horizons = {"60s": 0, "300s": 0}
        wins = 0

        for t in trajs:
            attr = t.get("attribution", "DIRECTIONAL_FAIL")
            counts[attr] = counts.get(attr, 0) + 1
            if t.get("outcome") == "win":
                wins += 1
            rec_h = t.get("recommended_horizon")
            if rec_h == 60:
                rec_horizons["60s"] += 1
            elif rec_h == 300:
                rec_horizons["300s"] += 1

        return {
            "total_trades": total,
            "clean_wins": counts.get("CLEAN_WIN", 0),
            "premature_expirations": counts.get("PREMATURE_EXPIRATION", 0),
            "momentum_exhaustions": counts.get("MOMENTUM_EXHAUSTION", 0),
            "structural_traps": counts.get("STRUCTURAL_TRAP", 0),
            "directional_fails": counts.get("DIRECTIONAL_FAIL", 0),
            "win_rate": round((wins / total) * 100.0, 1),
            "horizon_recommendations": rec_horizons,
            "recent_trajectories": trajs[-10:],
        }
