from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, fields, replace
from time import time as unix_time
from typing import Any, Callable

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


def _extract_market_context_field(oteo_result: dict[str, Any], field: str) -> Any:
    """Safely extract a field from nested market_context or top-level oteo_result."""
    mc = oteo_result.get("market_context")
    if isinstance(mc, dict) and field in mc and mc[field] is not None:
        return mc[field]
    return oteo_result.get(field)


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
    auto_execute_ai_pulse: bool = False
    min_zscore_enabled: bool = False
    min_zscore: float | None = None
    max_zscore_enabled: bool = False
    max_zscore: float | None = None
    regime_gate_enabled: bool = False
    allowed_regimes: list[str] | None = None
    require_regime_stable: bool = False
    adaptive_expiry_enabled: bool = True
    min_adaptive_expiry: int = 60
    blacklist_assets: list[str] | None = None
    rsi_cci_enabled: bool = False
    volatility_gate_enabled: bool = False
    min_volatility: float = 0.0
    max_volatility: float = 100.0
    liquidity_gate_enabled: bool = False
    min_liquidity: float = 0.0
    max_liquidity: float = 100.0
    adx_gate_enabled: bool = False
    cci_gate_enabled: bool = False
    bayesian_filter_enabled: bool = False
    bayesian_min_probability: float = 0.535
    # Calibration Mode (Plan 26-08-26): "standard" | "calibration". Owned by
    # CalibrationService via set_calibration_mode() — NOT exposed in the spec
    # table, so it is never API/model-writable.
    mode: str = "standard"

    def __post_init__(self):
        pass



# H3 rewrite: declarative configuration specification tables (replace ~90 repeated
# if-not-None blocks in AutoGhostService.update_config).
#
# _AUTO_GHOST_FIELD_SPECS: config_field -> (caster, lower_bound, upper_bound).
# Bounds are applied after casting (max(lo, v) then min(hi, v)); None disables a bound.
# Values mirror the exact semantics of the previous hand-written cascade.
_AUTO_GHOST_FIELD_SPECS: dict[str, tuple] = {
    "enabled": (bool, None, None),
    "amount": (float, 0.1, None),
    "expiration_seconds": (int, 5, None),
    "max_concurrent_trades": (int, 1, None),
    "per_asset_cooldown_seconds": (int, 0, None),
    "minimum_payout_pct": (float, 0.0, 100.0),
    "block_on_manipulation": (bool, None, None),
    "manipulation_severity_threshold": (float, 0.0, 1.0),
    "max_session_trades": (int, 1, None),
    "max_drawdown_amount": (float, 0.0, None),
    "drawdown_cooldown_seconds": (int, 0, None),
    "min_confidence_enabled": (bool, None, None),
    "min_confidence": (float, None, None),
    "max_confidence_enabled": (bool, None, None),
    "max_confidence": (float, None, None),
    "max_trades_per_timeframe": (int, 0, None),
    "timeframe_seconds": (int, 0, None),
    "oteo_ai_enabled": (bool, None, None),
    "oteo_ai_execution_mode": (str, None, None),
    "ai_trade_interval": (int, 1, None),
    "ai_pulse_enabled": (bool, None, None),
    "ai_pulse_interval_seconds": (int, 10, None),
    "auto_execute_ai_pulse": (bool, None, None),
    "min_zscore_enabled": (bool, None, None),
    "min_zscore": (float, None, None),
    "max_zscore_enabled": (bool, None, None),
    "max_zscore": (float, None, None),
    "regime_gate_enabled": (bool, None, None),
    "require_regime_stable": (bool, None, None),
    "adaptive_expiry_enabled": (bool, None, None),
    "min_adaptive_expiry": (int, None, None),
    "rsi_cci_enabled": (bool, None, None),
    "volatility_gate_enabled": (bool, None, None),
    "min_volatility": (float, None, None),
    "max_volatility": (float, None, None),
    "liquidity_gate_enabled": (bool, None, None),
    "min_liquidity": (float, None, None),
    "max_liquidity": (float, None, None),
    "adx_gate_enabled": (bool, None, None),
    "cci_gate_enabled": (bool, None, None),
    "bayesian_filter_enabled": (bool, None, None),
    # P0-8 (REV1 M6): clamped to the same bounds as the API path (strategy.py
    # ge=0.50, le=0.90). Prevents a model emitting percent-form 53.5 via the
    # direct update_config path from setting an impossible win-probability floor.
    "bayesian_min_probability": (float, 0.50, 0.90),
}

# List-valued config fields with per-item normalization (order-preserving).
_AUTO_GHOST_LIST_CASTERS: dict[str, Any] = {
    "allowed_regimes": lambda items: [
        str(r).strip().upper() for r in items if str(r).strip()
    ],
    "blacklist_assets": lambda items: [
        str(a).strip() for a in items if str(a).strip()
    ],
}

# Legacy fields accepted for backward API compatibility but owned/managed by the
# plugin extensions (never written into AutoGhostConfig by update_config).
_PLUGIN_MANAGED_CONFIG_FIELDS = frozenset({
    "hurst_filter_enabled",
    "hurst_filter_threshold",
    "hurst_mean_revert_threshold",
    "hurst_trend_threshold",
    "hurst_min_scale_cutoff",
    "hurst_ai_confidence_threshold",
    "hurst_l2_enabled",
    "hurst_l3_enabled",
})

# Phase 3 — Calibration Mode tiered autonomy (Plan 26-08-26 REV2).
# Locked internals live on CalibrationService.CALIBRATION_LOCKED_FIELDS.
CALIBRATION_TIER_A_FIELDS = frozenset({
    "min_zscore_enabled",
    "min_zscore",
    "max_zscore_enabled",
    "max_zscore",
    "volatility_gate_enabled",
    "min_volatility",
    "max_volatility",
    "liquidity_gate_enabled",
    "min_liquidity",
    "max_liquidity",
    "min_confidence_enabled",
    "min_confidence",
    "max_confidence_enabled",
    "max_confidence",
    "regime_gate_enabled",
    "allowed_regimes",
    "manipulation_severity_threshold",
    "per_asset_cooldown_seconds",
    "bayesian_filter_enabled",
    "bayesian_min_probability",
})

