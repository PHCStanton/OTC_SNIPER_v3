"""
Journal Statistics & Knowledge Base Staging Service — OTC SNIPER v3

Provides deep quantitative analytics on ghost and live trading sessions:
  1. Liquidity & Volatility Bucket Aggregator (derived from ATR, tick frequency, ADX)
  2. Asset Manipulation Profiler (frequency, dominant types, clean vs manipulated WR)
  3. Favoured Regimes Ranker (6 market regimes classified into FAVOURED, NEUTRAL, AVOID)
  4. Adaptive Expiries Performance Analyzer (60s, 120s, 180s, 300s)
  5. AI Session Briefing & Advisory Generator
  6. User-Controlled Knowledge Base & Bayesian Prior Staging System
"""

from __future__ import annotations

import json
import logging
import math
import shutil
import time
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from ..config import RuntimeSettings, get_settings
from ..services.ai_service import get_ai_service
from ..models.ai_models import AIChatRequest, AIContext, AIMessage

# Import shared BayesianPriorStore and BayesianProtocolManager for atomic cross-process transactions
try:
    from shared.bayesian_prior_store import (
        BayesianPriorStore,
        PriorStoreError,
    )
    from shared.bayesian_protocol import (
        BayesianProtocolManager,
        ProtocolError,
        ProtocolValidationError,
        compute_protocol_health,
    )
except ImportError:
    import sys
    _root = Path(__file__).resolve().parents[3]
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from shared.bayesian_prior_store import (
        BayesianPriorStore,
        PriorStoreError,
    )
    from shared.bayesian_protocol import (
        BayesianProtocolManager,
        ProtocolError,
        ProtocolValidationError,
        compute_protocol_health,
    )

logger = logging.getLogger("otc_sniper.journal_stats_service")


def _get_score_band(score: float) -> str:
    """Map OTEO score to standardized score band."""
    if score < 65:
        return "<65"
    elif score < 75:
        return "65-74"
    elif score < 85:
        return "75-84"
    elif score < 93:
        return "85-92"
    else:
        return "93+"


def _get_z_band(z_score: Optional[float]) -> str:
    """Map Z-score to standardized z-band."""
    if z_score is None:
        return "UNKNOWN"
    try:
        zv = float(z_score)
        if zv < -1.5:
            return "<-1.5"
        elif zv < -0.5:
            return "-1.5_to_-0.5"
        elif zv <= 0.5:
            return "-0.5_to_0.5"
        elif zv <= 1.5:
            return "0.5_to_1.5"
        else:
            return ">1.5"
    except (ValueError, TypeError):
        return "UNKNOWN"


