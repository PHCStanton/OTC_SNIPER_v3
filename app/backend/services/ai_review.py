"""
AI Review Service — OTC SNIPER v3

Periodic advisory-only AI review loop for regime validation and setup grading.

Design contract:
  - Runs at a configurable interval (default 300 s) as a background asyncio task.
  - Sends a market state snapshot to the AI provider and stores the structured result.
  - NEVER modifies signals, scores, or triggers trades.
  - AI failures are fully non-fatal: logged and silently skipped.
  - Covers all 6 Market_Regimes.md labels in every review prompt.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .ai_service import AIService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regime taxonomy injected into every review prompt so the AI has full context
# on what each label means for OTC binary options reversal strategies.
# ---------------------------------------------------------------------------
_REGIME_TAXONOMY = """
Market Regime Taxonomy (OTC Binary Options — OTEO Reversal Strategy):
  RANGE_BOUND      — Price oscillates between clear S/R. Ideal for OTEO reversals.
  TREND_REVERSAL   — ADX falling from peak, DI crossing, direction changing. Good for reversals.
  TREND_PULLBACK   — Clear HH/HL or LH/LL. Conditional: allow only trend-aligned entries.
  STRONG_MOMENTUM  — Persistent one-directional move, high ADX. Dangerous for reversals.
  BREAKOUT         — Price breaks S/R with expanding volatility. Avoid until stabilized.
  CHOPPY           — Erratic wicks, no clear structure. No statistical edge — avoid entirely.
  INSUFFICIENT_DATA — Not enough candles for classification yet.
""".strip()


_MANIPULATION_TAXONOMY = """
OTC Manipulation & Microstructure Patterns:
  Liquidity Sweeps / Grabs — Stop clusters swept before sharp reversal. Signal: Sudden velocity spike + immediate reversal. Impact: High false exhaustion signals.
  Pinning                  — Price held near psychological level/round numbers. Signal: Low price range over 15-30 ticks. Impact: False stable conditions before trap.
  Push & Snap              — Aggressive push followed by immediate snap back. Signal: Extreme velocity (>3-4x average). Impact: Strong false reversal setups.
  Fake Breakouts           — Structure broken briefly before hard reversal. Signal: Break + quick failure + increased reversal density. Impact: Classic trap for momentum.
  Chop / Whipsaw           — Erratic back-and-forth, no bias. Signal: High reversal density + low directional efficiency. Impact: Very dangerous for reversals.
  Dead / Low Liquidity     — Extremely slow tick rate. Signal: Tick frequency < 8-12 per minute. Impact: Amplified fake moves.
  Multi-Asset Coordination — Correlated pairs moving in lockstep. Signal: Simultaneous signals across 3+ assets. Impact: Broker-wide manipulation.