CALIBRATION_TIER_B_FIELDS = frozenset({
    "amount",
    "max_concurrent_trades",
    "max_drawdown_amount",
    "expiration_seconds",
    "enabled",
})

CALIBRATION_GATE_FAMILIES: dict[str, frozenset[str]] = {
    "zscore": frozenset({"min_zscore_enabled", "min_zscore", "max_zscore_enabled", "max_zscore"}),
    "volatility": frozenset({"volatility_gate_enabled", "min_volatility", "max_volatility"}),
    "liquidity": frozenset({"liquidity_gate_enabled", "min_liquidity", "max_liquidity"}),
    "confidence": frozenset({
        "min_confidence_enabled", "min_confidence", "max_confidence_enabled", "max_confidence",
    }),
    "regimes": frozenset({"regime_gate_enabled", "allowed_regimes"}),
    "manipulation": frozenset({"manipulation_severity_threshold"}),
    "cooldown": frozenset({"per_asset_cooldown_seconds"}),
    "bayesian": frozenset({"bayesian_filter_enabled", "bayesian_min_probability"}),
}


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
        self._session_trades: deque[dict[str, Any]] = deque(maxlen=200)
        # Phase 1 (Calibration Mode): entry veto callback + settlement observers.
        # Both are owned by CalibrationService wiring — never API-writable.
        self._entry_veto_check: Callable[[], str | None] | None = None
        self._outcome_observers: list[Callable[..., None]] = []
        # H2 drain signal: settlements not yet emitted. Independent of
        # `_active_assets` (capacity), which `_release_asset` can clear first.
        self._in_flight_settlements: int = 0

    def _record_reject(self, asset: str, reason: str) -> None:
        self._last_reject_reason_by_asset[asset] = reason
        self._reject_counts[reason] = self._reject_counts.get(reason, 0) + 1

    def update_config(self, **kwargs: Any) -> dict[str, Any]:
        """
        Update controller configuration via the declarative field-spec table (H3).

        Explicit None means "no change" — semantics preserved from the previous
        explicit-signature API. Unknown fields are logged and ignored; plugin-managed
        ``hurst_*`` fields are accepted for backward compatibility but are extension-
        owned and never written into AutoGhostConfig here.
        """
        previous_enabled = self.config.enabled
        # H3 rewrite: declarative spec-table update (was ~90 repeated if-blocks).
        # Explicit None still means "no change"; cast+bound semantics preserved per
        # `_AUTO_GHOST_FIELD_SPECS`; plugin-managed hurst_* fields are accepted but
        # never written here (extension-owned).
        updates: dict[str, Any] = {}
        for _name, _value in kwargs.items():
            if _value is None:
                continue
            if _name in _AUTO_GHOST_LIST_CASTERS:
                updates[_name] = _AUTO_GHOST_LIST_CASTERS[_name](_value)
            elif _name in _AUTO_GHOST_FIELD_SPECS:
                _caster, _lo, _hi = _AUTO_GHOST_FIELD_SPECS[_name]
                _casted = _caster(_value)
                if _lo is not None:
                    _casted = max(_lo, _casted)
                if _hi is not None:
                    _casted = min(_hi, _casted)
                updates[_name] = _casted
            elif _name in _PLUGIN_MANAGED_CONFIG_FIELDS:
                logger.debug("update_config: %s is plugin-managed; ignoring", _name)
            else:
                logger.warning("update_config: ignoring unknown config field %r", _name)

        self.config = replace(self.config, **updates)
        self._sync_extension_states()

        if self.config.enabled and (not previous_enabled or not self._session_id):
            self._reset_session()
            logger.info("Started Auto-Ghost session %s", self._session_id)
        elif not self.config.enabled and previous_enabled:
            self._pending_signals.clear()
        return self.status

    def restore_config_snapshot(self, snapshot: dict[str, Any]) -> None:
        """D4: force-apply a full config snapshot, including None values.

        ``update_config`` treats None as "no change", which would leave
        calibration-preset bounds (e.g. min_zscore=-2.5) stuck after DONE.
        This path is CalibrationService-owned, not API-writable.
        """
        allowed = {f.name for f in fields(self.config) if f.name != "mode"}
        kwargs = {k: v for k, v in snapshot.items() if k in allowed}
        self.config = replace(self.config, **kwargs)
        self._sync_extension_states()

    def note_in_flight_settlement(self) -> None:
        """Increment the H2 drain counter when a ghost trade starts tracking."""
        self._in_flight_settlements += 1

    def release_in_flight_settlement(self) -> None:
        """Decrement after emit + report_outcome (or tracking failure)."""
        if self._in_flight_settlements <= 0:
            logger.warning("release_in_flight_settlement called with counter already 0")
            self._in_flight_settlements = 0
            return
        self._in_flight_settlements -= 1

    def _reset_session(self, session_id: str | None = None) -> None:
        """Reset ghost session counters and mint a session id.

        M1/M9: calibration runs mint `auto_ghost_calib_{epoch}` so milestone and
        journal analytics stay isolated from live ghost history.
        """
        if self.config.mode == "calibration":
            self._session_id = session_id or f"auto_ghost_calib_{int(unix_time())}"
        else:
            self._session_id = session_id or f"auto_ghost_{int(unix_time())}"
        self._pending_signals.clear()
        self._consecutive_losses.clear()
        self._condition_stats.clear()
        self._session_pnl = 0.0
        self._session_trades = deque(maxlen=200)
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

    def set_calibration_mode(self, active: bool, session_id: str | None = None) -> None:
        """Enter/exit calibration mode (owned by CalibrationService — not API-writable).

        Entering mints the dedicated `auto_ghost_calib_{epoch}` session explicitly
        (bypassing update_config's enabled-transition reset condition).
        Exiting re-mints a standard session id (only meaningful when enabled).
        """
        new_mode = "calibration" if active else "standard"
        if self.config.mode == new_mode and not session_id:
            return
        self.config = replace(self.config, mode=new_mode)
        if active:
            self._reset_session(session_id=session_id)
            logger.info("Calibration mode ENTERED (session %s)", self._session_id)
        else:
            # Always re-mint a standard session id on exit — the D4 restore may
            # have set enabled=False, but a stale calib_* id must never survive
            # into post-calibration sessions (M1/M9 isolation contract).
            self._reset_session()
            logger.info("Calibration mode EXITED")

    def set_entry_veto_check(self, veto: Callable[[], str | None] | None) -> None:
        """Register the entry-veto callback (Phase 1 M10 freeze / calibration gates)."""
        self._entry_veto_check = veto

    def add_outcome_observer(self, callback: Callable[..., None]) -> None:
        """Register a settlement observer (invoked from report_outcome, sync context)."""
        if callback not in self._outcome_observers:
            self._outcome_observers.append(callback)

    def remove_outcome_observer(self, callback: Callable[..., None]) -> None:
        self._outcome_observers = [cb for cb in self._outcome_observers if cb is not callback]

    def _notify_outcome_observers(self, **kwargs: Any) -> None:
        """Notify observers of a settlement; observer errors are logged, never silent."""
        for cb in self._outcome_observers:
            try:
                cb(**kwargs)
            except Exception as obs_err:
                logger.error("Outcome observer %s failed: %s", getattr(cb, "__name__", cb), obs_err)

    def _sync_extension_states(self) -> None:
        """Propagate current configuration flags dynamically to active extensions."""
        if getattr(self, "extension_manager", None) is not None:
            for ext in self.extension_manager.get_active_extensions():
                name = ext.__class__.__name__
                if name == "VolatilityAdaptiveExpiry":
                    ext.enabled = self.config.adaptive_expiry_enabled
                elif name == "VolatilityLiquidityGates":
                    ext.enabled = self.config.volatility_gate_enabled or self.config.liquidity_gate_enabled
                elif name == "RSICCIConfluenceExtension":
                    ext.enabled = self.config.rsi_cci_enabled
                elif name == "BayesianSignalFilter":
                    ext.enabled = self.config.bayesian_filter_enabled
                    ext.min_win_probability = self.config.bayesian_min_probability

    def clear_plugin_cache(self) -> None:
        """Invalidate cached extension detection flags (called on plugin reload)."""
        self._sync_extension_states()

    @property
    def status(self) -> dict[str, Any]:
        return {
            "auto_ghost_enabled": self.config.enabled,
            "auto_ghost_amount": self.config.amount,
            "auto_ghost_expiration_seconds": self.config.expiration_seconds,
            "auto_ghost_max_concurrent_trades": self.config.max_concurrent_trades,
            "auto_ghost_per_asset_cooldown_seconds": self.config.per_asset_cooldown_seconds,
            "auto_ghost_minimum_payout_pct": self.config.minimum_payout_pct,
            "auto_ghost_blacklist_assets": self.config.blacklist_assets or [],
            "auto_ghost_rsi_cci_enabled": self.config.rsi_cci_enabled,
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
            "auto_ghost_auto_execute_ai_pulse": self.config.auto_execute_ai_pulse,
            "auto_ghost_min_zscore_enabled": self.config.min_zscore_enabled,
            "auto_ghost_min_zscore": self.config.min_zscore,
            "auto_ghost_max_zscore_enabled": self.config.max_zscore_enabled,
            "auto_ghost_max_zscore": self.config.max_zscore,
            "auto_ghost_regime_gate_enabled": self.config.regime_gate_enabled,
            "auto_ghost_allowed_regimes": self.config.allowed_regimes,
            "auto_ghost_require_regime_stable": self.config.require_regime_stable,

            "auto_ghost_volatility_gate_enabled": self.config.volatility_gate_enabled,
            "auto_ghost_min_volatility": self.config.min_volatility,
            "auto_ghost_max_volatility": self.config.max_volatility,
            "auto_ghost_liquidity_gate_enabled": self.config.liquidity_gate_enabled,
            "auto_ghost_min_liquidity": self.config.min_liquidity,
            "auto_ghost_max_liquidity": self.config.max_liquidity,
            "auto_ghost_adx_gate_enabled": self.config.adx_gate_enabled,
            "auto_ghost_cci_gate_enabled": self.config.cci_gate_enabled,
            "auto_ghost_adaptive_expiry_enabled": self.config.adaptive_expiry_enabled,
            "auto_ghost_min_adaptive_expiry": self.config.min_adaptive_expiry,
            "auto_ghost_bayesian_filter_enabled": self.config.bayesian_filter_enabled,
            "auto_ghost_bayesian_min_probability": self.config.bayesian_min_probability,

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

    def status_for_live_poll(self) -> dict[str, Any]:
        """C1/H1: status payload safe for the live `status_update.auto_ghost` key.

        While calibration mode is active the Ghost widget still consumes this
        object. Session PnL/WR/counts/ids are zeroed so calibration activity
        cannot paint the live UI. Full metrics live under `status_update.calibration`.
        """
        payload = dict(self.status)
        if getattr(self.config, "mode", "standard") != "calibration":
            return payload
        payload["auto_ghost_session_id"] = None
        payload["auto_ghost_session_pnl"] = 0.0
        payload["auto_ghost_session_trades"] = 0
        payload["auto_ghost_session_wins"] = 0
        payload["auto_ghost_session_losses"] = 0
        payload["auto_ghost_current_streak_type"] = None
        payload["auto_ghost_current_streak_count"] = 0
        payload["auto_ghost_max_win_streak"] = 0
        payload["auto_ghost_max_loss_streak"] = 0
        payload["auto_ghost_avg_recovery_time_mins"] = 0.0
        payload["auto_ghost_active_trades"] = 0
        payload["auto_ghost_last_reject_reason_by_asset"] = {}
        payload["auto_ghost_reject_counts"] = {}
        payload["auto_ghost_drawdown_cooldown_active"] = False
        payload["auto_ghost_session_halted"] = False
        return payload

    def report_outcome(
        self,
        trade_id: str,
        outcome: str,
        profit: float,
        *,
        asset: str | None = None,
        entry_context: dict[str, Any] | None = None,
        direction: str | None = None,
        expiration_seconds: int | None = None,
    ) -> None:
        self._session_trade_count += 1
        self._session_pnl += profit
        now = unix_time()

        if expiration_seconds is None and entry_context:
            expiration_seconds = entry_context.get("expiration_seconds")

        # Cache completed trade context in memory for AI Pulse
        self._session_trades.append({
            "timestamp": now,
            "asset": asset,
            "direction": direction or "unknown",
            "outcome": outcome,
            "pnl": profit,
            "expiration_seconds": expiration_seconds,
            "regime_label": entry_context.get("regime_label", "UNKNOWN") if entry_context else "UNKNOWN",
            "entry_context": entry_context,
        })
        # deque(maxlen=200) handles eviction automatically

        # Note: Silent live KB auto-writing (kb_loader.record_trade_outcome) is intentionally disabled
        # to uphold CORE_PRINCIPLES (Zero Silent Writes). All knowledge base mutations must be vetted
        # through the Staging Review gate.

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

        if getattr(self, "extension_manager", None) is not None:
            for ext in self.extension_manager.get_active_extensions():
                if hasattr(ext, "on_trade_outcome"):
                    try:
                        ext.on_trade_outcome({
                            "asset": asset,
                            "outcome": outcome,
                            "profit": profit,
                            "direction": direction,
                            "expiration_seconds": expiration_seconds,
                            "entry_context": entry_context,
                        })
                    except Exception as ext_err:
                        logger.error("Error calling on_trade_outcome on %s: %s", ext.__class__.__name__, ext_err)

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
                task = asyncio.create_task(self._run_trade_count_suggestions())
                task.add_done_callback(lambda t: logger.error("_run_trade_count_suggestions failed: %s", t.exception()) if not t.cancelled() and t.exception() else None)

        # Phase 1 (Calibration Mode): settlement observers (M1 budget accounting,
        # C4 kill-switch). Called for EVERY outcome including voids — the observer
        # decides what counts as evidence.
        if self._outcome_observers:
            self._notify_outcome_observers(
                trade_id=trade_id,
                outcome=outcome,
                profit=profit,
                asset=asset,
                entry_context=entry_context,
                direction=direction,
                expiration_seconds=expiration_seconds,
            )

    def _reject(self, asset: str, reason: str) -> None:
        self._record_reject(asset, reason)
        self._pending_signals.pop(asset, None)

    def _passes_ghost_gates(
        self,
        *,
        asset: str,
        price: float,
        timestamp: float,
        oteo_result: dict[str, Any],
        manipulation: dict[str, Any],
        payout_pct: float | None,
    ) -> str | None:
        """
        Run the ordered Ghost gate cascade (H4 extraction from consider_signal).

        Returns the reject reason string when a gate blocks the signal, or None when
        every gate passes. Rejection bookkeeping (`_reject`) stays with the caller so
        the observable flow contract is unchanged.
        """
        now = unix_time()

        if self.config.blacklist_assets and asset in self.config.blacklist_assets:
            logger.info("Auto-Ghost skipped %s: asset is blacklisted", asset)
            return 'asset_blacklisted'

        if not self.config.enabled:
            return 'disabled'

        if self._session_halted:
            return 'session_halted'
        if self._session_trade_count >= self.config.max_session_trades:
            return 'max_session_trades'
        if now < self._drawdown_cooldown_until:
            return 'drawdown_cooldown'

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
                return 'timeframe_limit'

        if oteo_result.get("recommended") not in {"CALL", "PUT"}:
            return 'not_call_or_put'
        if not oteo_result.get("actionable"):
            return 'not_actionable'

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
                return 'below_min_confidence'
        if self.config.max_confidence_enabled and self.config.max_confidence is not None:
            if score > self.config.max_confidence:
                logger.info(
                    "Auto-Ghost skipped %s: score %.1f > max confidence bounds %.1f",
                    asset,
                    score,
                    self.config.max_confidence
                )
                return 'above_max_confidence'
        if payout_pct is None:
            logger.warning("Auto-Ghost skipped %s: payout unavailable", asset)
            return 'payout_unavailable'
        if self.config.minimum_payout_pct > 0 and payout_pct < self.config.minimum_payout_pct:
            logger.info(
                "Auto-Ghost skipped %s: payout %.1f%% < minimum %.1f%%",
                asset,
                payout_pct,
                self.config.minimum_payout_pct,
            )
            return 'payout_below_minimum'
        if self.config.block_on_manipulation and manipulation:
            if any(_get_severity(sev_val) >= self.config.manipulation_severity_threshold for sev_val in manipulation.values()):
                logger.info(
                    "Auto-Ghost skipped %s due to active manipulation severity: %s (threshold: %.2f)",
                    asset,
                    manipulation,
                    self.config.manipulation_severity_threshold
                )
                return 'manipulation_block'

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
                        return 'below_min_zscore'
                if self.config.max_zscore_enabled and self.config.max_zscore is not None:
                    if z_val > self.config.max_zscore:
                        logger.info(
                            "Auto-Ghost skipped %s: z-score %.2f > max gate %.2f (Ghost Protocol gate)",
                            asset,
                            z_val,
                            self.config.max_zscore,
                        )
                        return 'above_max_zscore'
            except (ValueError, TypeError) as exc:
                logger.warning("Auto-Ghost: non-numeric z_score %r for %s, skipping Z gates: %s", z_score, asset, exc)

        # Regime Gate checks (Ghost Protocol)
        regime_label = oteo_result.get("regime_label")
        regime_stable = oteo_result.get("regime_stable")
        if self.config.regime_gate_enabled and self.config.allowed_regimes:
            if regime_label is None:
                logger.info("Auto-Ghost skipped %s: regime gate enabled but signal has no regime label", asset)
                return 'missing_regime_label'
            if str(regime_label).upper() not in self.config.allowed_regimes:
                logger.info("Auto-Ghost skipped %s: regime %s not in allowed %s (Ghost Protocol gate)", asset, regime_label, self.config.allowed_regimes)
                return 'regime_not_allowed'

        if self.config.regime_gate_enabled and self.config.require_regime_stable and regime_stable is False:
            logger.info("Auto-Ghost skipped %s: regime %s is unstable (Ghost Protocol gate)", asset, regime_label)
            return 'regime_unstable'

        # Volatility Gate checks
        vol_score = _extract_market_context_field(oteo_result, "volatility_score")
        if self.config.volatility_gate_enabled and vol_score is not None:
            if vol_score < self.config.min_volatility or vol_score > self.config.max_volatility:
                logger.info(
                    "Auto-Ghost skipped %s: volatility score %.1f outside gate [%.1f, %.1f] (Volatility Gate)",
                    asset,
                    vol_score,
                    self.config.min_volatility,
                    self.config.max_volatility,
                )
                return 'volatility_gate'

        # Liquidity Gate checks
        liq_score = _extract_market_context_field(oteo_result, "liquidity_score")
        if self.config.liquidity_gate_enabled and liq_score is not None:
            if liq_score < self.config.min_liquidity or liq_score > self.config.max_liquidity:
                logger.info(
                    "Auto-Ghost skipped %s: liquidity score %.1f outside gate [%.1f, %.1f] (Liquidity Gate)",
                    asset,
                    liq_score,
                    self.config.min_liquidity,
                    self.config.max_liquidity,
                )
                return 'liquidity_gate'

        # ADX Gate checks
        adx_regime = _extract_market_context_field(oteo_result, "adx_regime")
        reversal_friendly = _extract_market_context_field(oteo_result, "reversal_friendly")

        if self.config.adx_gate_enabled and adx_regime is not None:
            if str(adx_regime).upper() == "STRONG" and not reversal_friendly:
                logger.info(
                    "Auto-Ghost skipped %s: ADX regime is strong and not reversal friendly (ADX Gate)",
                    asset
                )
                return 'adx_gate_trend_block'

        # CCI Gate checks
        cci_state = _extract_market_context_field(oteo_result, "cci_state")
        direction = str(oteo_result.get("recommended")).upper()

        if self.config.cci_gate_enabled and cci_state is not None:
            if direction == "CALL" and str(cci_state).upper() == "OVERBOUGHT":
                logger.info("Auto-Ghost skipped %s: CCI is overbought but signal recommended CALL (CCI Gate)", asset)
                return 'cci_gate_overbought_call'
            if direction == "PUT" and str(cci_state).upper() == "OVERSOLD":
                logger.info("Auto-Ghost skipped %s: CCI is oversold but signal recommended PUT (CCI Gate)", asset)
                return 'cci_gate_oversold_put'

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
                        return f"plugin_veto_{reason or 'unknown'}"
                except Exception as ext_err:
                    logger.error("Error in extension %s.on_consider_signal: %s", ext.__class__.__name__, ext_err)

        if asset in self._active_assets:
            return 'asset_active'
        if len(self._active_assets) >= self.config.max_concurrent_trades:
            return 'max_concurrent_trades'
        if unix_time() < self._cooldown_until.get(asset, 0):
            return 'asset_cooldown'

        return None

    def _build_trade_request(
        self,
        *,
        asset: str,
        price: float,
        timestamp: float,
        oteo_result: dict[str, Any],
        manipulation: dict[str, Any],
        payout_pct: float | None,
    ) -> TradeExecutionRequest:
        """Build the ghost TradeExecutionRequest with full entry context (H4 extraction)."""
        target_expiration = oteo_result.get("override_expiration_seconds") or self.config.expiration_seconds

        entry_context = {
            "asset": asset,
            "price": price,
            "timestamp": timestamp,
            "expiration_seconds": target_expiration,
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
            "manipulation": manipulation,
            "payout_pct": payout_pct,
        }

        return TradeExecutionRequest(
            asset_id=asset,
            direction=str(oteo_result["recommended"]).lower(),
            amount=self.config.amount,
            expiration=target_expiration,
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

    def _finalize_execution(
        self,
        *,
        asset: str,
        timestamp: float,
        actual_expiry: int,
        recommended: str,
    ) -> None:
        """Post-success bookkeeping: timeframe stamping, cooldown, release task (H4 extraction)."""
        # Record trade execution timestamp for timeframe gating
        self._trade_timestamps.append(timestamp)

        self._cooldown_until[asset] = unix_time() + actual_expiry + self.config.per_asset_cooldown_seconds
        task = asyncio.create_task(self._release_asset(asset, actual_expiry + 1))
        task.add_done_callback(lambda t: logger.error("_release_asset failed: %s", t.exception()) if not t.cancelled() and t.exception() else None)
        logger.info(
            "Auto-Ghost trade opened for %s (%s, %ss)",
            asset,
            recommended,
            actual_expiry,
        )

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
        # Phase 1 (Calibration Mode): entry veto (M10 freeze / state gates).
        veto = self._entry_veto_check() if self._entry_veto_check else None
        if veto:
            return self._reject(asset, veto)

        # Defensive fallback: clean up active assets whose cooldowns have fully elapsed.
        # Only discard assets that have an explicit cooldown set AND it has elapsed;
        # assets currently mid-execution (no cooldown set yet) must be preserved.
        now = unix_time()
        for a in [a for a in self._active_assets if a in self._cooldown_until and now >= self._cooldown_until[a]]:
            self._active_assets.discard(a)

        # H4 extraction: ordered gate cascade (reject bookkeeping preserved at call site).
        reject_reason = self._passes_ghost_gates(
            asset=asset,
            price=price,
            timestamp=timestamp,
            oteo_result=oteo_result,
            manipulation=manipulation,
            payout_pct=payout_pct,
        )
        if reject_reason is not None:
            return self._reject(asset, reject_reason)

        score = float(oteo_result.get("oteo_score", 0.0))

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
            advisory_task = asyncio.create_task(
                self._run_ai_advisory(
                    asset=asset,
                    direction=oteo_result.get("recommended"),
                    oteo_score=score,
                    market_context=oteo_result.get("market_context") or {},
                    manipulation=manipulation,
                    strategy_level=strategy_level,
                )
            )
            advisory_task.add_done_callback(lambda t: logger.error("_run_ai_advisory failed: %s", t.exception()) if not t.cancelled() and t.exception() else None)

        # H4 extraction: entry-context + request construction
        request = self._build_trade_request(
            asset=asset,
            price=price,
            timestamp=timestamp,
            oteo_result=oteo_result,
            manipulation=manipulation,
            payout_pct=payout_pct,
        )

        # C3 fix: reserve capacity SYNCHRONOUSLY before the first await point.
        # There are no awaits between the gate checks above and this line, so the
        # check-and-reserve sequence is atomic within the event loop - concurrent
        # consider_signal tasks can no longer both pass the capacity check.
        self._active_assets.add(asset)

        try:
            result = await self.trade_service.execute_trade(BrokerType.POCKET_OPTION, request)
        except Exception:
            self._active_assets.discard(asset)
            raise

        if not result.get("success"):
            logger.warning("Auto-Ghost failed for %s: %s", asset, result.get("message"))
            self._active_assets.discard(asset)
            return result

        self._finalize_execution(
            asset=asset,
            timestamp=timestamp,
            actual_expiry=request.expiration,
            recommended=str(oteo_result.get("recommended")),
        )
        return result

    async def _emit_pulse_channel(self, event: str, payload: dict[str, Any]) -> None:
        """C1 (Phase 1): route ALL pulse pending/abort emissions through one helper.

        While calibration mode is active, live pulse events are remapped to
        `calibration_*` channels so the live UI hears nothing.
        """
        sio = getattr(self.trade_service, "sio", None)
        if not sio:
            return
        if getattr(self.config, "mode", "standard") == "calibration":
            await sio.emit(f"calibration_{event}", payload)
        else:
            await sio.emit(event, payload)

    async def _emit_notification(self, payload: dict[str, Any]) -> None:
        """H4 (Phase 1.1): route leftover advisory notifications off the live UI.

        Live `notification` toasts (ai_advisory / AI confirmation) must not
        fire during calibration. Kill-switch abort stays on the live channel
        via CalibrationService._emit_loud_abort (intentional visibility).
        """
        sio = getattr(self.trade_service, "sio", None)
        if not sio:
            return
        event = (
            "calibration_notification"
            if getattr(self.config, "mode", "standard") == "calibration"
            else "notification"
        )
        await sio.emit(event, payload)

    async def execute_ai_pulse_signal(
        self,
        *,
        asset: str,
        direction: str,
        target_expiration: int | None = None,
        confidence: float | None = None,
    ) -> Any:
        """Directly dispatch an AI Pulse suggested signal under the ghost controller."""
        if not asset or asset.upper() in ("CALL", "PUT", "BUY", "SELL", "CALL_OTC", "PUT_OTC", "UNKNOWN"):
            logger.warning("Auto-Ghost rejected malformed AI Pulse asset: %r", asset)
            return None

        # Phase 1 (Calibration Mode): entry veto (M10 freeze / state gates).
        veto = self._entry_veto_check() if self._entry_veto_check else None
        if veto:
            logger.info("AI Pulse signal for %s vetoed: %s", asset, veto)
            await self._emit_pulse_channel("ai_pulse_aborted", {"asset": asset, "reason": veto})
            return None

        if not self.config.enabled:
            reason = "Auto-Ghost disabled"
            logger.info("Auto-Ghost is disabled; skipping AI Pulse signal for %s", asset)
            await self._emit_pulse_channel("ai_pulse_aborted", {"asset": asset, "reason": reason})
            return None

        if asset in self._active_assets:
            reason = "Asset already has an active trade"
            logger.info("Auto-Ghost already has active trade for %s; skipping AI Pulse signal", asset)
            await self._emit_pulse_channel("ai_pulse_aborted", {"asset": asset, "reason": reason})
            return None

        if len(self._active_assets) >= self.config.max_concurrent_trades:
            reason = f"Max concurrent trades ({self.config.max_concurrent_trades}) reached"
            logger.info("Auto-Ghost max concurrent trades (%d) reached; skipping AI Pulse signal", self.config.max_concurrent_trades)
            await self._emit_pulse_channel("ai_pulse_aborted", {"asset": asset, "reason": reason})
            return None

        # Adaptive expiry resolution if not explicitly specified
        exp = target_expiration
        if not exp or exp <= 0:
            if self.config.adaptive_expiry_enabled and hasattr(self.trade_service, "_get_market_context"):
                mc = self.trade_service._get_market_context(asset) or {}
                regime = mc.get("regime_label", "")
                vol = float(mc.get("volatility_score", 50.0) or 50.0)
                if regime in ("RANGE_BOUND", "TREND_REVERSAL") and vol < 60.0:
                    exp = 300
                elif regime in ("STRONG_MOMENTUM", "BREAKOUT") or vol >= 70.0:
                    exp = 60
                else:
                    exp = self.config.expiration_seconds or 60
            else:
                exp = self.config.expiration_seconds or 60

        price = 1.0
        if hasattr(self.trade_service, "_latest_logged_price"):
            price = self.trade_service._latest_logged_price(asset) or 1.0
        elif hasattr(self.trade_service, "get_last_price"):
            price = self.trade_service.get_last_price(asset) or 1.0
        # M5 fix: explicit None-handling — never fabricate a payout value.
        payout_pct: float | None = None
        if hasattr(self.trade_service, "adapter") and self.trade_service.adapter:
            try:
                payout_pct = self.trade_service._resolve_payout_pct(self.trade_service.adapter, asset)
            except Exception as payout_err:
                logger.warning("AI Pulse payout resolution failed for %s: %s", asset, payout_err)
                payout_pct = None
        if payout_pct is None:
            logger.info(
                "AI Pulse payout unavailable for %s; recording payout_pct=None in entry context",
                asset,
            )

        conf_level = "HIGH" if (confidence and confidence >= 80) else "MEDIUM"
        entry_context = {
            "asset": asset,
            "price": price,
            "timestamp": unix_time(),
            "expiration_seconds": exp,
            "recommended": direction.upper(),
            "confidence": conf_level,
            "trigger_mode": "ai_pulse",
            "source": "ai_pulse",
            "pulse_confidence": confidence,
            "forecast_horizon": exp,
            "payout_pct": payout_pct,
        }

        request = TradeExecutionRequest(
            asset_id=asset,
            direction=direction.lower(),
            amount=self.config.amount,
            expiration=exp,
            account_key="primary",
            trade_mode="ghost",
            session_id=self._session_id,
            confidence="HIGH" if (confidence and confidence >= 80) else "MEDIUM",
            entry_context=entry_context,
            trigger_mode="ai_pulse",
        )

        try:
            self._active_assets.add(asset)
            self._session_trade_count += 1
            self._trade_timestamps.append(unix_time())
            self._cooldown_until[asset] = unix_time() + exp + self.config.per_asset_cooldown_seconds
            task = asyncio.create_task(self._release_asset(asset, exp + 1))
            task.add_done_callback(lambda t: logger.error("_release_asset failed: %s", t.exception()) if not t.cancelled() and t.exception() else None)

            record = await self.trade_service.execute_trade(BrokerType.POCKET_OPTION, request)
            logger.info("Auto-Ghost executed AI Pulse trade: %s %s %ds", asset, direction, exp)
            return record
        except Exception as exc:
            reason = f"Execution failed: {exc}"
            logger.error("Auto-Ghost AI Pulse trade failed for %s: %s", asset, exc)
            self._active_assets.discard(asset)
            await self._emit_pulse_channel("ai_pulse_aborted", {"asset": asset, "reason": reason})
            return None

    async def schedule_candle_open_pulse_execution(
        self,
        *,
        asset: str,
        direction: str,
        target_price: float | None = None,
        wait_minutes: int | None = 1,
        target_expiration: int | None = None,
        confidence: float | None = None,
    ) -> None:
        """
        Schedule an AI Pulse trade for precision execution on the upcoming 1-minute candle open (T = 00s),
        honoring the requested wait duration (wait_minutes) and running a pre-flight validation gate at T - 5s.
        """
        if not asset or asset.upper() in ("CALL", "PUT", "BUY", "SELL", "CALL_OTC", "PUT_OTC", "UNKNOWN"):
            logger.warning("Auto-Ghost rejected malformed AI Pulse asset in schedule: %r", asset)
            return

        if not self.config.enabled:
            logger.info("Auto-Ghost disabled; skipping scheduled AI Pulse signal for %s", asset)
            return

        now = unix_time()
        wait_m = max(1, int(wait_minutes or 1))
        # Target candle open wait_m minutes away
        target_candle_open = (int(now // 60) + wait_m) * 60.0
        seconds_to_open = max(1.0, target_candle_open - now)

        pending_info = {
            "asset": asset,
            "direction": direction.upper(),
            "target_price": target_price,
            "wait_minutes": wait_m,
            "confidence": confidence,
            "target_candle_open": target_candle_open,
            "seconds_remaining": round(seconds_to_open, 1),
        }

        # Emit WebSocket pending status to UI
        await self._emit_pulse_channel("ai_pulse_pending", pending_info)

        # Wait until T - 5s before candle open for pre-flight validation
        pre_flight_wait = max(0.1, seconds_to_open - 5.0)
        await asyncio.sleep(pre_flight_wait)

        # PRE-FLIGHT VALIDATION GATE (at T - 5s)
        # 1. Capacity & active asset check
        if asset in self._active_assets or len(self._active_assets) >= self.config.max_concurrent_trades:
            reason = "Asset active or max concurrent trades reached"
            logger.info("AI Pulse pre-flight aborted for %s: %s", asset, reason)
            await self._emit_pulse_channel("ai_pulse_aborted", {"asset": asset, "reason": reason})
            return

        # 2. Target Price Proximity Check (Option 2)
        if target_price and target_price > 0:
            current_p = None
            if hasattr(self.trade_service, "_latest_logged_price"):
                current_p = self.trade_service._latest_logged_price(asset)
            elif hasattr(self.trade_service, "get_last_price"):
                current_p = self.trade_service.get_last_price(asset)

            if current_p and current_p > 0:
                deviation_pct = abs(current_p - target_price) / target_price * 100.0
                if deviation_pct > 0.4:
                    reason = f"Price ({current_p:.5f}) deviated {deviation_pct:.2f}% from target zone ({target_price:.5f})"
                    logger.info("AI Pulse pre-flight aborted for %s: %s", asset, reason)
                    await self._emit_pulse_channel("ai_pulse_aborted", {"asset": asset, "reason": reason})
                    return

        # 3. Manipulation check
        mc = {}
        if hasattr(self.trade_service, "_get_market_context"):
            mc = self.trade_service._get_market_context(asset) or {}
        manip = mc.get("manipulation") or {}
        max_sev = max(manip.values()) if manip and isinstance(manip, dict) and manip.values() else 0.0
        if self.config.block_on_manipulation and max_sev >= self.config.manipulation_severity_threshold and self.config.manipulation_severity_threshold > 0:
            reason = f"Manipulation spike ({max_sev:.2f}) >= threshold ({self.config.manipulation_severity_threshold:.2f})"
            logger.info("AI Pulse pre-flight aborted for %s: %s", asset, reason)
            await self._emit_pulse_channel("ai_pulse_aborted", {"asset": asset, "reason": reason})
            return

        # 4. Multi-Scale HTF Directional Bias check
        from .htf_directional_bias import HTFDirectionalBiasEngine
        htf_engine = HTFDirectionalBiasEngine.get_instance()
        candles_1m = mc.get("closed_candles") or []
        recent_ticks = mc.get("recent_ticks") or []
        confluence = htf_engine.evaluate_directional_confluence(
            asset=asset,
            direction=direction,
            candles_1m=candles_1m,
            recent_ticks=recent_ticks,
        )

        if confluence.get("veto"):
            reason = str(confluence.get("veto_reason") or "HTF Directional Bias Veto")
            logger.info("AI Pulse pre-flight aborted for %s: %s", asset, reason)
            await self._emit_pulse_channel("ai_pulse_aborted", {"asset": asset, "reason": reason})
            return

        # 5. Bayesian Win Probability floor check (51% - 56%) - fail-closed (C2 fix)
        calibrated_floor = confluence.get("calibrated_bayesian_floor", self.config.bayesian_min_probability)
        b_prob = mc.get("bayesian_win_probability_60s") or mc.get("bayesian_win_probability")
        if self.config.bayesian_filter_enabled:
            if b_prob is None:
                reason = "Bayesian win probability unavailable (fail-closed: filter enabled but no WP computed yet)"
                logger.info("AI Pulse pre-flight aborted for %s: %s", asset, reason)
                await self._emit_pulse_channel("ai_pulse_aborted", {"asset": asset, "reason": reason})
                return
            if float(b_prob) < calibrated_floor:
                reason = f"Bayesian probability ({float(b_prob)*100:.1f}%) below floor ({calibrated_floor*100:.1f}%)"
                logger.info("AI Pulse pre-flight aborted for %s: %s", asset, reason)
                await self._emit_pulse_channel("ai_pulse_aborted", {"asset": asset, "reason": reason})
                return

        # Wait remaining time until EXACT T = 00.000s (New Candle Open)
        remaining = max(0.001, target_candle_open - unix_time())
        await asyncio.sleep(remaining)

        # Execute market trade on candle open
        await self.execute_ai_pulse_signal(
            asset=asset,
            direction=direction,
            target_expiration=target_expiration,
            confidence=confidence,
        )

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
        z_score = market_context.get("z_score", "N/A")
        volatility_score = market_context.get("volatility_score", "N/A")
        liquidity_score = market_context.get("liquidity_score", "N/A")
        b_prob = market_context.get("bayesian_win_probability") or market_context.get("bayesian_win_probability_60s")
        bayesian_str = f"{float(b_prob)*100:.1f}%" if b_prob is not None else "N/A"

        # Retrieve only high-confidence historical patterns (min sample N >= 20)
        kb_loader = KnowledgeBaseLoader.get_instance()
        from shared.utc_time_blocks import utc_4h_block as _utc_4h_block
        matched_patterns = kb_loader.query_top_patterns(
            asset=asset,
            strategy_level=strategy_level,
            oteo_score=oteo_score,
            regime_label=regime_label,
            direction=direction,
            min_sample_size=20,
            utc_4h_block=_utc_4h_block(unix_time()),
        )
        patterns_context = (
            format_patterns_for_prompt(matched_patterns)
            if matched_patterns
            else "No high-sample historical patterns (Relying strictly on live market physics & Bayesian probability)"
        )

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

        # Expiry duration context
        vol_adaptive_expiry = market_context.get("volatility_adaptive_expiry")
        suggested_expiry_str = f"{vol_adaptive_expiry}s (Volatility-Adaptive)" if vol_adaptive_expiry else f"{self.config.expiration_seconds}s (Static)"

        user_msg = (
            f"Trade Setup to Verify:\n"
            f"Asset: {asset}\n"
            f"Direction: {direction}\n"
            f"OTEO Score: {oteo_score}\n"
            f"Strategy Level: {strategy_level.upper()}\n"
            f"Suggested Expiry: {suggested_expiry_str}\n"
            f"Regime: {regime_label} (confidence: {regime_confidence}%, stable: {regime_stable})\n"
            f"Trend Direction: {trend}\n"
            f"Z-Score: {z_score}\n"
            f"Volatility / Liquidity: Vol={volatility_score}, Liq={liquidity_score}\n"
            f"Bayesian Win Probability: {bayesian_str}\n"
            f"ADX: {adx}\n"
            f"CCI: {cci} ({cci_state})\n"
            f"Nearest S/R: {nearest_structure_atr} ATR\n"
            f"Tick Health: {tick_health}\n"
            f"Active Manipulation: {active_manip}\n\n"
            f"Historical Context (Statistically Proven Patterns N >= 20):\n"
            f"{patterns_context}\n\n"
            f"Decision Criteria:\n"
            f"1. Base decision on live market physics, manipulation severity, regime alignment, and Bayesian probability.\n"
            f"2. Confirm clean, stable structural setups with low manipulation.\n"
            f"3. Reject setups during extreme manipulation spikes (>0.40) or severe momentum divergence.\n\n"
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
            from shared.utc_time_blocks import utc_4h_block as _utc_4h_block
            matched_patterns = kb_loader.query_top_patterns(
                asset=asset,
                strategy_level=strategy_level,
                oteo_score=oteo_score,
                regime_label=regime_label,
                direction=direction,
                utc_4h_block=_utc_4h_block(unix_time()),
            )
            top_pattern_str = "No KB Match"
            if matched_patterns:
                top_p = matched_patterns[0]
                top_pattern_str = f"KB Match: WR={top_p.get('win_rate_pct', 0.0):.1f}%, N={top_p.get('sample_size', 0)}"

            msg = f"[AI Advisor] Trade Setup {direction} on {asset} reviewed. Decision: {response}. ({top_pattern_str})"
            if self.trade_service.sio:
                await self._emit_notification({
                    "type": "info" if confirmed else "warning",
                    "message": msg,
                    "timestamp": unix_time(),
                })
            logger.info("AI Advisory completed for %s: %s (%s)", asset, response, top_pattern_str)
        except Exception as e:
            logger.warning("AI Advisory background query failed for %s: %s", asset, e)

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
                await self._emit_notification({
                    "type": "ai_advisory",
                    "message": ai_suggestion,
                    "timestamp": unix_time(),
                })
        except Exception as e:
            logger.warning("AI Trade Count Suggestion background query failed: %s", e)