class JournalStatsService:
    """
    Core quantitative analytics engine for the Trading Journal and Ghost Journal.
    Computes statistical distributions and manages the staged Knowledge Base review workflow.
    """

    def __init__(self, settings: Optional[RuntimeSettings] = None) -> None:
        self.settings = settings or get_settings()
        self.stats_dir = self.settings.data_dir / "ghost_trades" / "stats"
        self.staged_updates_path = (
            self.stats_dir / "staged_knowledge_updates.json"
        )
        self.bayesian_priors_path = (
            self.stats_dir / "bayesian_priors.json"
        )
        self.kb_path = self._find_kb_path()
        self._ensure_staging_file()
        self.protocol_manager = BayesianProtocolManager(self.stats_dir)
        self._stats_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._cache_ttl_sec = 180.0  # 3 minutes in-memory cache

    def _find_kb_path(self) -> Path:
        """Find the condition_patterns.json knowledge base file path."""
        p1 = Path(__file__).resolve().parents[3] / "reports" / "analysis" / "knowledge_base" / "condition_patterns.json"
        if p1.exists():
            return p1
        p2 = Path("reports/analysis/knowledge_base/condition_patterns.json").resolve()
        if p2.exists():
            return p2
        return p1

    def _ensure_staging_file(self) -> None:
        """Create empty staging updates file if it does not exist."""
        try:
            self.staged_updates_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.staged_updates_path.exists():
                self.staged_updates_path.write_text(
                    json.dumps({"staged_reports": []}, indent=2), encoding="utf-8"
                )
        except Exception as e:
            logger.error("Failed to initialize staged updates file: %s", e)

    # --------------------------------------------------------------------------
    # Trade Log Parsing & Raw Aggregation
    # --------------------------------------------------------------------------

    def _load_trades_from_session_file(self, filepath: Path) -> List[Dict[str, Any]]:
        """Load valid JSON trade lines from a single JSONL session file."""
        if not filepath.exists():
            return []
        trades = []
        try:
            with filepath.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        trades.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error("Error reading trades from %s: %s", filepath.name, e)
        return trades

    def get_all_session_files(self, kind: str = "ghost") -> List[Path]:
        """Return list of session files sorted by modification time descending."""
        sessions_dir = self.settings.data_dir / f"{kind}_trades" / "sessions"
        if not sessions_dir.exists():
            return []
        files = list(sessions_dir.glob("*.jsonl"))
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files

    # --------------------------------------------------------------------------
    # Core Quantitative Calculations
    # --------------------------------------------------------------------------

    def compute_journal_stats(
        self,
        session_id: Optional[str] = None,
        kind: str = "ghost",
        min_trades: int = 0,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compute full statistical profile for a specific session or aggregated across all sessions.
        Optionally filters session files by date range (YYYY-MM-DD strings, inclusive).
        When date_from/date_to are provided the session_id filter is ignored (date range takes precedence).
        """
        cache_key = f"{kind}:{session_id or 'ALL'}:{min_trades}:{date_from or ''}:{date_to or ''}"
        now = time.time()
        if cache_key in self._stats_cache:
            cached_time, cached_data = self._stats_cache[cache_key]
            if now - cached_time < self._cache_ttl_sec:
                return cached_data

        # Parse date boundaries once
        _date_from: Optional[date] = None
        _date_to: Optional[date] = None
        if date_from:
            try:
                _date_from = date.fromisoformat(date_from)
            except ValueError:
                logger.warning("Invalid date_from value '%s' — ignoring.", date_from)
        if date_to:
            try:
                _date_to = date.fromisoformat(date_to)
            except ValueError:
                logger.warning("Invalid date_to value '%s' — ignoring.", date_to)

        def _file_in_date_range(f: Path) -> bool:
            """Return True if file mtime falls within [_date_from, _date_to] (inclusive)."""
            if _date_from is None and _date_to is None:
                return True
            file_date = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).date()
            if _date_from and file_date < _date_from:
                return False
            if _date_to and file_date > _date_to:
                return False
            return True

        is_all = (not session_id or session_id.strip().upper() == "ALL") or (_date_from is not None or _date_to is not None)
        trades: List[Dict[str, Any]] = []
        sessions_scanned = 0

        if is_all:
            session_files = self.get_all_session_files(kind)
            for f in session_files:
                if not _file_in_date_range(f):
                    continue
                file_trades = self._load_trades_from_session_file(f)
                if min_trades > 0 and len(file_trades) < min_trades:
                    continue
                trades.extend(file_trades)
                sessions_scanned += 1
        else:
            filepath = self.settings.data_dir / f"{kind}_trades" / "sessions" / f"{session_id}.jsonl"
            if not filepath.exists():
                candidates = list((self.settings.data_dir / f"{kind}_trades" / "sessions").glob(f"*{session_id}*"))
                if candidates:
                    filepath = candidates[0]
            if filepath.exists():
                trades = self._load_trades_from_session_file(filepath)
                sessions_scanned = 1

        stats = self._aggregate_trade_metrics(trades, session_id or "ALL", kind, sessions_scanned)
        self._stats_cache[cache_key] = (now, stats)
        return stats

    def _aggregate_trade_metrics(
        self,
        trades: List[Dict[str, Any]],
        session_id: str,
        kind: str,
        sessions_scanned: int,
    ) -> Dict[str, Any]:
        """Process list of trade records into structured analytical models."""
        total_trades = len(trades)
        wins = sum(1 for t in trades if str(t.get("outcome", "")).lower() == "win")
        losses = sum(1 for t in trades if str(t.get("outcome", "")).lower() == "loss")
        voids = sum(1 for t in trades if str(t.get("outcome", "")).lower() == "void")
        decided = wins + losses

        win_rate = round((wins / decided * 100.0), 1) if decided > 0 else 0.0

        total_profit = sum(float(t.get("profit") or 0.0) for t in trades)
        avg_profit = round(total_profit / total_trades, 2) if total_trades > 0 else 0.0

        gross_win = sum(float(t.get("profit") or 0.0) for t in trades if float(t.get("profit") or 0.0) > 0)
        gross_loss = abs(sum(float(t.get("profit") or 0.0) for t in trades if float(t.get("profit") or 0.0) < 0))
        profit_factor = round(gross_win / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0)

        # Expectancy = (Win% * AvgWin) - (Loss% * AvgLoss)
        avg_win = (gross_win / wins) if wins > 0 else 0.0
        avg_loss = (gross_loss / losses) if losses > 0 else 0.0
        expectancy = round(((wins / decided * avg_win) - (losses / decided * avg_loss)), 2) if decided > 0 else 0.0

        # 1. Volatility Buckets (derived from ATR and normalized bands)
        volatility_buckets = self._compute_volatility_buckets(trades)

        # 2. Liquidity Buckets (derived from tick_frequency)
        liquidity_buckets = self._compute_liquidity_buckets(trades)

        # 3. Asset Manipulation Profiler
        manipulation_stats = self._compute_manipulation_stats(trades)

        # 4. Favoured Regimes Ranking
        regimes_ranking = self._compute_regimes_ranking(trades)

        # 5. Adaptive Expiries Analyzer
        expiries_stats = self._compute_expiries_stats(trades)

        # 6. Candidate Knowledge Base Patterns & Bayesian Deltas
        candidate_patterns, bayesian_deltas = self._extract_knowledge_updates(trades)

        # Statistical significance check: at least 25 trades across >= 2 sessions or >= 30 in single session
        statistical_significance = (
            (total_trades >= 25 and sessions_scanned >= 2) or (total_trades >= 30 and sessions_scanned == 1)
        )

        return {
            "session_id": session_id,
            "kind": kind,
            "sessions_count": sessions_scanned,
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "voids": voids,
            "win_rate": win_rate,
            "total_profit": round(total_profit, 2),
            "avg_profit": avg_profit,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "statistical_significance": statistical_significance,
            "volatility": volatility_buckets,
            "liquidity": liquidity_buckets,
            "manipulation": manipulation_stats,
            "regimes": regimes_ranking,
            "expiries": expiries_stats,
            "candidate_patterns_count": len(candidate_patterns),
            "candidate_patterns": candidate_patterns[:50],  # top 50 candidates
            "bayesian_deltas": bayesian_deltas,
        }

    # --------------------------------------------------------------------------
    # Sub-Engine 1: Volatility Buckets
    # --------------------------------------------------------------------------

    def _compute_volatility_buckets(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Group trades by ATR volatility bands:
          - Ultra-Low: ATR < 0.0002
          - Optimal: 0.0002 <= ATR <= 0.0006
          - High: 0.0006 < ATR <= 0.0012
          - Extreme: ATR > 0.0012
        """
        bands = {
            "Ultra-Low (<0.0002)": {"trades": 0, "wins": 0, "losses": 0, "profit": 0.0, "key": "ultra_low"},
            "Optimal (0.0002-0.0006)": {"trades": 0, "wins": 0, "losses": 0, "profit": 0.0, "key": "optimal"},
            "High (0.0006-0.0012)": {"trades": 0, "wins": 0, "losses": 0, "profit": 0.0, "key": "high"},
            "Extreme (>0.0012)": {"trades": 0, "wins": 0, "losses": 0, "profit": 0.0, "key": "extreme"},
        }

        for t in trades:
            entry_ctx = t.get("entry_context") or {}
            market_ctx = entry_ctx.get("market_context") or {}
            
            atr_val = market_ctx.get("atr")
            if atr_val is None:
                atr_val = 0.00035

            try:
                atr = float(atr_val)
            except (ValueError, TypeError):
                atr = 0.00035

            if atr < 0.0002:
                band_name = "Ultra-Low (<0.0002)"
            elif atr <= 0.0006:
                band_name = "Optimal (0.0002-0.0006)"
            elif atr <= 0.0012:
                band_name = "High (0.0006-0.0012)"
            else:
                band_name = "Extreme (>0.0012)"

            outcome = str(t.get("outcome", "")).lower()
            profit = float(t.get("profit") or 0.0)

            bands[band_name]["trades"] += 1
            if outcome == "win":
                bands[band_name]["wins"] += 1
            elif outcome == "loss":
                bands[band_name]["losses"] += 1
            bands[band_name]["profit"] += profit

        formatted_bands = []
        best_band = None
        best_score = -999.0

        for name, data in bands.items():
            total = data["trades"]
            w = data["wins"]
            l = data["losses"]
            decided = w + l
            wr = round((w / decided * 100.0), 1) if decided > 0 else 0.0
            avg_p = round(data["profit"] / total, 2) if total > 0 else 0.0

            score = wr if total >= 3 else (wr * 0.5)
            if total >= 3 and score > best_score:
                best_score = score
                best_band = name

            formatted_bands.append({
                "band": name,
                "key": data["key"],
                "trades": total,
                "wins": w,
                "losses": l,
                "win_rate": wr,
                "total_profit": round(data["profit"], 2),
                "avg_profit": avg_p,
            })

        for b in formatted_bands:
            b["is_sweet_spot"] = (b["band"] == best_band)

        return {
            "bands": formatted_bands,
            "sweet_spot": best_band or "Optimal (0.0002-0.0006)",
        }

    # --------------------------------------------------------------------------
    # Sub-Engine 2: Liquidity Buckets
    # --------------------------------------------------------------------------

    def _compute_liquidity_buckets(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Group trades by tick frequency (ticks/min):
          - Low: < 80 ticks/min
          - Balanced: 80 - 150 ticks/min
          - High: > 150 ticks/min
        """
        bands = {
            "Low (<80/min)": {"trades": 0, "wins": 0, "losses": 0, "profit": 0.0, "key": "low"},
            "Balanced (80-150/min)": {"trades": 0, "wins": 0, "losses": 0, "profit": 0.0, "key": "balanced"},
            "High (>150/min)": {"trades": 0, "wins": 0, "losses": 0, "profit": 0.0, "key": "high"},
        }

        for t in trades:
            entry_ctx = t.get("entry_context") or {}
            market_ctx = entry_ctx.get("market_context") or {}
            
            tf_val = market_ctx.get("tick_frequency")
            if tf_val is None:
                tf_val = 110.0

            try:
                tf = float(tf_val)
            except (ValueError, TypeError):
                tf = 110.0

            if tf < 80.0:
                band_name = "Low (<80/min)"
            elif tf <= 150.0:
                band_name = "Balanced (80-150/min)"
            else:
                band_name = "High (>150/min)"

            outcome = str(t.get("outcome", "")).lower()
            profit = float(t.get("profit") or 0.0)

            bands[band_name]["trades"] += 1
            if outcome == "win":
                bands[band_name]["wins"] += 1
            elif outcome == "loss":
                bands[band_name]["losses"] += 1
            bands[band_name]["profit"] += profit

        formatted_bands = []
        best_band = None
        best_score = -999.0

        for name, data in bands.items():
            total = data["trades"]
            w = data["wins"]
            l = data["losses"]
            decided = w + l
            wr = round((w / decided * 100.0), 1) if decided > 0 else 0.0
            avg_p = round(data["profit"] / total, 2) if total > 0 else 0.0

            score = wr if total >= 3 else (wr * 0.5)
            if total >= 3 and score > best_score:
                best_score = score
                best_band = name

            formatted_bands.append({
                "band": name,
                "key": data["key"],
                "trades": total,
                "wins": w,
                "losses": l,
                "win_rate": wr,
                "total_profit": round(data["profit"], 2),
                "avg_profit": avg_p,
            })

        for b in formatted_bands:
            b["is_sweet_spot"] = (b["band"] == best_band)

        return {
            "bands": formatted_bands,
            "sweet_spot": best_band or "Balanced (80-150/min)",
        }

    # --------------------------------------------------------------------------
    # Sub-Engine 3: Asset Manipulation Profiler
    # --------------------------------------------------------------------------

    def _compute_manipulation_stats(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze manipulation impact across assets and identify hazardous assets.
        """
        asset_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total": 0,
            "manipulated": 0,
            "clean": 0,
            "clean_wins": 0,
            "clean_losses": 0,
            "manip_wins": 0,
            "manip_losses": 0,
            "type_counts": defaultdict(int),
        })

        total_manipulated = 0
        total_clean = 0
        manip_wins_global = 0
        manip_losses_global = 0
        clean_wins_global = 0
        clean_losses_global = 0

        for t in trades:
            asset = str(t.get("asset") or "UNKNOWN")
            entry_ctx = t.get("entry_context") or {}
            manip_entry = t.get("manipulation_at_entry") or entry_ctx.get("manipulation") or {}

            is_manip = False
            dominant_type = None

            if isinstance(manip_entry, dict) and manip_entry:
                is_manip = True
                dominant_type = max(manip_entry.keys(), key=lambda k: float(manip_entry[k] or 0.0))
            elif isinstance(manip_entry, str) and manip_entry.strip():
                is_manip = True
                dominant_type = manip_entry.strip()
            elif isinstance(manip_entry, list) and manip_entry:
                is_manip = True
                dominant_type = str(manip_entry[0])

            outcome = str(t.get("outcome", "")).lower()

            asset_stats[asset]["total"] += 1
            if is_manip:
                total_manipulated += 1
                asset_stats[asset]["manipulated"] += 1
                if dominant_type:
                    asset_stats[asset]["type_counts"][dominant_type] += 1
                if outcome == "win":
                    manip_wins_global += 1
                    asset_stats[asset]["manip_wins"] += 1
                elif outcome == "loss":
                    manip_losses_global += 1
                    asset_stats[asset]["manip_losses"] += 1
            else:
                total_clean += 1
                asset_stats[asset]["clean"] += 1
                if outcome == "win":
                    clean_wins_global += 1
                    asset_stats[asset]["clean_wins"] += 1
                elif outcome == "loss":
                    clean_losses_global += 1
                    asset_stats[asset]["clean_losses"] += 1

        leaderboard = []
        for asset, s in asset_stats.items():
            tot = s["total"]
            manip_cnt = s["manipulated"]
            clean_cnt = s["clean"]
            freq_pct = round((manip_cnt / tot * 100.0), 1) if tot > 0 else 0.0

            clean_decided = s["clean_wins"] + s["clean_losses"]
            clean_wr = round((s["clean_wins"] / clean_decided * 100.0), 1) if clean_decided > 0 else 0.0

            manip_decided = s["manip_wins"] + s["manip_losses"]
            manip_wr = round((s["manip_wins"] / manip_decided * 100.0), 1) if manip_decided > 0 else 0.0

            dominant = "None"
            if s["type_counts"]:
                dominant = max(s["type_counts"].items(), key=lambda x: x[1])[0]

            if freq_pct >= 25.0:
                danger_level = "HIGH"
            elif freq_pct >= 10.0:
                danger_level = "MODERATE"
            else:
                danger_level = "LOW"

            leaderboard.append({
                "asset": asset,
                "total_trades": tot,
                "manipulated_trades": manip_cnt,
                "clean_trades": clean_cnt,
                "manipulation_freq_pct": freq_pct,
                "clean_win_rate": clean_wr,
                "manipulated_win_rate": manip_wr,
                "dominant_manipulation_type": dominant,
                "danger_level": danger_level,
                "type_breakdown": dict(s["type_counts"]),
            })

        leaderboard.sort(key=lambda a: (a["manipulation_freq_pct"], a["total_trades"]), reverse=True)

        clean_decided_global = clean_wins_global + clean_losses_global
        clean_wr_global = round((clean_wins_global / clean_decided_global * 100.0), 1) if clean_decided_global > 0 else 0.0

        manip_decided_global = manip_wins_global + manip_losses_global
        manip_wr_global = round((manip_wins_global / manip_decided_global * 100.0), 1) if manip_decided_global > 0 else 0.0

        return {
            "total_clean_trades": total_clean,
            "total_manipulated_trades": total_manipulated,
            "global_clean_win_rate": clean_wr_global,
            "global_manipulated_win_rate": manip_wr_global,
            "leaderboard": leaderboard,
        }

    # --------------------------------------------------------------------------
    # Sub-Engine 4: Favoured Regimes Ranking
    # --------------------------------------------------------------------------

    def _compute_regimes_ranking(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Compute win rates, PnL, and profit factors for all 6 market regimes.
        Classifies each into FAVOURED (>=58%), NEUTRAL (50-58%), or AVOID (<50%).
        """
        all_regimes = [
            "RANGE_BOUND",
            "TREND_REVERSAL",
            "TREND_PULLBACK",
            "STRONG_MOMENTUM",
            "BREAKOUT",
            "CHOPPY",
        ]

        regime_data: Dict[str, Dict[str, Any]] = {
            r: {"trades": 0, "wins": 0, "losses": 0, "profit": 0.0, "gross_win": 0.0, "gross_loss": 0.0}
            for r in all_regimes
        }
        regime_data["UNKNOWN"] = {"trades": 0, "wins": 0, "losses": 0, "profit": 0.0, "gross_win": 0.0, "gross_loss": 0.0}

        for t in trades:
            entry_ctx = t.get("entry_context") or {}
            regime = str(entry_ctx.get("regime_label") or entry_ctx.get("regime") or "UNKNOWN").upper().strip()
            if regime not in regime_data:
                regime_data[regime] = {"trades": 0, "wins": 0, "losses": 0, "profit": 0.0, "gross_win": 0.0, "gross_loss": 0.0}

            outcome = str(t.get("outcome", "")).lower()
            profit = float(t.get("profit") or 0.0)

            regime_data[regime]["trades"] += 1
            if outcome == "win":
                regime_data[regime]["wins"] += 1
                if profit > 0:
                    regime_data[regime]["gross_win"] += profit
            elif outcome == "loss":
                regime_data[regime]["losses"] += 1
                if profit < 0:
                    regime_data[regime]["gross_loss"] += abs(profit)
            regime_data[regime]["profit"] += profit

        ranking = []
        for regime, d in regime_data.items():
            tot = d["trades"]
            if tot == 0 and regime == "UNKNOWN":
                continue

            w = d["wins"]
            l = d["losses"]
            decided = w + l
            wr = round((w / decided * 100.0), 1) if decided > 0 else 0.0
            pnl = round(d["profit"], 2)

            gw = d["gross_win"]
            gl = d["gross_loss"]
            pf = round(gw / gl, 2) if gl > 0 else (99.0 if gw > 0 else 0.0)

            if wr >= 58.0 and tot >= 2:
                classification = "FAVOURED"
                badge_color = "emerald"
            elif wr >= 50.0 or tot < 2:
                classification = "NEUTRAL"
                badge_color = "amber"
            else:
                classification = "AVOID"
                badge_color = "rose"

            ranking.append({
                "regime": regime,
                "trades": tot,
                "wins": w,
                "losses": l,
                "win_rate": wr,
                "net_profit": pnl,
                "profit_factor": pf,
                "classification": classification,
                "badge_color": badge_color,
            })

        ranking.sort(key=lambda r: (r["win_rate"], r["trades"]), reverse=True)
        return ranking

    # --------------------------------------------------------------------------
    # Sub-Engine 5: Adaptive Expiries Performance
    # --------------------------------------------------------------------------

    def _compute_expiries_stats(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze performance across expiration durations (60s, 120s, 180s, 300s, etc.).
        """
        exp_data: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
            "trades": 0, "wins": 0, "losses": 0, "profit": 0.0
        })

        for t in trades:
            exp_sec = t.get("expiration_seconds")
            if exp_sec is None:
                exp_sec = 60
            try:
                exp_sec = int(exp_sec)
            except (ValueError, TypeError):
                exp_sec = 60

            outcome = str(t.get("outcome", "")).lower()
            profit = float(t.get("profit") or 0.0)

            exp_data[exp_sec]["trades"] += 1
            if outcome == "win":
                exp_data[exp_sec]["wins"] += 1
            elif outcome == "loss":
                exp_data[exp_sec]["losses"] += 1
            exp_data[exp_sec]["profit"] += profit

        formatted_expiries = []
        best_duration = None
        best_score = -999.0

        for duration, d in sorted(exp_data.items(), key=lambda x: x[0]):
            tot = d["trades"]
            w = d["wins"]
            l = d["losses"]
            decided = w + l
            wr = round((w / decided * 100.0), 1) if decided > 0 else 0.0
            avg_p = round(d["profit"] / tot, 2) if tot > 0 else 0.0

            mins = duration // 60
            secs = duration % 60
            label = f"{mins}m" if secs == 0 else f"{duration}s"

            score = wr if tot >= 3 else (wr * 0.5)
            if tot >= 3 and score > best_score:
                best_score = score
                best_duration = duration

            formatted_expiries.append({
                "duration_seconds": duration,
                "label": label,
                "trades": tot,
                "wins": w,
                "losses": l,
                "win_rate": wr,
                "total_profit": round(d["profit"], 2),
                "avg_profit": avg_p,
            })

        for e in formatted_expiries:
            e["is_best"] = (e["duration_seconds"] == best_duration)

        return {
            "expiries": formatted_expiries,
            "best_duration": best_duration or 60,
        }

    # --------------------------------------------------------------------------
    # Sub-Engine 6: Candidate Patterns & Bayesian Feature Deltas Extraction
    # --------------------------------------------------------------------------

    def _extract_knowledge_updates(
        self, trades: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Extract candidate condition patterns (for condition_patterns.json) and
        Bayesian prior feature deltas (for bayesian_priors.json).
        """
        pattern_groups: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "asset": "",
            "strategy_level": "level3",
            "oteo_score_band": "",
            "regime_label": "",
            "direction": "",
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "profit": 0.0,
        })

        bayesian_deltas: Dict[str, Dict[str, int]] = defaultdict(lambda: {"win": 0, "loss": 0})
        bayesian_total_wins = 0
        bayesian_total_losses = 0

        bayesian_deltas_300: Dict[str, Dict[str, int]] = defaultdict(lambda: {"win": 0, "loss": 0})
        bayesian_total_wins_300 = 0
        bayesian_total_losses_300 = 0

        for t in trades:
            asset = str(t.get("asset") or "UNKNOWN")
            strategy_level = str(t.get("strategy_level") or "level3")
            direction = str(t.get("direction") or "CALL").upper()
            outcome = str(t.get("outcome", "")).lower()
            is_win = (outcome == "win")
            is_loss = (outcome == "loss")
            profit = float(t.get("profit") or 0.0)

            oteo_score = float(t.get("oteo_score") or 50.0)
            score_band = _get_score_band(oteo_score)

            entry_ctx = t.get("entry_context") or {}
            regime = str(entry_ctx.get("regime_label") or entry_ctx.get("regime") or "UNKNOWN").upper().strip()
            confidence = str(t.get("confidence") or entry_ctx.get("confidence") or "MEDIUM").upper().strip()

            z_score = entry_ctx.get("z_score")
            z_band = _get_z_band(z_score)

            manip = entry_ctx.get("manipulation") or t.get("manipulation_at_entry")
            has_manip = "MANIP_TRUE" if (isinstance(manip, (dict, list, bool)) and bool(manip)) else "MANIP_FALSE"

            # 1. Observational candidate patterns include all session trades
            pkey = f"{asset}|{strategy_level}|{score_band}|{regime}|{direction}"
            pg = pattern_groups[pkey]
            pg["pattern_key"] = pkey
            pg["asset"] = asset
            pg["strategy_level"] = strategy_level
            pg["oteo_score_band"] = score_band
            pg["regime_label"] = regime
            pg["direction"] = direction
            pg["trades"] += 1
            if is_win:
                pg["wins"] += 1
            elif is_loss:
                pg["losses"] += 1
            pg["profit"] += profit

            # 2. Bayesian Prior Deltas separated by horizon (60s and 300s)
            exp_sec = t.get("expiration_seconds")
            if exp_sec is None and isinstance(entry_ctx, dict):
                exp_sec = entry_ctx.get("expiration_seconds")
            try:
                exp_int = int(exp_sec) if exp_sec is not None else 60
            except (ValueError, TypeError):
                exp_int = 60

            bucket = "win" if is_win else ("loss" if is_loss else None)

            if exp_int == 60:
                if is_win:
                    bayesian_total_wins += 1
                elif is_loss:
                    bayesian_total_losses += 1

                if bucket:
                    bayesian_deltas[f"oteo_band={score_band}"][bucket] += 1
                    bayesian_deltas[f"regime={regime}"][bucket] += 1
                    bayesian_deltas[f"confidence={confidence}"][bucket] += 1
                    bayesian_deltas[f"z_band={z_band}"][bucket] += 1
                    bayesian_deltas[f"has_manip={has_manip}"][bucket] += 1
                    bayesian_deltas[f"direction={direction}"][bucket] += 1
            elif exp_int == 300:
                if is_win:
                    bayesian_total_wins_300 += 1
                elif is_loss:
                    bayesian_total_losses_300 += 1

                if bucket:
                    bayesian_deltas_300[f"oteo_band={score_band}"][bucket] += 1
                    bayesian_deltas_300[f"regime={regime}"][bucket] += 1
                    bayesian_deltas_300[f"confidence={confidence}"][bucket] += 1
                    bayesian_deltas_300[f"z_band={z_band}"][bucket] += 1
                    bayesian_deltas_300[f"has_manip={has_manip}"][bucket] += 1
                    bayesian_deltas_300[f"direction={direction}"][bucket] += 1

        candidate_patterns = []
        for pkey, pg in pattern_groups.items():
            n = pg["trades"]
            w = pg["wins"]
            decided = w + pg["losses"]
            wr = round((w / decided * 100.0), 1) if decided > 0 else 0.0
            net = round(pg["profit"], 2)
            exp = round(net / n, 2) if n > 0 else 0.0

            if n >= 20:
                tier = "HIGH"
            elif n >= 10:
                tier = "MEDIUM"
            elif n >= 5:
                tier = "LOW"
            else:
                tier = "VERY_LOW"

            candidate_patterns.append({
                "pattern_key": pkey,
                "asset": pg["asset"],
                "strategy_level": pg["strategy_level"],
                "oteo_score_band": pg["oteo_score_band"],
                "regime_label": pg["regime_label"],
                "direction": pg["direction"],
                "sample_size": n,
                "win_rate_pct": wr,
                "expectancy": exp,
                "net_profit": net,
                "confidence_tier": tier,
                "suppression_candidate": (wr < 48.0 and n >= 5),
                "boost_candidate": (wr >= 60.0 and n >= 5),
            })

        candidate_patterns.sort(key=lambda p: (p["sample_size"], p["win_rate_pct"]), reverse=True)

        bayesian_summary_60s = {
            "total_wins_delta": bayesian_total_wins,
            "total_losses_delta": bayesian_total_losses,
            "total_trades_delta": bayesian_total_wins + bayesian_total_losses,
            "feature_deltas": dict(bayesian_deltas),
        }

        bayesian_summary_300s = {
            "total_wins_delta": bayesian_total_wins_300,
            "total_losses_delta": bayesian_total_losses_300,
            "total_trades_delta": bayesian_total_wins_300 + bayesian_total_losses_300,
            "feature_deltas": dict(bayesian_deltas_300),
        }

        bayesian_summary = {
            "total_wins_delta": bayesian_total_wins,
            "total_losses_delta": bayesian_total_losses,
            "total_trades_delta": bayesian_total_wins + bayesian_total_losses,
            "feature_deltas": dict(bayesian_deltas),
            "bayesian_deltas_60s": bayesian_summary_60s,
            "bayesian_deltas_300s": bayesian_summary_300s,
        }

        return candidate_patterns, bayesian_summary

    # --------------------------------------------------------------------------
    # AI Briefing & Strategic Advisory Generator
    # --------------------------------------------------------------------------

    async def generate_ai_brief_report(
        self,
        session_id: Optional[str] = None,
        kind: str = "ghost",
    ) -> Dict[str, Any]:
        """
        Generate comprehensive AI session executive briefing and strategic recommendations.
        """
        stats = self.compute_journal_stats(session_id, kind)
        ai_service = get_ai_service()

        session_label = session_id if (session_id and session_id.upper() != "ALL") else f"Aggregated Multi-Session ({stats['sessions_count']} sessions)"

        top_manip = stats["manipulation"]["leaderboard"][:3]
        manip_summary = ", ".join(f"{m['asset']} ({m['manipulation_freq_pct']}%, Danger: {m['danger_level']})" for m in top_manip) if top_manip else "None"

        favoured_regimes = [r["regime"] for r in stats["regimes"] if r["classification"] == "FAVOURED"]
        avoid_regimes = [r["regime"] for r in stats["regimes"] if r["classification"] == "AVOID"]

        sweet_vol = stats["volatility"]["sweet_spot"]
        sweet_liq = stats["liquidity"]["sweet_spot"]

        prompt = f"""You are an elite quantitative trading psychologist and OTC microstructure strategist.
Review the following trading session analytics and produce an Executive Session Briefing & Advisory.

Session Context:
  Session: {session_label} (Kind: {kind.upper()})
  Total Trades: {stats['total_trades']} ({stats['wins']} Wins / {stats['losses']} Losses)
  Win Rate: {stats['win_rate']}% | Profit Factor: {stats['profit_factor']} | Net PnL: ${stats['total_profit']}
  Expectancy per Trade: ${stats['expectancy']}
  Statistical Significance: {'SUFFICIENT (N >= 25)' if stats['statistical_significance'] else 'INSUFFICIENT SAMPLE (< 25 trades)'}

Microstructure Metrics:
  Optimal Volatility Sweet Spot: {sweet_vol}
  Optimal Liquidity Sweet Spot: {sweet_liq}
  Worst Asset Manipulation Traps: {manip_summary}
  Favoured Market Regimes: {', '.join(favoured_regimes) if favoured_regimes else 'None'}
  High-Risk / Avoid Regimes: {', '.join(avoid_regimes) if avoid_regimes else 'None'}
  Best Expiration Duration: {stats['expiries']['best_duration']}s

Please generate a structured, professional report in Markdown with the following exact 4 sections:
### 1. Key Observations & Structural Edges
(Highlight what worked exceptionally well, identifying high-probability confluence sweet spots)

### 2. Vulnerabilities & Manipulation Traps
(Detail where losses concentrated, hazardous assets to avoid or tighten, and worst regime conditions)

### 3. Actionable Advisory for Future Sessions
(Provide concrete parameters: recommended Auto-Ghost regime whitelists, Z-score gate adjustments, and expiry suggestions)

### 4. Knowledge Base & Bayesian Staging Recommendation
(State whether the statistical evidence is strong enough to stage updates into condition_patterns.json and bayesian_priors.json)

Keep the language direct, authoritative, and concise (under 250 words total).
""".strip()

        try:
            req = AIChatRequest(
                messages=[AIMessage(role="user", content=prompt)],
                context=AIContext(
                    active_asset=top_manip[0]["asset"] if top_manip else "EURUSD_otc",
                    strategy_level="level3",
                ),
            )
            resp = await ai_service.chat(req)
            report_text = resp.reply if resp and resp.reply else "AI briefing generator returned an empty response."
        except Exception as e:
            logger.error("AI briefing generation error: %s", e, exc_info=True)
            report_text = f"AI Briefing generated fallback summary:\n\nSession Win Rate: {stats['win_rate']}%, Net Profit: ${stats['total_profit']}. Sweet spots: Volatility={sweet_vol}, Liquidity={sweet_liq}. Favoured Regimes: {', '.join(favoured_regimes)}."

        voice_script = f"Session report: Win rate {stats['win_rate']} percent across {stats['total_trades']} trades, net profit {stats['total_profit']} dollars. Optimal volatility sweet spot was {sweet_vol}. Favoured regimes: {', '.join(favoured_regimes) if favoured_regimes else 'Range bound'}. Check the staging review panel for knowledge base updates."

        return {
            "session_id": session_id or "ALL",
            "kind": kind,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "report": report_text,
            "voice_script": voice_script,
            "stats_summary": {
                "total_trades": stats["total_trades"],
                "win_rate": stats["win_rate"],
                "net_profit": stats["total_profit"],
                "profit_factor": stats["profit_factor"],
                "sweet_spot_volatility": sweet_vol,
                "sweet_spot_liquidity": sweet_liq,
                "favoured_regimes": favoured_regimes,
                "avoid_regimes": avoid_regimes,
            },
            "candidate_patterns_count": stats["candidate_patterns_count"],
            "statistical_significance": stats["statistical_significance"],
        }

    # --------------------------------------------------------------------------
    # Staging Review & Transactional Commit
    # --------------------------------------------------------------------------

    def get_staged_reports(self) -> List[Dict[str, Any]]:
        """Retrieve all currently staged reports pending review."""
        try:
            if self.staged_updates_path.exists():
                data = json.loads(self.staged_updates_path.read_text(encoding="utf-8"))
                return data.get("staged_reports", [])
        except Exception as e:
            logger.error("Failed to load staged reports: %s", e)
        return []

    def stage_session_report(
        self,
        session_id: Optional[str] = None,
        kind: str = "ghost",
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Package a session analysis report into the Staging Review area for user review.
        """
        stats = self.compute_journal_stats(session_id, kind)
        staged_id = f"staged_{int(time.time())}_{session_id or 'all'}"

        staged_entry = {
            "staged_id": staged_id,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id or "ALL",
            "kind": kind,
            "status": "PENDING_REVIEW",
            "user_notes": notes,
            "sessions_count": stats["sessions_count"],
            "total_trades": stats["total_trades"],
            "win_rate": stats["win_rate"],
            "net_profit": stats["total_profit"],
            "statistical_significance": stats["statistical_significance"],
            "candidate_patterns": stats["candidate_patterns"],
            "bayesian_deltas": stats["bayesian_deltas"],
            "sweet_spot_volatility": stats["volatility"]["sweet_spot"],
            "sweet_spot_liquidity": stats["liquidity"]["sweet_spot"],
        }

        try:
            reports = self.get_staged_reports()
            reports = [r for r in reports if r.get("staged_id") != staged_id]
            reports.insert(0, staged_entry)

            self.staged_updates_path.write_text(
                json.dumps({"staged_reports": reports}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info("Successfully staged report %s for review.", staged_id)
            return staged_entry
        except Exception as e:
            logger.error("Failed to save staged report: %s", e)
            raise

    def delete_staged_report(self, staged_id: str) -> bool:
        """Delete a staged report from the review queue."""
        try:
            reports = self.get_staged_reports()
            new_reports = [r for r in reports if r.get("staged_id") != staged_id]
            self.staged_updates_path.write_text(
                json.dumps({"staged_reports": new_reports}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return True
        except Exception as e:
            logger.error("Failed to delete staged report %s: %s", staged_id, e)
            return False

    def commit_staged_to_knowledge_base(
        self,
        staged_id: str,
        selected_pattern_keys: Optional[List[str]] = None,
        commit_bayesian: bool = True,
        commit_kb: bool = True,
    ) -> Dict[str, Any]:
        """
        User-approved transactional commit of staged patterns and Bayesian prior updates.
        AUTOMATICALLY creates timestamped backups before writing anything.
        """
        reports = self.get_staged_reports()
        matched = next((r for r in reports if r.get("staged_id") == staged_id), None)
        if not matched:
            raise ValueError(f"Staged report {staged_id} not found.")

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_files = []

        # 1. Backup existing files
        if commit_bayesian and self.bayesian_priors_path.exists():
            bak_path = self.bayesian_priors_path.parent / f"bayesian_priors_{timestamp_str}.json.bak"
            shutil.copy2(self.bayesian_priors_path, bak_path)
            backup_files.append(str(bak_path.name))
            logger.info("Created backup of bayesian_priors.json at %s", bak_path)

        if commit_kb and self.kb_path.exists():
            bak_kb_path = self.kb_path.parent / f"condition_patterns_{timestamp_str}.json.bak"
            shutil.copy2(self.kb_path, bak_kb_path)
            backup_files.append(str(bak_kb_path.name))
            logger.info("Created backup of condition_patterns.json at %s", bak_kb_path)

        committed_patterns_count = 0
        bayesian_committed = False

        # 2. Apply Bayesian Priors Update (Transactional via BayesianPriorStore)
        if commit_bayesian:
            b_deltas = matched.get("bayesian_deltas") or {}
            feature_deltas = b_deltas.get("feature_deltas", {})
            wins_delta = int(b_deltas.get("total_wins_delta", 0))
            losses_delta = int(b_deltas.get("total_losses_delta", 0))

            if wins_delta + losses_delta > 0:
                store = BayesianPriorStore(self.bayesian_priors_path)
                def _apply_deltas(current_priors: Dict[str, Any]) -> Dict[str, Any]:
                    cur_wins = current_priors.get("total_wins", 0) + wins_delta
                    cur_losses = current_priors.get("total_losses", 0) + losses_delta
                    fc = current_priors.get("feature_counts", {}) or {}
                    
                    for fkey, counts in feature_deltas.items():
                        if fkey not in fc:
                            fc[fkey] = {"win": 0, "loss": 0}
                        fc[fkey]["win"] = fc[fkey].get("win", 0) + counts.get("win", 0)
                        fc[fkey]["loss"] = fc[fkey].get("loss", 0) + counts.get("loss", 0)

                    return {
                        "total_wins": cur_wins,
                        "total_losses": cur_losses,
                        "total_trades": cur_wins + cur_losses,
                        "feature_counts": fc,
                    }

                store.mutate(_apply_deltas)
                bayesian_committed = True
                logger.info("Committed %d wins and %d losses to Bayesian priors.", wins_delta, losses_delta)

        # 3. Apply Knowledge Base Condition Patterns Update
        if commit_kb:
            candidates = matched.get("candidate_patterns") or []
            if selected_pattern_keys:
                allowed_keys = set(selected_pattern_keys)
                candidates = [c for c in candidates if c.get("pattern_key") in allowed_keys]

            if candidates:
                kb_data = {"metadata": {"total_patterns": 0, "generated_utc": ""}, "patterns": []}
                if self.kb_path.exists():
                    try:
                        kb_data = json.loads(self.kb_path.read_text(encoding="utf-8"))
                    except Exception as e:
                        logger.error("Error reading existing condition_patterns.json: %s", e)

                existing_patterns: List[Dict[str, Any]] = kb_data.get("patterns", [])
                patterns_by_key = {p.get("pattern_key"): p for p in existing_patterns if p.get("pattern_key")}

                for cand in candidates:
                    pkey = cand["pattern_key"]
                    if pkey in patterns_by_key:
                        ex = patterns_by_key[pkey]
                        n_old = ex.get("sample_size", 0)
                        n_new = cand.get("sample_size", 0)
                        total_n = n_old + n_new

                        if total_n > 0:
                            old_wr = ex.get("win_rate_pct", 0.0)
                            new_wr = cand.get("win_rate_pct", 0.0)
                            combined_wr = round(((old_wr * n_old) + (new_wr * n_new)) / total_n, 1)
                            combined_profit = round(ex.get("net_profit", 0.0) + cand.get("net_profit", 0.0), 2)
                            combined_exp = round(combined_profit / total_n, 2)

                            ex["sample_size"] = total_n
                            ex["win_rate_pct"] = combined_wr
                            ex["net_profit"] = combined_profit
                            ex["expectancy"] = combined_exp
                            ex["confidence_tier"] = (
                                "HIGH" if total_n >= 20 else ("MEDIUM" if total_n >= 10 else ("LOW" if total_n >= 5 else "VERY_LOW"))
                            )
                            ex["suppression_candidate"] = (combined_wr < 48.0 and total_n >= 5)
                            ex["boost_candidate"] = (combined_wr >= 60.0 and total_n >= 5)
                    else:
                        existing_patterns.append(cand)
                        patterns_by_key[pkey] = cand

                    committed_patterns_count += 1

                kb_data["metadata"]["total_patterns"] = len(existing_patterns)
                kb_data["metadata"]["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                kb_data["patterns"] = existing_patterns

                self.kb_path.parent.mkdir(parents=True, exist_ok=True)
                self.kb_path.write_text(json.dumps(kb_data, indent=2, ensure_ascii=False), encoding="utf-8")
                logger.info("Committed %d condition patterns to %s.", committed_patterns_count, self.kb_path)

        # 4. Mark Staged Report as COMMITTED
        matched["status"] = "COMMITTED"
        matched["committed_utc"] = datetime.now(timezone.utc).isoformat()
        matched["backups_created"] = backup_files
        self.staged_updates_path.write_text(
            json.dumps({"staged_reports": reports}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return {
            "success": True,
            "staged_id": staged_id,
            "status": "COMMITTED",
            "backups": backup_files,
            "bayesian_committed": bayesian_committed,
            "patterns_committed": committed_patterns_count,
            "message": f"Successfully committed updates with {len(backup_files)} automated backup(s) created.",
        }

    # --------------------------------------------------------------------------
    # Bayesian Protocol Management (Library & Active State)
    # --------------------------------------------------------------------------

    def list_protocols(self) -> List[Dict[str, Any]]:
        """List all saved protocol snapshots."""
        return self.protocol_manager.list_protocols()

    def get_protocol(self, proto_id: str) -> Optional[Dict[str, Any]]:
        """Get full details of a specific protocol snapshot."""
        return self.protocol_manager.get_protocol(proto_id)

    def save_protocol_from_staged(
        self,
        staged_id: str,
        name: str = "",
        notes: str = "",
        horizon_seconds: int = 60,
    ) -> Dict[str, Any]:
        """Save a staged report into the protocol library as a named snapshot."""
        reports = self.get_staged_reports()
        matched = next((r for r in reports if r.get("staged_id") == staged_id), None)
        if not matched:
            raise ValueError(f"Staged report {staged_id} not found.")

        all_b_deltas = matched.get("bayesian_deltas") or {}
        if horizon_seconds == 300 and "bayesian_deltas_300s" in all_b_deltas:
            b_deltas = all_b_deltas["bayesian_deltas_300s"]
        elif horizon_seconds == 60 and "bayesian_deltas_60s" in all_b_deltas:
            b_deltas = all_b_deltas["bayesian_deltas_60s"]
        else:
            b_deltas = all_b_deltas

        tw = int(b_deltas.get("total_wins_delta", 0))
        tl = int(b_deltas.get("total_losses_delta", 0))
        session_id = matched.get("session_id", "staged_session")

        proto_dict = {
            "schema_version": 1,
            "id": f"proto_{staged_id}_{horizon_seconds}s",
            "name": name or f"Protocol: {session_id} ({horizon_seconds}s)",
            "horizon_seconds": horizon_seconds,
            "source_sessions": [session_id] if session_id != "ALL" else [],
            "trade_count": tw + tl,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "notes": notes or matched.get("user_notes", ""),
            "priors": {
                "total_wins": tw,
                "total_losses": tl,
                "total_trades": tw + tl,
                "feature_counts": b_deltas.get("feature_deltas", {}),
            },
            "patterns": matched.get("candidate_patterns", []),
            "gates": {"min_win_probability": 0.55},
        }
        return self.protocol_manager.save_protocol(proto_dict)

    def import_protocol(self, raw_content: str | bytes) -> Dict[str, Any]:
        """Import a protocol from raw JSON or legacy export bundle."""
        return self.protocol_manager.import_from_json(raw_content)

    def activate_protocol(self, proto_id: str, allow_experimental: bool = True) -> Dict[str, Any]:
        """Activate a protocol by ID into the live working copy."""
        return self.protocol_manager.activate_protocol(proto_id, allow_experimental=allow_experimental)

    def delete_protocol(self, proto_id: str) -> bool:
        """Delete a protocol snapshot from the library."""
        return self.protocol_manager.delete_protocol(proto_id)

    def get_active_protocol(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently active protocol."""
        return self.protocol_manager.get_active_protocol_info()


_journal_stats_service: Optional[JournalStatsService] = None

def get_journal_stats_service() -> JournalStatsService:
    global _journal_stats_service
    if _journal_stats_service is None:
        _journal_stats_service = JournalStatsService()
    return _journal_stats_service