""".strip()


class AIReviewService:
    """
    Background periodic AI review loop.

    Attach to StreamingService via `attach_to_streaming()`.
    Call `push_snapshot(asset, snapshot)` from the streaming pipeline
    to supply fresh market state for the next review cycle.
    """

    def __init__(self, ai_service: "AIService", interval_seconds: int = 300) -> None:
        self._ai_service = ai_service
        self._interval = max(30, int(interval_seconds))
        self._running = False
        self._task: asyncio.Task | None = None
        # Latest snapshot per asset, updated by the streaming pipeline
        self._pending_snapshots: dict[str, dict[str, Any]] = {}
        # Latest completed review per asset
        self._last_reviews: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._review_loop())
        self._task.add_done_callback(self._on_loop_done)
        logger.info("AI review loop started (interval: %ds)", self._interval)

    def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("AI review loop stopped")

    def _on_loop_done(self, task: asyncio.Task) -> None:
        if not task.cancelled() and task.exception() is not None:
            logger.error("AI review loop terminated with error: %s", task.exception())

    # ------------------------------------------------------------------
    # Snapshot ingestion (called by streaming pipeline — non-blocking)
    # ------------------------------------------------------------------

    def push_snapshot(self, asset: str, snapshot: dict[str, Any]) -> None:
        """
        Store the latest market snapshot for an asset.
        Called from StreamingService on each actionable tick (non-blocking).
        The review loop picks up the most recent snapshot at each interval.
        """
        self._pending_snapshots[asset] = snapshot

    def clear_asset(self, asset: str) -> None:
        """Remove buffered state for a specific asset (e.g. on asset removal)."""
        self._pending_snapshots.pop(asset, None)
        self._last_reviews.pop(asset, None)

    def clear_all(self) -> None:
        """Remove all buffered state (e.g. on streaming stop)."""
        self._pending_snapshots.clear()
        self._last_reviews.clear()

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def get_last_review(self, asset: str | None = None) -> dict[str, Any] | None:
        """Return the latest review result, optionally filtered by asset."""
        if asset:
            return self._last_reviews.get(asset)
        # Return the most recently completed review across all assets
        if not self._last_reviews:
            return None
        return max(self._last_reviews.values(), key=lambda r: r.get("timestamp", 0))

    def get_all_reviews(self) -> dict[str, Any]:
        return dict(self._last_reviews)

    # ------------------------------------------------------------------
    # Review loop
    # ------------------------------------------------------------------

    async def _review_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self._interval)
            if not self._running:
                break
            snapshots = dict(self._pending_snapshots)
            for asset, snapshot in snapshots.items():
                try:
                    await self._perform_review(asset, snapshot)
                except Exception as exc:  # non-fatal
                    logger.warning("AI review iteration failed for %s: %s", asset, exc)

    async def _perform_review(self, asset: str, snapshot: dict[str, Any]) -> None:
        """Send one snapshot to the AI provider and store the result."""
        if not self._ai_service:
            return

        from ..models.ai_models import AIChatRequest, AIContext, AIMessage

        prompt = self._build_review_prompt(snapshot)
        context = AIContext(
            asset=asset,
            session_pnl=snapshot.get("session_pnl"),
            win_rate=snapshot.get("recent_win_rate"),
            total_trades=snapshot.get("recent_trade_count"),
        )

        try:
            request = AIChatRequest(
                messages=[AIMessage(role="user", content=prompt)],
                context=context,
            )
            result = await asyncio.wait_for(
                self._ai_service.chat(request), timeout=10.0
            )
        except asyncio.TimeoutError:
            logger.warning("AI review timed out for %s", asset)
            return
        except Exception as exc:
            logger.warning("AI review request failed for %s: %s", asset, exc)
            return

        self._last_reviews[asset] = {
            "timestamp": time.time(),
            "asset": asset,
            "regime_label": snapshot.get("regime_label"),
            "regime_confidence": snapshot.get("regime_confidence"),
            "regime_stable": snapshot.get("regime_stable"),
            "ai_response": result.text,
            "model": result.model,
        }
        logger.info(
            "AI review completed for %s (regime: %s, confidence: %s%%)",
            asset,
            snapshot.get("regime_label"),
            snapshot.get("regime_confidence"),
        )

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_review_prompt(self, snapshot: dict[str, Any]) -> str:
        """Build a regime-aware review prompt covering all 6 Market_Regimes.md labels."""

        # Per-regime condition stats from AutoGhost (if available)
        condition_stats = snapshot.get("condition_stats") or {}
        regime_label = snapshot.get("regime_label", "UNKNOWN")
        regime_stat_key = f"regime:{regime_label}"
        regime_stats = condition_stats.get(regime_stat_key, {})
        regime_win_rate = regime_stats.get("win_rate", "N/A")
        regime_trade_count = regime_stats.get("total", 0)

        manipulation = snapshot.get("manipulation") or {}
        manip_summary = (
            ", ".join(f"{k}={v:.2f}" for k, v in manipulation.items())
            if manipulation
            else "None"
        )

        # Retrieve matching historical patterns for periodic review context
        kb_loader = KnowledgeBaseLoader.get_instance()
        matched_patterns = kb_loader.query_top_patterns(
            asset=snapshot.get("asset", ""),
            regime_label=regime_label
        )
        patterns_context = format_patterns_for_prompt(matched_patterns)

        return f"""You are an OTC binary options market analyst reviewing a live market state snapshot.

{_REGIME_TAXONOMY}

{_MANIPULATION_TAXONOMY}

Current Market State:
  Asset:              {snapshot.get('asset', 'Unknown')}
  Detected Regime:    {regime_label} (confidence: {snapshot.get('regime_confidence', 0)}%, stable: {snapshot.get('regime_stable', False)})
  Regime Persistence: {snapshot.get('regime_persistence', 'N/A')} candles
  Prior Regime:       {snapshot.get('regime_prior', 'N/A')}
  ADX:                {snapshot.get('adx', 'N/A')} (slope: {snapshot.get('adx_slope', 'N/A')})
  DI Spread:          {snapshot.get('di_spread', 'N/A')}
  CCI:                {snapshot.get('cci', 'N/A')} ({snapshot.get('cci_state', 'N/A')})
  CCI Divergence:     {snapshot.get('cci_divergence', 'None')}
  ATR:                {snapshot.get('atr', 'N/A')}
  Nearest S/R:        {snapshot.get('nearest_structure_atr', 'N/A')} ATR units
  Tick Health:        {snapshot.get('tick_health', 'N/A')} ({snapshot.get('tick_frequency', 'N/A')}/min)
  Manipulation:       {manip_summary}

Recent Performance:
  Win Rate:           {snapshot.get('recent_win_rate', 'N/A')}% (last {snapshot.get('recent_trade_count', 'N/A')} trades)
  Regime Win Rate:    {regime_win_rate}% ({regime_trade_count} trades in {regime_label})
  Session P&L:        {snapshot.get('session_pnl', 'N/A')}

