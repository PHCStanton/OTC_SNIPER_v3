"""Session-First Learning: live session performance tracker + 3-layer effective WR engine.

feat/ai_kb (Session_First_Learning decision record 26-09-04).

Design contracts:
- Session key: strictly ``AutoGhostService._session_id``. A new session id
  archives the previous live session into Layer-2 history and resets all
  counters. Never keyed to websocket uptime.
- Calibration isolation: sessions matching ``auto_ghost_calib_*`` are never
  recorded and never archived into Layer-2 history (calibration runs must not
  pollute live trading statistics).
- Voids: ``void`` outcomes carry zero win-rate evidence — they never touch
  streaks, settled counts, or regime stats.
- Horizon isolation: 60s and 300s expiries are tracked separately.
- UTC 4h blocks: origin 22:00 UTC, blocks 0..5 (``shared.utc_time_blocks``).
- KB staging invariant: strictly READ-ONLY against the knowledge base. This
  module NEVER writes ``bayesian_priors*.json`` / ``condition_patterns.json``.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from time import time as unix_time
from typing import Any

from shared.utc_time_blocks import utc_4h_block, utc_4h_label

logger = logging.getLogger(__name__)

# Calibration sessions must never pollute live trading statistics (M1/M9).
CALIB_SESSION_PREFIX = "auto_ghost_calib_"

MAX_SETTLED_TRADES = 50
MAX_SESSION_HISTORY = 6  # keeps >= 3 same-day sessions available for Layer 2
RECENT_SESSION_WINDOW = 3  # Layer 2 uses up to the 3 most recent sessions today
LAYER3_MIN_PATTERN_SAMPLE = 20  # mirror the AI-confirmation evidence bar (N >= 20)
LAYER3_TOP_N = 8

# Session-local regime veto triggers (Category A, Step 4):
#   0 wins out of >= 5 settled outcomes, OR win rate <= 2/12 (~16.7%) with N >= 12.
REGIME_VETO_ZERO_WIN_MIN_SETTLED = 5
REGIME_VETO_WR_MIN_SETTLED = 12
REGIME_VETO_MAX_WR = 2.0 / 12.0


def effective_wr_weights(n_session: int) -> tuple[float, float, float]:
    """Weight matrix ``(w_session, w_recent, w_kb)`` keyed by session sample size.

    - N < 10       -> 0.40 / 0.30 / 0.30  (early session)
    - 10 <= N < 20 -> 0.50 / 0.25 / 0.25  (developing)
    - N >= 20      -> 0.60 / 0.20 / 0.20  (established — session-first bias)
    """
    if n_session < 10:
        return (0.40, 0.30, 0.30)
    if n_session < 20:
        return (0.50, 0.25, 0.25)
    return (0.60, 0.20, 0.20)


def _utc_date(ts: float) -> str:
    """UTC calendar day (YYYY-MM-DD) for a Unix timestamp."""
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%d")


@dataclass(frozen=True)
class SettledOutcome:
    """One settled live ghost outcome (voids are never recorded)."""

    outcome: str  # "win" | "loss"
    regime_label: str  # normalized upper-case, "UNKNOWN" when absent
    horizon: int | None  # expiration seconds (60 / 300); None when unknown
    settled_at: float


@dataclass(frozen=True)
class SessionSnapshot:
    """Archived end-of-session summary feeding Layer 2 (recent sessions)."""

    session_id: str
    ended_at: float
    utc_date: str
    wins_by_horizon: dict
    losses_by_horizon: dict
    is_calibration: bool = False


class SessionPerformanceTracker:
    """In-memory, session-scoped live performance state (Steps 1 + 2).

    Lightweight and standalone: no persistence, no background loops, no KB
    writes. All state dies with the process; Layer-2 history is rebuilt from
    archived live sessions within the current server lifetime only.
    """

    def __init__(
        self,
        max_settled: int = MAX_SETTLED_TRADES,
        max_history: int = MAX_SESSION_HISTORY,
    ) -> None:
        self._session_id: str | None = None
        self._session_started_at: float | None = None
        self._settled: deque[SettledOutcome] = deque(maxlen=max_settled)
        self._streak: int = 0  # +N consecutive wins, -N consecutive losses, 0 initially
        self._per_regime: dict[str, dict[str, int]] = {}
        self._history: deque[SessionSnapshot] = deque(maxlen=max_history)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @property
    def session_started_at(self) -> float | None:
        return self._session_started_at

    def ensure_session(self, session_id: str | None, *, now: float | None = None) -> bool:
        """Align the tracker with ``AutoGhostService._session_id``.

        Returns True when the tracker (re)bound to a new session: the previous
        live session is archived into Layer-2 history (calibration sessions are
        NEVER archived) and all counters reset.
        """
        if session_id == self._session_id:
            return False
        self._archive_current(now=now)
        self._session_id = session_id
        self._session_started_at = now if now is not None else unix_time()
        self._settled.clear()
        self._streak = 0
        self._per_regime.clear()
        return True

    def _archive_current(self, *, now: float | None = None) -> None:
        """Archive the current live session for Layer-2 (recent-sessions) evidence."""
        if not self._session_id or self._session_id.startswith(CALIB_SESSION_PREFIX):
            return  # nothing live to archive, or a calibration session (never archived)
        if not self._settled:
            return  # empty sessions carry zero Layer-2 evidence
        ended = now if now is not None else unix_time()
        wins_by_h: dict = {}
        losses_by_h: dict = {}
        for o in self._settled:
            target = wins_by_h if o.outcome == "win" else losses_by_h
            target[o.horizon] = target.get(o.horizon, 0) + 1
        self._history.append(
            SessionSnapshot(
                session_id=self._session_id,
                ended_at=ended,
                utc_date=_utc_date(ended),
                wins_by_horizon=wins_by_h,
                losses_by_horizon=losses_by_h,
                is_calibration=False,
            )
        )

    def archive_calibration_session(
        self,
        *,
        session_id: str,
        settled_trades: list[dict[str, Any]],
        ended_at: float | None = None,
    ) -> bool:
        """Archive a completed calibration session into Layer 2 (recent sessions).

        Bridges empirical calibration evidence into the 3-layer effective WR
        engine on the same UTC day without polluting live session counters
        (_settled, _streak, _per_regime remain untouched).
        """
        if not settled_trades:
            return False
        ended = ended_at if ended_at is not None else unix_time()
        wins_by_h: dict[int, int] = {}
        losses_by_h: dict[int, int] = {}
        for t in settled_trades:
            outcome = str(t.get("outcome") or "").lower()
            if outcome not in ("win", "loss"):
                continue
            exp = t.get("expiration_seconds") or t.get("duration")
            h = int(exp) if exp else 60
            if outcome == "win":
                wins_by_h[h] = wins_by_h.get(h, 0) + 1
            else:
                losses_by_h[h] = losses_by_h.get(h, 0) + 1

        if not wins_by_h and not losses_by_h:
            return False

        self._history.append(
            SessionSnapshot(
                session_id=session_id,
                ended_at=ended,
                utc_date=_utc_date(ended),
                wins_by_horizon=wins_by_h,
                losses_by_horizon=losses_by_h,
                is_calibration=True,
            )
        )
        return True

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_settlement(
        self,
        *,
        outcome: str,
        regime_label: str = "UNKNOWN",
        horizon: int | None = None,
        session_id: str | None = None,
        now: float | None = None,
    ) -> None:
        """Record one settled ghost outcome into the current live session.

        - Voids are ignored entirely (neither wins nor losses — zero evidence).
        - Settlements tagged with an ``auto_ghost_calib_*`` session id are ignored.
        - Unkeyed settlements (no session id anywhere) are dropped LOUDLY —
          never silently folded into the wrong session.
        """
        if outcome not in ("win", "loss"):
            return  # void (or unknown) outcomes provide zero WR evidence
        if session_id is not None:
            if str(session_id).startswith(CALIB_SESSION_PREFIX):
                return
            self.ensure_session(session_id, now=now)
        if self._session_id is None or self._session_id.startswith(CALIB_SESSION_PREFIX):
            logger.warning(
                "Session tracker dropped %s settlement: no live session bound (settlement session_id=%r)",
                outcome,
                session_id,
            )
            return

        settled_at = now if now is not None else unix_time()
        regime = str(regime_label or "UNKNOWN").strip().upper() or "UNKNOWN"
        self._settled.append(
            SettledOutcome(
                outcome=outcome,
                regime_label=regime,
                horizon=int(horizon) if horizon else None,
                settled_at=settled_at,
            )
        )
        tally = self._per_regime.setdefault(regime, {"wins": 0, "losses": 0})
        tally["wins" if outcome == "win" else "losses"] += 1
        if outcome == "win":
            self._streak = self._streak + 1 if self._streak > 0 else 1
        else:
            self._streak = self._streak - 1 if self._streak < 0 else -1

    # ------------------------------------------------------------------
    # Session reads (Step 1 tracked state)
    # ------------------------------------------------------------------

    @property
    def settled_trades(self) -> list[SettledOutcome]:
        """Snapshot list of settled outcomes (voids never present)."""
        return list(self._settled)

    @property
    def settled_count(self) -> int:
        return len(self._settled)

    @property
    def wins(self) -> int:
        return sum(1 for o in self._settled if o.outcome == "win")

    @property
    def losses(self) -> int:
        return sum(1 for o in self._settled if o.outcome == "loss")

    @property
    def last_10_settled(self) -> list[str]:
        """Slice of the last 10 settled outcomes: ``["win", "loss", ...]``."""
        return [o.outcome for o in list(self._settled)[-10:]]

    @property
    def rolling_session_wr(self) -> float | None:
        """Win rate over ALL settled trades in the current session; None if N == 0."""
        if not self._settled:
            return None
        return self.wins / len(self._settled)

    @property
    def current_streak(self) -> int:
        return self._streak

    @property
    def per_regime_stats(self) -> dict[str, dict[str, Any]]:
        """``regime -> {"wins", "losses", "settled", "wr"}`` for the current session."""
        stats: dict[str, dict[str, Any]] = {}
        for regime, tally in self._per_regime.items():
            settled = tally["wins"] + tally["losses"]
            stats[regime] = {
                "wins": tally["wins"],
                "losses": tally["losses"],
                "settled": settled,
                "wr": (tally["wins"] / settled) if settled else 0.0,
            }
        return stats

    @property
    def utc_4h_block_index(self) -> int:
        """Current UTC 4h block index (0..5, origin 22:00 UTC)."""
        return utc_4h_block(unix_time())

    @property
    def utc_4h_block_label(self) -> str:
        """Human-readable window for the active 4h block, e.g. ``18:00-22:00``."""
        return utc_4h_label(self.utc_4h_block_index)

    @property
    def last_regime_label(self) -> str | None:
        """Regime of the most recent settled outcome (None when unset/unknown)."""
        if not self._settled:
            return None
        regime = self._settled[-1].regime_label
        return regime if regime and regime != "UNKNOWN" else None

    # ------------------------------------------------------------------
    # Session-local regime veto support (Category A)
    # ------------------------------------------------------------------

    def regime_veto_candidates(self) -> list[str]:
        """Regimes meeting a session-local veto trigger.

        Trigger (Step 4.1.2): a regime achieving 0 wins out of >= 5 settled
        outcomes, or win rate <= 2/12 (~16.7%) with N >= 12, in the active
        session.
        """
        flagged: list[str] = []
        for regime, s in self.per_regime_stats.items():
            if s["settled"] >= REGIME_VETO_ZERO_WIN_MIN_SETTLED and s["wins"] == 0:
                flagged.append(regime)
            elif s["settled"] >= REGIME_VETO_WR_MIN_SETTLED and s["wr"] <= REGIME_VETO_MAX_WR:
                flagged.append(regime)
        return flagged

    # ------------------------------------------------------------------
    # Three-layer effective win rate engine (Step 2)
    # ------------------------------------------------------------------

    def layer1_session_wr(self, *, horizon: int | None = None) -> float | None:
        """Layer 1 — current session settled trades (optionally horizon-filtered)."""
        subset = [o for o in self._settled if horizon is None or o.horizon == horizon]
        if not subset:
            return None
        wins = sum(1 for o in subset if o.outcome == "win")
        return wins / len(subset)

    def layer2_recent_wr(self, *, horizon: int | None = None, now: float | None = None) -> float | None:
        """Layer 2 — settled WR across up to 3 most recent live ghost sessions.

        Restricted to sessions archived on the SAME UTC calendar day and, when
        ``horizon`` is given, the SAME expiry horizon. Returns None when no
        prior session today carries evidence for the requested horizon.
        """
        today = _utc_date(now if now is not None else unix_time())
        wins = 0
        losses = 0
        used = 0
        for snap in reversed(self._history):
            if used >= RECENT_SESSION_WINDOW:
                break
            if snap.utc_date != today:
                continue
            if horizon is not None:
                w = snap.wins_by_horizon.get(horizon, 0)
                l = snap.losses_by_horizon.get(horizon, 0)
            else:
                w = sum(snap.wins_by_horizon.values())
                l = sum(snap.losses_by_horizon.values())
            if w + l == 0:
                continue  # no evidence on this horizon — does not consume a session slot
            wins += w
            losses += l
            used += 1
        if wins + losses == 0:
            return None
        return wins / (wins + losses)

    def layer3_kb_wr(
        self,
        *,
        regime_label: str | None = None,
        now: float | None = None,
        asset: str | None = None,
    ) -> float | None:
        """Layer 3 — recency-weighted book WR for the current regime + UTC block.

        Reads the offline-mined condition-pattern book (itself recency-weighted
        at mining time via the 21-day half-life backfill) and aggregates
        matching patterns with sample-size weighting. STRICTLY read-only.
        Returns None (missing — never a hallucinated 50.0%) when no qualifying
        pattern matches.
        """
        try:
            from .ai_review import KnowledgeBaseLoader

            block = utc_4h_block(now if now is not None else unix_time())
            patterns = KnowledgeBaseLoader.get_instance().query_top_patterns(
                asset=asset,
                regime_label=regime_label,
                utc_4h_block=block,
                min_sample_size=LAYER3_MIN_PATTERN_SAMPLE,
                top_n=LAYER3_TOP_N,
            )
        except Exception as exc:  # KB unavailable must never break live tracking
            logger.warning("Session tracker Layer-3 KB query failed; layer marked missing: %s", exc)
            return None

        weighted = 0.0
        total_n = 0
        for p in patterns:
            n = int(p.get("sample_size", 0) or 0)
            wr = p.get("win_rate_pct")
            if n <= 0 or wr is None:
                continue
            weighted += float(wr) * n
            total_n += n
        if total_n <= 0:
            return None
        return (weighted / total_n) / 100.0

    def effective_win_rate(
        self,
        *,
        regime_label: str | None = None,
        horizon: int | None = None,
        now: float | None = None,
        asset: str | None = None,
    ) -> dict[str, Any]:
        """Composite 3-layer effective win rate with renormalization guardrail.

        ``effective_wr = w_session*WR_session + w_recent*WR_recent + w_kb*WR_kb``

        Missing layers are dropped and the remaining weights are renormalized
        to sum to 1.0 (logged). Never hallucinates a default 50.0% WR: if NO
        layer has data, ``effective_wr`` is None.
        """
        now = now if now is not None else unix_time()
        n_session = len(self._settled)
        w_session, w_recent, w_kb = effective_wr_weights(n_session)
        spec = {
            "session": (w_session, self.layer1_session_wr(horizon=horizon)),
            "recent": (w_recent, self.layer2_recent_wr(horizon=horizon, now=now)),
            "kb": (w_kb, self.layer3_kb_wr(regime_label=regime_label, now=now, asset=asset)),
        }
        components = {name: wr for name, (_w, wr) in spec.items() if wr is not None}
        missing = [name for name, (_w, wr) in spec.items() if wr is None]
        renormalized = bool(missing)
        weights: dict[str, float] = {}
        if components:
            total_w = sum(w for name, (w, _wr) in spec.items() if name in components)
            weights = {name: spec[name][0] / total_w for name in components}
            if renormalized:
                logger.info(
                    "Effective WR renormalized after missing layers %s (weights: %s)",
                    missing,
                    {k: round(v, 4) for k, v in weights.items()},
                )
            effective = sum(components[name] * weights[name] for name in components)
        else:
            effective = None
            logger.info(
                "Effective WR UNAVAILABLE: no layer has data (N_session=%d, regime=%r)",
                n_session,
                regime_label,
            )
        return {
            "effective_wr": effective,
            "weights": weights,
            "components": components,
            "renormalized": renormalized,
            "missing_layers": missing,
            "n_session": n_session,
        }
