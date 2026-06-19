from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, replace
from time import time as unix_time
from typing import Any

from ..brokers.base import BrokerType
from ..models.requests import TradeExecutionRequest
from .trade_service import TradeService

logger = logging.getLogger(__name__)


def _get_severity(val: Any) -> float:
    """Extract a numeric severity from a manipulation flag value."""
    if isinstance(val, bool):
        return 1.0 if val else 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 1.0 if val else 0.0


@dataclass(frozen=True)
class AutoGhostConfig:
    enabled: bool = False
    amount: float = 1.0
    expiration_seconds: int = 60
    max_concurrent_trades: int = 3
    per_asset_cooldown_seconds: int = 30
    minimum_payout_pct: float = 88.0
    block_on_manipulation: bool = True
    manipulation_severity_threshold: float = 0.0  # 0.0 to 1.0 (default 0.0 is block on any)
    max_session_trades: int = 100
    max_drawdown_amount: float = 0.0
    drawdown_cooldown_seconds: int = 300
    min_confidence_enabled: bool = False
    min_confidence: float | None = None
    max_confidence_enabled: bool = False
    max_confidence: float | None = None
    max_trades_per_timeframe: int = 0
    timeframe_seconds: int = 0
    oteo_ai_enabled: bool = False
    oteo_ai_execution_mode: str = "advisory"
    ai_trade_interval: int = 10
    ai_pulse_enabled: bool = False
    ai_pulse_interval_seconds: int = 120
    min_zscore_enabled: bool = False
    min_zscore: float | None = None
    max_zscore_enabled: bool = False
    max_zscore: float | None = None
    regime_gate_enabled: bool = False
    allowed_regimes: list[str] | None = None
    require_regime_stable: bool = False
    hurst_filter_enabled: bool = False
    hurst_filter_threshold: float = 0.48
    hurst_mean_revert_threshold: float = 0.44
    hurst_trend_threshold: float = 0.58
    min_adaptive_expiry: int = 60
    hurst_min_scale_cutoff: int = 12
    hurst_ai_confidence_threshold: float = 80.0