Historical Context (Top Matching KB Patterns for Asset/Regime):
{patterns_context}

Provide a concise review (max 150 words) with these 4 points:
1. REGIME AGREEMENT: Do you agree with the {regime_label} classification? (YES/NO + one-line reason)
2. SETUP GRADE: Rate current conditions for OTEO reversals (A=excellent, B=good, C=marginal, D=poor, F=avoid)
3. CAUTION FLAGS: Any unusual conditions or risks to highlight?
4. RECOMMENDATION: One sentence of actionable guidance based on historical matching patterns.
""".strip()


class KnowledgeBaseLoader:
    _instance = None

    def __init__(self) -> None:
        self.patterns: list[dict[str, Any]] = []
        self.metadata: dict[str, Any] = {}
        self.loaded: bool = False

    @classmethod
    def get_instance(cls) -> KnowledgeBaseLoader:
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.lazy_load()
        return cls._instance

    def lazy_load(self) -> None:
        if self.loaded:
            return
        kb_path = self._find_kb_path()
        if not kb_path or not kb_path.exists():
            logger.warning("Knowledge Base file not found. AI confirmation will run without historical patterns.")
            return
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.patterns = data.get("patterns", [])
                self.metadata = data.get("metadata", {})
                self.loaded = True
                logger.info("Successfully loaded %d patterns from Knowledge Base.", len(self.patterns))
        except Exception as e:
            logger.error("Failed to load Knowledge Base from %s: %s", kb_path, e)

    def _find_kb_path(self) -> Path | None:
        try:
            p1 = Path(__file__).resolve().parents[3] / "reports" / "analysis" / "knowledge_base" / "condition_patterns.json"
            if p1.exists():
                return p1
        except Exception:
            pass

        p2 = Path("reports/analysis/knowledge_base/condition_patterns.json")
        if p2.exists():
            return p2.resolve()

        try:
            p3 = Path(__file__).resolve().parents[2] / "reports" / "analysis" / "knowledge_base" / "condition_patterns.json"
            if p3.exists():
                return p3
        except Exception:
            pass

        return None

    def query_top_patterns(
        self,
        asset: str,
        strategy_level: str | None = None,
        oteo_score: float | None = None,
        regime_label: str | None = None,
        direction: str | None = None,
        top_n: int = 5,
    ) -> list[dict[str, Any]]:
        if not self.loaded:
            self.lazy_load()
        if not self.patterns:
            return []

        score_band = get_score_band(oteo_score) if oteo_score is not None else None
        clean_asset = asset.strip().lower().replace("_otc", "") if asset else None
        target_level = strategy_level.strip().lower() if strategy_level else None
        target_regime = regime_label.strip().upper() if regime_label else None
        target_direction = direction.strip().upper() if direction else None

        scored_patterns = []
        for p in self.patterns:
            similarity = 0
            p_asset = p.get("asset", "").strip().lower().replace("_otc", "")
            p_level = p.get("strategy_level", "").strip().lower()
            p_regime = p.get("regime_label", "").strip().upper()
            p_band = p.get("oteo_score_band", "").strip()
            p_dir = p.get("direction", "").strip().upper()

            if clean_asset:
                if p_asset == clean_asset:
                    similarity += 10

            if target_level:
                if p_level == target_level:
                    similarity += 5

            if target_regime:
                if p_regime == target_regime:
                    similarity += 5

            if score_band:
                if p_band == score_band:
                    similarity += 3

            if target_direction:
                if p_dir == target_direction:
                    similarity += 2

            min_required = 0
            if clean_asset:
                min_required += 5
            if target_regime:
                min_required += 5

            if similarity >= max(5, min_required):
                scored_patterns.append((similarity, p))

        scored_patterns.sort(
            key=lambda x: (x[0], x[1].get("sample_size", 0), x[1].get("expectancy", 0.0)),
            reverse=True,
        )
        return [item[1] for item in scored_patterns[:top_n]]


def get_score_band(score: float) -> str:
    if score < 50:
        return "<50"
    elif score < 65:
        return "50-64"
    elif score < 75:
        return "65-74"
    elif score < 85:
        return "75-84"
    elif score < 93:
        return "85-92"
    else:
        return "93+"


def format_patterns_for_prompt(patterns: list[dict[str, Any]]) -> str:
    if not patterns:
        return "No historical matching patterns found."
    lines = []
    for p in patterns:
        key = p.get("pattern_key", "unknown")
        n = p.get("sample_size", 0)
        wr = p.get("win_rate_pct", 0.0)
        exp = p.get("expectancy", 0.0)
        boost = "YES" if p.get("boost_candidate") else "NO"
        suppress = "YES" if p.get("suppression_candidate") else "NO"
        lines.append(
            f"- {key}: N={n}, WinRate={wr:.1f}%, Expectancy={exp:.2f} (Boost: {boost}, Suppress: {suppress})"
        )
    return "\n".join(lines)