class AutoGhostService:
    CONFIRMATION_TICKS = 1

    def __init__(self, trade_service: TradeService, config: AutoGhostConfig | None = None):
        self.trade_service = trade_service
        self.config = config or AutoGhostConfig()
        self.extension_manager = None
        self._active_assets: set[str] = set()
        self._cooldown_until: dict[str, float] = {}
        self._pending_signals: dict[str, tuple[dict[str, Any], int]] = {}
        self._consecutive_losses: dict[str, int] = {}
        self._condition_stats: dict[str, dict[str, int]] = {}
        self._session_id: str | None = None
        self._session_pnl: float = 0.0
        self._session_trade_count: int = 0
        self._session_wins: int = 0
        self._session_losses: int = 0
        self._drawdown_cooldown_until: float = 0.0
        self._session_halted: bool = False
        self._current_streak_type: str | None = None
        self._current_streak_count: int = 0
        self._max_win_streak: int = 0
        self._max_loss_streak: int = 0
        self._last_streak_start_time: float = 0.0
        self._avg_recovery_time: float = 0.0
        self._total_recovery_sessions: int = 0
        self._trade_timestamps: list[float] = []
        self._last_reject_reason_by_asset: dict[str, str] = {}
        self._reject_counts: dict[str, int] = {}

    def _record_reject(self, asset: str, reason: str) -> None:
        self._last_reject_reason_by_asset[asset] = reason
        self._reject_counts[reason] = self._reject_counts.get(reason, 0) + 1

    def update_config(
        self,
        *,
        enabled: bool | None = None,
        amount: float | None = None,
        expiration_seconds: int | None = None,
        max_concurrent_trades: int | None = None,
        per_asset_cooldown_seconds: int | None = None,
        minimum_payout_pct: float | None = None,
        max_session_trades: int | None = None,
        max_drawdown_amount: float | None = None,
        drawdown_cooldown_seconds: int | None = None,
        manipulation_severity_threshold: float | None = None,
        block_on_manipulation: bool | None = None,
        min_confidence_enabled: bool | None = None,
        min_confidence: float | None = None,
        max_confidence_enabled: bool | None = None,
        max_confidence: float | None = None,
        max_trades_per_timeframe: int | None = None,
        timeframe_seconds: int | None = None,
        oteo_ai_enabled: bool | None = None,
        oteo_ai_execution_mode: str | None = None,
        ai_trade_interval: int | None = None,
        ai_pulse_enabled: bool | None = None,
        ai_pulse_interval_seconds: int | None = None,
        min_zscore_enabled: bool | None = None,
        min_zscore: float | None = None,
        max_zscore_enabled: bool | None = None,
        max_zscore: float | None = None,
        regime_gate_enabled: bool | None = None,
        allowed_regimes: list[str] | None = None,
        require_regime_stable: bool | None = None,
        hurst_filter_enabled: bool | None = None,
        hurst_filter_threshold: float | None = None,
        hurst_mean_revert_threshold: float | None = None,
        hurst_trend_threshold: float | None = None,
        min_adaptive_expiry: int | None = None,
        hurst_min_scale_cutoff: int | None = None,
        hurst_ai_confidence_threshold: float | None = None,
    ) -> dict[str, Any]:
        previous_enabled = self.config.enabled
        updates: dict[str, Any] = {}
        if enabled is not None:
            updates["enabled"] = bool(enabled)
        if amount is not None:
            updates["amount"] = max(0.1, float(amount))
        if expiration_seconds is not None:
            updates["expiration_seconds"] = max(5, int(expiration_seconds))
        if max_concurrent_trades is not None:
            updates["max_concurrent_trades"] = max(1, int(max_concurrent_trades))
        if per_asset_cooldown_seconds is not None:
            updates["per_asset_cooldown_seconds"] = max(0, int(per_asset_cooldown_seconds))
        if minimum_payout_pct is not None:
            updates["minimum_payout_pct"] = max(0.0, min(100.0, float(minimum_payout_pct)))
        if block_on_manipulation is not None:
            updates["block_on_manipulation"] = bool(block_on_manipulation)
        if manipulation_severity_threshold is not None:
            updates["manipulation_severity_threshold"] = max(0.0, min(1.0, float(manipulation_severity_threshold)))
        if max_session_trades is not None:
            updates["max_session_trades"] = max(1, int(max_session_trades))
        if max_drawdown_amount is not None:
            updates["max_drawdown_amount"] = max(0.0, float(max_drawdown_amount))
        if drawdown_cooldown_seconds is not None:
            updates["drawdown_cooldown_seconds"] = max(0, int(drawdown_cooldown_seconds))
        if min_confidence_enabled is not None:
            updates["min_confidence_enabled"] = bool(min_confidence_enabled)
        if min_confidence is not None:
            updates["min_confidence"] = float(min_confidence)
        if max_confidence_enabled is not None:
            updates["max_confidence_enabled"] = bool(max_confidence_enabled)
        if max_confidence is not None:
            updates["max_confidence"] = float(max_confidence)
        if max_trades_per_timeframe is not None:
            updates["max_trades_per_timeframe"] = max(0, int(max_trades_per_timeframe))
        if timeframe_seconds is not None:
            updates["timeframe_seconds"] = max(0, int(timeframe_seconds))
        if oteo_ai_enabled is not None:
            updates["oteo_ai_enabled"] = bool(oteo_ai_enabled)
        if oteo_ai_execution_mode is not None:
            updates["oteo_ai_execution_mode"] = str(oteo_ai_execution_mode)
        if ai_trade_interval is not None:
            updates["ai_trade_interval"] = max(1, int(ai_trade_interval))
        if ai_pulse_enabled is not None:
            updates["ai_pulse_enabled"] = bool(ai_pulse_enabled)
        if ai_pulse_interval_seconds is not None:
            updates["ai_pulse_interval_seconds"] = max(10, int(ai_pulse_interval_seconds))
        if min_zscore_enabled is not None:
            updates["min_zscore_enabled"] = bool(min_zscore_enabled)
        if min_zscore is not None:
            updates["min_zscore"] = float(min_zscore)
        if max_zscore_enabled is not None:
            updates["max_zscore_enabled"] = bool(max_zscore_enabled)
        if max_zscore is not None:
            updates["max_zscore"] = float(max_zscore)
        if regime_gate_enabled is not None:
            updates["regime_gate_enabled"] = bool(regime_gate_enabled)
        if allowed_regimes is not None:
            updates["allowed_regimes"] = [str(r).strip().upper() for r in allowed_regimes if str(r).strip()]
        if require_regime_stable is not None:
            updates["require_regime_stable"] = bool(require_regime_stable)
        if hurst_filter_enabled is not None:
            updates["hurst_filter_enabled"] = bool(hurst_filter_enabled)
        if hurst_filter_threshold is not None:
            updates["hurst_filter_threshold"] = float(hurst_filter_threshold)
        if hurst_mean_revert_threshold is not None:
            updates["hurst_mean_revert_threshold"] = float(hurst_mean_revert_threshold)
        if hurst_trend_threshold is not None:
            updates["hurst_trend_threshold"] = float(hurst_trend_threshold)
        if min_adaptive_expiry is not None:
            updates["min_adaptive_expiry"] = int(min_adaptive_expiry)
        if hurst_min_scale_cutoff is not None:
            updates["hurst_min_scale_cutoff"] = int(hurst_min_scale_cutoff)
        if hurst_ai_confidence_threshold is not None:
            updates["hurst_ai_confidence_threshold"] = float(hurst_ai_confidence_threshold)
 
        self.config = replace(self.config, **updates)
 
        if self.config.enabled and (not previous_enabled or not self._session_id):
            self._session_id = f"auto_ghost_{int(unix_time())}"
            self._pending_signals.clear()
            self._consecutive_losses.clear()
            self._condition_stats.clear()
            self._session_pnl = 0.0
            self._session_trade_count = 0
            self._session_wins = 0
            self._session_losses = 0
            self._session_halted = False
            self._current_streak_type = None
            self._current_streak_count = 0
            self._max_win_streak = 0
            self._max_loss_streak = 0
            self._last_streak_start_time = unix_time()
            self._avg_recovery_time = 0.0
            self._total_recovery_sessions = 0
            self._trade_timestamps.clear()
            self._last_reject_reason_by_asset.clear()
            self._reject_counts.clear()
            logger.info("Started Auto-Ghost session %s", self._session_id)
        elif not self.config.enabled and previous_enabled:
            self._pending_signals.clear()
        return self.status
 
    @property
    def status(self) -> dict[str, Any]:
        return {
            "auto_ghost_enabled": self.config.enabled,
            "auto_ghost_amount": self.config.amount,
            "auto_ghost_expiration_seconds": self.config.expiration_seconds,
            "auto_ghost_max_concurrent_trades": self.config.max_concurrent_trades,
            "auto_ghost_per_asset_cooldown_seconds": self.config.per_asset_cooldown_seconds,
            "auto_ghost_minimum_payout_pct": self.config.minimum_payout_pct,
            "auto_ghost_manipulation_severity_threshold": self.config.manipulation_severity_threshold,
            "auto_ghost_block_on_manipulation": self.config.block_on_manipulation,
            "auto_ghost_min_confidence_enabled": self.config.min_confidence_enabled,
            "auto_ghost_min_confidence": self.config.min_confidence,
            "auto_ghost_max_confidence_enabled": self.config.max_confidence_enabled,
            "auto_ghost_max_confidence": self.config.max_confidence,
            "auto_ghost_max_trades_per_timeframe": self.config.max_trades_per_timeframe,
            "auto_ghost_timeframe_seconds": self.config.timeframe_seconds,
            "oteo_ai_enabled": self.config.oteo_ai_enabled,
            "oteo_ai_execution_mode": self.config.oteo_ai_execution_mode,
            "ai_trade_interval": self.config.ai_trade_interval,
            "ai_pulse_enabled": self.config.ai_pulse_enabled,
            "ai_pulse_interval_seconds": self.config.ai_pulse_interval_seconds,
            "auto_ghost_min_zscore_enabled": self.config.min_zscore_enabled,
            "auto_ghost_min_zscore": self.config.min_zscore,
            "auto_ghost_max_zscore_enabled": self.config.max_zscore_enabled,
            "auto_ghost_max_zscore": self.config.max_zscore,
            "auto_ghost_regime_gate_enabled": self.config.regime_gate_enabled,
            "auto_ghost_allowed_regimes": self.config.allowed_regimes,
            "auto_ghost_require_regime_stable": self.config.require_regime_stable,
            "auto_ghost_hurst_filter_enabled": self.config.hurst_filter_enabled,
            "auto_ghost_hurst_filter_threshold": self.config.hurst_filter_threshold,
            "auto_ghost_hurst_mean_revert_threshold": self.config.hurst_mean_revert_threshold,
            "auto_ghost_hurst_trend_threshold": self.config.hurst_trend_threshold,
            "auto_ghost_min_adaptive_expiry": self.config.min_adaptive_expiry,
            "auto_ghost_hurst_min_scale_cutoff": self.config.hurst_min_scale_cutoff,
            "auto_ghost_hurst_ai_confidence_threshold": self.config.hurst_ai_confidence_threshold,
            "hasPremiumHurst": any(ext.__class__.__name__ == "HurstAdaptiveExpiry" for ext in self.extension_manager.get_active_extensions()) if getattr(self, "extension_manager", None) is not None else False,
            "hasEliteHurst": any(ext.__class__.__name__ == "HurstAiNoise" for ext in self.extension_manager.get_active_extensions()) if getattr(self, "extension_manager", None) is not None else False,
            "auto_ghost_active_trades": len(self._active_assets),
            "auto_ghost_session_id": self._session_id,
            "auto_ghost_session_pnl": self._session_pnl,
            "auto_ghost_session_trades": self._session_trade_count,
            "auto_ghost_session_wins": self._session_wins,
            "auto_ghost_session_losses": self._session_losses,
            "auto_ghost_current_streak_type": self._current_streak_type,
            "auto_ghost_current_streak_count": self._current_streak_count,
            "auto_ghost_max_win_streak": self._max_win_streak,
            "auto_ghost_max_loss_streak": self._max_loss_streak,
            "auto_ghost_avg_recovery_time_mins": round(self._avg_recovery_time / 60, 2),
            "auto_ghost_drawdown_cooldown_active": unix_time() < self._drawdown_cooldown_until,
            "auto_ghost_session_halted": self._session_halted,
            "auto_ghost_last_reject_reason_by_asset": dict(self._last_reject_reason_by_asset),
            "auto_ghost_reject_counts": dict(self._reject_counts),
        }

    def report_outcome(
        self,
        trade_id: str,
        outcome: str,
        profit: float,
        *,
        asset: str | None = None,
        entry_context: dict[str, Any] | None = None,
    ) -> None:
        self._session_trade_count += 1
        self._session_pnl += profit
        now = unix_time()

        if outcome == "win":
            self._session_wins += 1
        elif outcome == "loss":
            self._session_losses += 1

        # Streak Tracking
        if outcome in {"win", "loss"}:
            if outcome == self._current_streak_type:
                self._current_streak_count += 1
            else:
                # Previous streak ended - handle recovery time if it was a loss streak
                if self._current_streak_type == "loss":
                    duration = now - self._last_streak_start_time
                    self._total_recovery_sessions += 1
                    # Simple moving average for recovery time
                    self._avg_recovery_time = (
                        (self._avg_recovery_time * (self._total_recovery_sessions - 1) + duration)
                        / self._total_recovery_sessions
                    )

                self._current_streak_type = outcome
                self._current_streak_count = 1
                self._last_streak_start_time = now

            # Update records
            if outcome == "win":
                self._max_win_streak = max(self._max_win_streak, self._current_streak_count)
            else:
                self._max_loss_streak = max(self._max_loss_streak, self._current_streak_count)

        if self.config.max_drawdown_amount > 0 and self._session_pnl <= -abs(self.config.max_drawdown_amount):
            self._drawdown_cooldown_until = unix_time() + self.config.drawdown_cooldown_seconds
            logger.warning("Ghost session drawdown limit hit (%.2f <= -%.2f). Cooling down for %ds.",
                           self._session_pnl, self.config.max_drawdown_amount, self.config.drawdown_cooldown_seconds)

        if asset:
            if outcome == "loss":
                loss_count = self._consecutive_losses.get(asset, 0) + 1
                self._consecutive_losses[asset] = loss_count
                extended_cooldown = self.config.per_asset_cooldown_seconds * (3 if loss_count >= 3 else 2)
                self._cooldown_until[asset] = max(
                    self._cooldown_until.get(asset, 0.0),
                    now + extended_cooldown,
                )
                if loss_count >= 3:
                    logger.warning(
                        "Triple cooldown for %s after %d consecutive losses (%ds)",
                        asset,
                        loss_count,
                        extended_cooldown,
                    )
                else:
                    logger.info(
                        "Extended cooldown for %s after loss (%ds)",
                        asset,
                        extended_cooldown,
                    )
            elif outcome == "win":
                self._consecutive_losses.pop(asset, None)

        if entry_context and outcome in {"win", "loss"}:
            is_win = outcome == "win"
            market_context = entry_context.get("market_context") or {}
            regime_label = entry_context.get("regime_label", "unknown")
            adx_regime = market_context.get("adx_regime") or "unknown"
            cci_state = market_context.get("cci_state") or "unknown"
            tick_health = market_context.get("tick_health") or "unknown"

            self._update_condition_stat(f"regime:{regime_label}", is_win)
            self._update_condition_stat(f"adx:{adx_regime}", is_win)
            self._update_condition_stat(f"cci:{cci_state}", is_win)
            self._update_condition_stat(f"tick_health:{tick_health}", is_win)
            if asset:
                self._update_condition_stat(f"asset:{asset}", is_win)

        if self.config.oteo_ai_enabled and self.config.ai_trade_interval > 0:
            if self._session_trade_count > 0 and self._session_trade_count % self.config.ai_trade_interval == 0:
                logger.info("Trade count interval reached (%d trades). Triggering AI Suggestions in background.", self._session_trade_count)
                asyncio.create_task(self._run_trade_count_suggestions())

    def _reject(self, asset: str, reason: str) -> None:
        self._record_reject(asset, reason)
        self._pending_signals.pop(asset, None)

    async def consider_signal(
        self,
        *,
        asset: str,
        price: float,
        timestamp: float,
        oteo_result: dict[str, Any],
        manipulation: dict[str, Any],
        payout_pct: float | None = 100.0,
    ) -> dict[str, Any] | None:
        # Defensive fallback: clean up active assets whose cooldowns have fully elapsed
        now = unix_time()
        for a in [a for a in self._active_assets if now >= self._cooldown_until.get(a, 0)]:
            self._active_assets.discard(a)

        if not self.config.enabled:
            return self._reject(asset, 'disabled')
            
        if self._session_halted:
            return self._reject(asset, 'session_halted')
        if self._session_trade_count >= self.config.max_session_trades:
            return self._reject(asset, 'max_session_trades')
        if now < self._drawdown_cooldown_until:
            return self._reject(asset, 'drawdown_cooldown')

        # Timeframe limit gate check
        if self.config.max_trades_per_timeframe > 0 and self.config.timeframe_seconds > 0:
            self._trade_timestamps = [t for t in self._trade_timestamps if timestamp - t < self.config.timeframe_seconds]
            if len(self._trade_timestamps) >= self.config.max_trades_per_timeframe:
                logger.info(
                    "Auto-Ghost skipped %s: timeframe limit reached (%d trades in last %ds, limit: %d)",
                    asset,
                    len(self._trade_timestamps),
                    self.config.timeframe_seconds,
                    self.config.max_trades_per_timeframe
                )
                return self._reject(asset, 'timeframe_limit')

        if oteo_result.get("recommended") not in {"CALL", "PUT"}:
            return self._reject(asset, 'not_call_or_put')
        if not oteo_result.get("actionable"):
            return self._reject(asset, 'not_actionable')

        # Numeric confidence gate bounds checks
        score = float(oteo_result.get("oteo_score", 0.0))
        if self.config.min_confidence_enabled and self.config.min_confidence is not None:
            if score < self.config.min_confidence:
                logger.info(
                    "Auto-Ghost skipped %s: score %.1f < min confidence bounds %.1f",
                    asset,
                    score,
                    self.config.min_confidence
                )
                return self._reject(asset, 'below_min_confidence')
        if self.config.max_confidence_enabled and self.config.max_confidence is not None:
            if score > self.config.max_confidence:
                logger.info(
                    "Auto-Ghost skipped %s: score %.1f > max confidence bounds %.1f",
                    asset,
                    score,
                    self.config.max_confidence
                )
                return self._reject(asset, 'above_max_confidence')
        if payout_pct is None:
            logger.warning(f"Auto-Ghost skipped {asset}: payout unavailable")
            return self._reject(asset, 'payout_unavailable')
        if self.config.minimum_payout_pct > 0 and payout_pct < self.config.minimum_payout_pct:
            logger.info(
                "Auto-Ghost skipped %s: payout %.1f%% < minimum %.1f%%",
                asset,
                payout_pct,
                self.config.minimum_payout_pct,
            )
            return self._reject(asset, 'payout_below_minimum')
        if self.config.block_on_manipulation and manipulation:
            if any(_get_severity(sev_val) >= self.config.manipulation_severity_threshold for sev_val in manipulation.values()):
                logger.info(
                    "Auto-Ghost skipped %s due to active manipulation severity: %s (threshold: %.2f)",
                    asset,
                    manipulation,
                    self.config.manipulation_severity_threshold
                )
                return self._reject(asset, 'manipulation_block')

        # Z-Score Gate Bounds checks (Ghost Protocol)
        z_score = oteo_result.get("z_score")
        if z_score is not None:
            try:
                z_val = float(z_score)
                if self.config.min_zscore_enabled and self.config.min_zscore is not None:
                    if z_val < self.config.min_zscore:
                        logger.info(
                            "Auto-Ghost skipped %s: z-score %.2f < min gate %.2f (Ghost Protocol gate)",
                            asset,
                            z_val,
                            self.config.min_zscore,
                        )
                        return self._reject(asset, 'below_min_zscore')
                if self.config.max_zscore_enabled and self.config.max_zscore is not None:
                    if z_val > self.config.max_zscore:
                        logger.info(
                            "Auto-Ghost skipped %s: z-score %.2f > max gate %.2f (Ghost Protocol gate)",
                            asset,
                            z_val,
                            self.config.max_zscore,
                        )
                        return self._reject(asset, 'above_max_zscore')
            except (ValueError, TypeError) as exc:
                logger.warning("Auto-Ghost: non-numeric z_score %r for %s, skipping Z gates: %s", z_score, asset, exc)

        # Regime Gate checks (Ghost Protocol)
        regime_label = oteo_result.get("regime_label")
        regime_stable = oteo_result.get("regime_stable")
        if self.config.regime_gate_enabled and self.config.allowed_regimes:
            if regime_label is None:
                logger.info(f"Auto-Ghost skipped {asset}: regime gate enabled but signal has no regime label")
                return self._reject(asset, 'missing_regime_label')
            if str(regime_label).upper() not in self.config.allowed_regimes:
                logger.info(f"Auto-Ghost skipped {asset}: regime {regime_label} not in allowed {self.config.allowed_regimes} (Ghost Protocol gate)")
                return self._reject(asset, 'regime_not_allowed')

        if self.config.regime_gate_enabled and self.config.require_regime_stable and regime_stable is False:
            logger.info(f"Auto-Ghost skipped {asset}: regime {regime_label} is unstable (Ghost Protocol gate)")
            return self._reject(asset, 'regime_unstable')

        # Hurst Exponent Gate check (L1 Core)
        hurst = oteo_result.get("market_context", {}).get("hurst") if isinstance(oteo_result.get("market_context"), dict) else oteo_result.get("hurst")
        if hurst is None:
            # Fallback to direct payload key if market_context nesting is skipped
            hurst = oteo_result.get("hurst")
            
        if self.config.hurst_filter_enabled and hurst is not None:
            if hurst >= self.config.hurst_filter_threshold:
                logger.info(
                    "Auto-Ghost skipped %s: hurst exponent %.3f >= threshold %.3f (L1 Hurst Gate)",
                    asset,
                    hurst,
                    self.config.hurst_filter_threshold,
                )
                return self._reject(asset, 'hurst_filter')
        # Plugin veto check
        if getattr(self, "extension_manager", None) is not None:
            for ext in self.extension_manager.get_active_extensions():
                try:
                    allow, reason = ext.on_consider_signal(asset, price, oteo_result, self.config)
                    if not allow:
                        logger.info(
                            "Auto-Ghost skipped %s: vetoed by extension %s (reason: %s)",
                            asset,
                            ext.__class__.__name__,
                            reason or "No reason given",
                        )
                        return self._reject(asset, f"plugin_veto_{reason or 'unknown'}")
                except Exception as ext_err:
                    logger.error("Error in extension %s.on_consider_signal: %s", ext.__class__.__name__, ext_err)

        if asset in self._active_assets:
            return self._reject(asset, 'asset_active')
        if len(self._active_assets) >= self.config.max_concurrent_trades:
            return self._reject(asset, 'max_concurrent_trades')
        if unix_time() < self._cooldown_until.get(asset, 0):
            return self._reject(asset, 'asset_cooldown')

        # Confirmation Gate (primarily for Phase 3 backward-compatibility tests)
        # Bypassed in production since CONFIRMATION_TICKS = 1 by default
        if self.CONFIRMATION_TICKS > 1:
            direction = str(oteo_result.get("recommended"))
            pending = self._pending_signals.get(asset)
            if pending is None:
                self._pending_signals[asset] = (dict(oteo_result), 1)
                return None

            pending_signal, pending_count = pending
            if pending_signal.get("recommended") != direction:
                return self._reject(asset, 'confirmation_direction_changed')

            pending_count += 1
            if pending_count < self.CONFIRMATION_TICKS:
                self._pending_signals[asset] = (dict(oteo_result), pending_count)
                return None

            self._pending_signals.pop(asset, None)

        # AI Advisory Gate (Advisory only - Confirmation mode is deprecated)
        if self.config.oteo_ai_enabled:
            strategy_level = "level3" if oteo_result.get("level3_enabled") else "level2" if oteo_result.get("level2_enabled") else "level1"
            # Advisory mode: Query in background without blocking execution
            asyncio.create_task(
                self._run_ai_advisory(
                    asset=asset,
                    direction=oteo_result.get("recommended"),
                    oteo_score=score,
                    market_context=oteo_result.get("market_context") or {},
                    manipulation=manipulation,
                    strategy_level=strategy_level,
                )
            )

        entry_context = {
            "asset": asset,
            "price": price,
            "timestamp": timestamp,
            "recommended": oteo_result.get("recommended"),
            "confidence": oteo_result.get("confidence"),
            "oteo_score": oteo_result.get("oteo_score"),
            "base_oteo_score": oteo_result.get("base_oteo_score"),
            "base_confidence": oteo_result.get("base_confidence"),
            "pressure_pct": oteo_result.get("pressure_pct"),
            "velocity": oteo_result.get("velocity"),
            "z_score": oteo_result.get("z_score"),
            "slow_velocity": oteo_result.get("slow_velocity"),
            "stretch_alignment": oteo_result.get("stretch_alignment"),
            "level2_enabled": oteo_result.get("level2_enabled"),
            "level2_score_adjustment": oteo_result.get("level2_score_adjustment"),
            "level2_suppressed_reason": oteo_result.get("level2_suppressed_reason"),
            "level3_enabled": oteo_result.get("level3_enabled"),
            "level3_score_adjustment": oteo_result.get("level3_score_adjustment"),
            "level3_suppressed_reason": oteo_result.get("level3_suppressed_reason"),
            "oteo_ai_enabled": oteo_result.get("oteo_ai_enabled"),
            "regime_label": oteo_result.get("regime_label"),
            "regime_confidence": oteo_result.get("regime_confidence"),
            "regime_stable": oteo_result.get("regime_stable"),
            "regime_detail": oteo_result.get("regime_detail"),
            "market_context": oteo_result.get("market_context"),
            "hurst": hurst,
            "manipulation": manipulation,
            "payout_pct": payout_pct,
        }

        request = TradeExecutionRequest(
            asset_id=asset,
            direction=str(oteo_result["recommended"]).lower(),
            amount=self.config.amount,
            expiration=oteo_result.get("override_expiration_seconds") or self.config.expiration_seconds,
            account_key="primary",
            trade_mode="ghost",
            session_id=self._session_id,
            confidence=oteo_result.get("confidence"),
            oteo_score=oteo_result.get("oteo_score"),
            base_oteo_score=oteo_result.get("base_oteo_score"),
            level2_score_adjustment=oteo_result.get("level2_score_adjustment"),
            strategy_level="level3" if oteo_result.get("level3_enabled") else "level2" if oteo_result.get("level2_enabled") else "level1",
            manipulation_at_entry=manipulation or None,
            entry_context=entry_context,
            trigger_mode="auto_ghost",
        )

        result = await self.trade_service.execute_trade(BrokerType.POCKET_OPTION, request)
        if not result.get("success"):
            logger.warning("Auto-Ghost failed for %s: %s", asset, result.get("message"))
            return result

        # Record trade execution timestamp for timeframe gating
        self._trade_timestamps.append(timestamp)

        self._active_assets.add(asset)
        self._cooldown_until[asset] = unix_time() + self.config.expiration_seconds + self.config.per_asset_cooldown_seconds
        task = asyncio.create_task(self._release_asset(asset, self.config.expiration_seconds + 1))
        task.add_done_callback(lambda t: logger.error("_release_asset failed: %s", t.exception()) if not t.cancelled() and t.exception() else None)
        logger.info(
            "Auto-Ghost trade opened for %s (%s, %ss)",
            asset,
            oteo_result.get("recommended"),
            self.config.expiration_seconds,
        )
        return result

    async def _release_asset(self, asset: str, delay_seconds: int) -> None:
        await asyncio.sleep(max(1, delay_seconds))
        self._active_assets.discard(asset)

    def _update_condition_stat(self, key: str, is_win: bool) -> None:
        stats = self._condition_stats.setdefault(key, {"wins": 0, "losses": 0})
        if is_win:
            stats["wins"] += 1
        else:
            stats["losses"] += 1

    def get_condition_stats(self) -> dict[str, dict[str, float | int]]:
        result: dict[str, dict[str, float | int]] = {}
        for key, stats in self._condition_stats.items():
            wins = int(stats.get("wins", 0))
            losses = int(stats.get("losses", 0))
            total = wins + losses
            result[key] = {
                "wins": wins,
                "losses": losses,
                "total": total,
                "win_rate": round((wins / total) * 100.0, 1) if total > 0 else 0.0,
            }
        return result

    async def _query_ai_confirmation(
        self,
        *,
        asset: str,
        direction: str,
        oteo_score: float,
        market_context: dict[str, Any],
        manipulation: dict[str, Any],
        strategy_level: str = "level1",
    ) -> tuple[bool, str]:
        """Query the AI provider for a binary trade confirmation (CONFIRM or REJECT)."""
        from .ai_service import get_ai_service
        from ..models.ai_models import AIChatRequest, AIMessage, AIContext
        from .ai_review import KnowledgeBaseLoader, format_patterns_for_prompt, _MANIPULATION_TAXONOMY

        ai_service = get_ai_service()
        if not ai_service.status().enabled:
            logger.warning("AI Service is disabled. Auto-confirming trade setup.")
            return True, "AI_DISABLED"

        # L3 regime fields (take priority over legacy adx_regime)
        regime_label = market_context.get("regime_label") or market_context.get("adx_regime", "unknown")
        regime_confidence = market_context.get("regime_confidence", 0)
        regime_stable = market_context.get("regime_stable", False)
        trend = market_context.get("trend_direction", "unknown")
        adx = market_context.get("adx", "unknown")
        cci = market_context.get("cci", "unknown")
        cci_state = market_context.get("cci_state", "unknown")
        tick_health = market_context.get("tick_health", "unknown")
        nearest_structure_atr = market_context.get("nearest_structure_atr", "N/A")

        # Retrieve top matching historical patterns from KB
        kb_loader = KnowledgeBaseLoader.get_instance()
        matched_patterns = kb_loader.query_top_patterns(
            asset=asset,
            strategy_level=strategy_level,
            oteo_score=oteo_score,
            regime_label=regime_label,
            direction=direction,
        )
        patterns_context = format_patterns_for_prompt(matched_patterns)

        # Format active manipulation flags cleanly
        active_manip = (
            ", ".join(f"{k} (severity: {_get_severity(v):.2f})" for k, v in manipulation.items())
            if manipulation
            else "None"
        )

        system_msg = (
            "You are an expert AI trading confirmation assistant. You review market data snapshots "
            "for short-expiry OTC binary options setups and confirm or reject them.\n\n"
            f"{_MANIPULATION_TAXONOMY}\n\n"
            "Regime context: RANGE_BOUND=ideal for reversals, TREND_REVERSAL=good for reversals, "
            "TREND_PULLBACK=conditional (trend-aligned only), STRONG_MOMENTUM/BREAKOUT/CHOPPY=dangerous for reversals.\n"
            "Answer with EXACTLY 'CONFIRM' or 'REJECT' (no other text, explanation, or punctuation)."
        )

        user_msg = (
            f"Trade Setup to Verify:\n"
            f"Asset: {asset}\n"
            f"Direction: {direction}\n"
            f"OTEO Score: {oteo_score}\n"
            f"Strategy Level: {strategy_level.upper()}\n"
            f"Regime: {regime_label} (confidence: {regime_confidence}%, stable: {regime_stable})\n"
            f"Trend Direction: {trend}\n"
            f"ADX: {adx}\n"
            f"CCI: {cci} ({cci_state})\n"
            f"Nearest S/R: {nearest_structure_atr} ATR\n"
            f"Tick Health: {tick_health}\n"
            f"Active Manipulation: {active_manip}\n\n"
            f"Historical Context (Top Matching KB Patterns):\n"
            f"{patterns_context}\n\n"
            f"Should we execute this trade? Respond with CONFIRM or REJECT."
        )

        chat_req = AIChatRequest(
            messages=[
                AIMessage(role="system", content=system_msg),
                AIMessage(role="user", content=user_msg),
            ],
            model=ai_service.settings.ai_model,
            context=AIContext(
                asset=asset,
                session_pnl=self._session_pnl,
                win_rate=self._session_wins / max(1, self._session_trade_count) * 100.0,
                total_trades=self._session_trade_count,
            )
        )

        try:
            res = await asyncio.wait_for(ai_service.chat(chat_req), timeout=4.0)
            res_text = res.text.strip().upper()
            
            logger.info("AI confirmation response for %s: %s", asset, res_text)
            
            if "CONFIRM" in res_text:
                return True, res_text
            elif "REJECT" in res_text:
                return False, res_text
            else:
                if "YES" in res_text or "ALLOW" in res_text:
                    return True, res_text
                return False, f"AMBIGUOUS_RESPONSE: {res_text}"
        except asyncio.TimeoutError:
            logger.error("AI confirmation request timed out (4s limit) for %s", asset)
            raise RuntimeError("AI confirmation timeout")
        except Exception as e:
            logger.error("AI confirmation request failed for %s: %s", asset, e)
            raise e

    async def _run_ai_advisory(
        self,
        *,
        asset: str,
        direction: str,
        oteo_score: float,
        market_context: dict[str, Any],
        manipulation: dict[str, Any],
        strategy_level: str = "level1",
    ) -> None:
        """Query the AI provider in the background for advisory analysis and emit notification."""
        try:
            confirmed, response = await self._query_ai_confirmation(
                asset=asset,
                direction=direction,
                oteo_score=oteo_score,
                market_context=market_context,
                manipulation=manipulation,
                strategy_level=strategy_level,
            )
            
            # Query top pattern for the advisory socket notification
            from .ai_review import KnowledgeBaseLoader
            kb_loader = KnowledgeBaseLoader.get_instance()
            regime_label = market_context.get("regime_label") or market_context.get("adx_regime", "unknown")
            matched_patterns = kb_loader.query_top_patterns(
                asset=asset,
                strategy_level=strategy_level,
                oteo_score=oteo_score,
                regime_label=regime_label,
                direction=direction,
            )
            top_pattern_str = "No KB Match"
            if matched_patterns:
                top_p = matched_patterns[0]
                top_pattern_str = f"KB Match: WR={top_p.get('win_rate_pct', 0.0):.1f}%, N={top_p.get('sample_size', 0)}"

            msg = f"[AI Advisor] Trade Setup {direction} on {asset} reviewed. Decision: {response}. ({top_pattern_str})"
            if self.trade_service.sio:
                await self.trade_service.sio.emit("notification", {
                    "type": "info" if confirmed else "warning",
                    "message": msg,
                    "timestamp": unix_time(),
                })
            logger.info("AI Advisory completed for %s: %s (%s)", asset, response, top_pattern_str)
        except Exception as e:
            logger.warning(f"AI Advisory background query failed for {asset}: {e}")

    async def _run_trade_count_suggestions(self) -> None:
        """Query AI for controller gates optimization suggestions based on session statistics."""
        try:
            from .ai_service import get_ai_service
            from ..models.ai_models import AIChatRequest, AIMessage, AIContext

            ai_service = get_ai_service()
            if not ai_service.status().enabled:
                return

            condition_stats = self.get_condition_stats()
            # Format condition stats for prompt
            stats_str = ""
            for key, stat in condition_stats.items():
                stats_str += f"- {key}: Wins={stat['wins']}, Losses={stat['losses']}, WinRate={stat['win_rate']}%\n"
            if not stats_str:
                stats_str = "No trades recorded for specific conditions yet."

            allowed_regimes = self.config.allowed_regimes or []
            min_z = self.config.min_zscore if self.config.min_zscore_enabled else "Disabled"
            max_z = self.config.max_zscore if self.config.max_zscore_enabled else "Disabled"
            manip_threshold = self.config.manipulation_severity_threshold if self.config.block_on_manipulation else "Disabled"

            system_msg = (
                "You are an expert algorithmic trading advisor for the OTC SNIPER Auto-Ghost system. "
                "You review session statistics and recommend optimization tweaks to the Ghost Controller gate settings "
                "or suggest which assets to focus on or avoid. "
                "Provide a constructive, highly actionable suggestion (maximum 80 words)."
            )

            user_msg = (
                f"Active Controller Gates:\n"
                f"- Allowed Regimes: {allowed_regimes}\n"
                f"- Min Z-Score: {min_z}\n"
                f"- Max Z-Score: {max_z}\n"
                f"- Block on Manipulation: {self.config.block_on_manipulation} (Threshold: {manip_threshold})\n\n"
                f"Session Performance:\n"
                f"- Total Trades: {self._session_trade_count}\n"
                f"- Wins: {self._session_wins}, Losses: {self._session_losses} (Win Rate: {self._session_wins / max(1, self._session_trade_count) * 100.0:.1f}%)\n"
                f"- PnL: ${self._session_pnl:.2f}\n\n"
                f"Performance by Condition:\n"
                f"{stats_str}\n\n"
                f"Based on the data above, recommend specific tweaks to win rates (e.g. tightening Z-Score bounds, adjusting whitelisted regimes) or specify assets/regimes to avoid/focus on."
            )

            chat_req = AIChatRequest(
                messages=[
                    AIMessage(role="system", content=system_msg),
                    AIMessage(role="user", content=user_msg),
                ],
                model=ai_service.settings.ai_model,
                context=AIContext(
                    session_pnl=self._session_pnl,
                    win_rate=self._session_wins / max(1, self._session_trade_count) * 100.0,
                    total_trades=self._session_trade_count,
                )
            )

            res = await ai_service.chat(chat_req)
            ai_suggestion = res.text.strip()

            logger.info("AI Trade Count Suggestion generated: %s", ai_suggestion)

            if self.trade_service.sio:
                await self.trade_service.sio.emit("notification", {
                    "type": "ai_advisory",
                    "message": ai_suggestion,
                    "timestamp": unix_time(),
                })
        except Exception as e:
            logger.warning(f"AI Trade Count Suggestion background query failed: {e}")
