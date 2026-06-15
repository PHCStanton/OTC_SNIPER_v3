"""Service layer for parsing session logs, running Grok analysis, and managing pattern memory."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..config import RuntimeSettings, get_settings
from ..services.ai_service import get_ai_service
from ..models.ai_models import AIChatRequest, AIContext, AIMessage

logger = logging.getLogger("otc_sniper.analysis_service")

class AnalysisService:
    def __init__(self, settings: RuntimeSettings | None = None) -> None:
        self.settings = settings or get_settings()
        self.pattern_memory_path = self.settings.data_dir / "settings" / "ai_pattern_memory.json"
        self._ensure_pattern_memory_file()

    def _ensure_pattern_memory_file(self) -> None:
        """Create empty pattern memory file if it does not exist."""
        try:
            self.pattern_memory_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.pattern_memory_path.exists():
                self.pattern_memory_path.write_text(json.dumps([], indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to initialize pattern memory file: %s", e)

    def load_patterns(self) -> List[Dict[str, Any]]:
        """Load saved market patterns from memory."""
        try:
            if self.pattern_memory_path.exists():
                return json.loads(self.pattern_memory_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Error loading patterns: %s", e)
        return []

    def save_pattern(self, pattern: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Save a new pattern to the persistent pattern memory database."""
        try:
            patterns = self.load_patterns()
            # Ensure unique pattern
            if "id" not in pattern:
                pattern["id"] = f"pat_{int(time.time())}"
            pattern["timestamp"] = datetime.utcnow().isoformat()
            
            # Remove existing pattern with same ID if present
            patterns = [p for p in patterns if p.get("id") != pattern["id"]]
            patterns.append(pattern)
            
            self.pattern_memory_path.write_text(json.dumps(patterns, indent=2, ensure_ascii=False), encoding="utf-8")
            return patterns
        except Exception as e:
            logger.error("Error saving pattern: %s", e)
            return []

    def parse_session_file(self, filepath: Path, kind: str) -> Dict[str, Any] | None:
        """Parse a single JSONL session file to calculate summary statistics."""
        if not filepath.exists():
            return None

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
            logger.error("Failed to read session file %s: %s", filepath.name, e)
            return None

        if not trades:
            return None

        wins = sum(1 for t in trades if str(t.get("outcome", "")).lower() == "win")
        losses = sum(1 for t in trades if str(t.get("outcome", "")).lower() == "loss")
        voids = sum(1 for t in trades if str(t.get("outcome", "")).lower() == "void")
        total_trades = len(trades)
        
        profit = 0.0
        for t in trades:
            p = t.get("profit")
            profit += float(p) if p is not None else 0.0

        win_rate = (wins / (wins + losses)) * 100.0 if (wins + losses) > 0 else 0.0

        timestamps = [float(t.get("timestamp", 0.0)) for t in trades if t.get("timestamp")]
        start_time = min(timestamps) if timestamps else filepath.stat().st_mtime
        end_time = max(timestamps) if timestamps else filepath.stat().st_mtime

        assets = list(set(t.get("asset") for t in trades if t.get("asset")))
        strategies = list(set(t.get("strategy_level") for t in trades if t.get("strategy_level")))

        # Compute regimes and avg z_score for filtering / optimal z analysis
        regimes = set()
        z_scores = []
        for t in trades:
            entry = t.get("entry_context") or {}
            r = entry.get("regime_label") or entry.get("regime") or "unknown"
            regimes.add(r)
            try:
                z = float(entry.get("z_score", 0) or 0)
                z_scores.append(z)
            except (ValueError, TypeError):
                pass
        avg_z = round(sum(z_scores) / len(z_scores), 2) if z_scores else 0.0

        return {
            "session_id": filepath.stem,
            "kind": kind,
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "voids": voids,
            "profit": profit,
            "win_rate": win_rate,
            "start_time": start_time,
            "end_time": end_time,
            "assets": assets,
            "strategy_levels": strategies,
            "regimes": list(regimes),
            "avg_z_score": avg_z,
            "trades": trades,
        }

    def get_all_sessions(self) -> Dict[str, Any]:
        """Load all ghost and live trading sessions and calculate stats."""
        ghost_sessions_dir = self.settings.data_dir / "ghost_trades" / "sessions"
        live_sessions_dir = self.settings.data_dir / "live_trades" / "sessions"

        ghost_sessions = []
        live_sessions = []

        if ghost_sessions_dir.exists():
            for filepath in ghost_sessions_dir.glob("*.jsonl"):
                stats = self.parse_session_file(filepath, "ghost")
                if stats:
                    ghost_sessions.append(stats)

        if live_sessions_dir.exists():
            for filepath in live_sessions_dir.glob("*.jsonl"):
                stats = self.parse_session_file(filepath, "live")
                if stats:
                    live_sessions.append(stats)

        # Sort by start time descending
        ghost_sessions.sort(key=lambda s: s["start_time"], reverse=True)
        live_sessions.sort(key=lambda s: s["start_time"], reverse=True)

        # Generate and save daily stats summaries
        self.update_daily_summaries(ghost_sessions, "ghost")
        self.update_daily_summaries(live_sessions, "live")

        # Load daily stats list
        daily_stats_ghost = self.load_daily_stats_files("ghost")
        daily_stats_live = self.load_daily_stats_files("live")

        # Calculate advanced insights
        insights_ghost = self._calculate_advanced_insights(ghost_sessions)
        insights_live = self._calculate_advanced_insights(live_sessions)

        # Compute z-regime win rates for the 5 optimal cutoffs (for panel filters and analysis)
        ghost_all_trades = [t for s in ghost_sessions for t in s.get("trades", [])]
        live_all_trades = [t for s in live_sessions for t in s.get("trades", [])]
        z_regime_ghost = self._compute_z_regime_winrates(ghost_all_trades)
        z_regime_live = self._compute_z_regime_winrates(live_all_trades)

        return {
            "ghost_sessions": [self._clean_session_for_api(s) for s in ghost_sessions],
            "live_sessions": [self._clean_session_for_api(s) for s in live_sessions],
            "daily_stats_ghost": daily_stats_ghost,
            "daily_stats_live": daily_stats_live,
            "insights_ghost": insights_ghost,
            "insights_live": insights_live,
            "z_regime_ghost": z_regime_ghost,
            "z_regime_live": z_regime_live,
        }

    def _calculate_advanced_insights(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute advanced insights (UTC hour, weekdays, extremes, streaks, score WRs, and best/worst assets)."""
        import datetime
        
        all_trades = []
        for s in sessions:
            for t in s.get("trades", []):
                if t.get("timestamp") and t.get("outcome") in ("win", "loss"):
                    all_trades.append(t)
                    
        empty_shell = {
            "time_of_day": {"best": "N/A", "worst": "N/A"},
            "day_of_week": {"best": "N/A", "worst": "N/A"},
            "session_extremes": {"top_wins": [], "top_losses": []},
            "streaks": {"avg_win_streak": 0.0, "avg_loss_streak": 0.0},
            "oteo_scores": {"best_band": "N/A", "worst_band": "N/A"},
            "asset_performers": {"best_assets": [], "worst_assets": []}
        }
        if not all_trades:
            return empty_shell
            
        # 1. Time of Day (UTC) & Weekdays
        hour_stats = {}
        day_stats = {}
        WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for t in all_trades:
            ts = float(t["timestamp"])
            dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
            h_str = f"{dt.hour:02d}:00"
            w_str = WEEKDAYS[dt.weekday()]
            
            is_win = t["outcome"] == "win"
            
            # Hour
            h_data = hour_stats.setdefault(h_str, {"total": 0, "wins": 0})
            h_data["total"] += 1
            if is_win:
                h_data["wins"] += 1
                
            # Weekday
            w_data = day_stats.setdefault(w_str, {"total": 0, "wins": 0})
            w_data["total"] += 1
            if is_win:
                w_data["wins"] += 1
                
        # Resolve best/worst hour (minimum 5 trades)
        valid_hours = {h: (d["wins"] / d["total"] * 100.0) for h, d in hour_stats.items() if d["total"] >= 5}
        best_hour = "N/A"
        worst_hour = "N/A"
        if valid_hours:
            best_h = max(valid_hours, key=valid_hours.get)
            worst_h = min(valid_hours, key=valid_hours.get)
            best_hour = f"{best_h} ({valid_hours[best_h]:.1f}% WR)"
            worst_hour = f"{worst_h} ({valid_hours[worst_h]:.1f}% WR)"
            
        # Resolve best/worst day (minimum 5 trades)
        valid_days = {w: (d["wins"] / d["total"] * 100.0) for w, d in day_stats.items() if d["total"] >= 5}
        best_day = "N/A"
        worst_day = "N/A"
        if valid_days:
            best_d = max(valid_days, key=valid_days.get)
            worst_d = min(valid_days, key=valid_days.get)
            best_day = f"{best_d} ({valid_days[best_d]:.1f}% WR)"
            worst_day = f"{worst_d} ({valid_days[worst_d]:.1f}% WR)"
            
        # 2. Session Extremes (Top 3 wins & losses)
        top_wins_sessions = []
        top_losses_sessions = []
        for s in sessions:
            top_wins_sessions.append({
                "session_id": s["session_id"],
                "wins": s["wins"],
                "total_trades": s["total_trades"],
                "win_rate": round(s["win_rate"], 1)
            })
            top_losses_sessions.append({
                "session_id": s["session_id"],
                "losses": s["losses"],
                "total_trades": s["total_trades"],
                "win_rate": round(s["win_rate"], 1)
            })
            
        top_wins = sorted(top_wins_sessions, key=lambda x: x["wins"], reverse=True)[:3]
        top_losses = sorted(top_losses_sessions, key=lambda x: x["losses"], reverse=True)[:3]
        
        # 3. Overall Streaks (Chronological across all trades)
        sorted_trades = sorted(all_trades, key=lambda x: float(x["timestamp"]))
        win_streaks = []
        loss_streaks = []
        
        curr_streak_type = None
        curr_streak_len = 0
        
        for t in sorted_trades:
            outcome = t["outcome"]
            if curr_streak_type is None:
                curr_streak_type = outcome
                curr_streak_len = 1
            elif outcome == curr_streak_type:
                curr_streak_len += 1
            else:
                if curr_streak_type == "win":
                    win_streaks.append(curr_streak_len)
                else:
                    loss_streaks.append(curr_streak_len)
                curr_streak_type = outcome
                curr_streak_len = 1
                
        if curr_streak_len > 0:
            if curr_streak_type == "win":
                win_streaks.append(curr_streak_len)
            else:
                loss_streaks.append(curr_streak_len)
                
        avg_win_streak = sum(win_streaks) / len(win_streaks) if win_streaks else 0.0
        avg_loss_streak = sum(loss_streaks) / len(loss_streaks) if loss_streaks else 0.0
        
        # 4. OTEO Score Bands (highest and lowest win rate band, minimum 5 trades)
        score_bands = {"50-60": {"total": 0, "wins": 0},
                       "60-70": {"total": 0, "wins": 0},
                       "70-80": {"total": 0, "wins": 0},
                       "80-90": {"total": 0, "wins": 0},
                       "90-100": {"total": 0, "wins": 0}}
                       
        for t in all_trades:
            score = float(t.get("oteo_score") or 0.0)
            is_win = t["outcome"] == "win"
            band = None
            if 50.0 <= score < 60.0:
                band = "50-60"
            elif 60.0 <= score < 70.0:
                band = "60-70"
            elif 70.0 <= score < 80.0:
                band = "70-80"
            elif 80.0 <= score < 90.0:
                band = "80-90"
            elif 90.0 <= score <= 100.0:
                band = "90-100"
                
            if band:
                score_bands[band]["total"] += 1
                if is_win:
                    score_bands[band]["wins"] += 1
                    
        valid_bands = {b: (d["wins"] / d["total"] * 100.0) for b, d in score_bands.items() if d["total"] >= 5}
        best_band = "N/A"
        worst_band = "N/A"
        if valid_bands:
            best_b = max(valid_bands, key=valid_bands.get)
            worst_b = min(valid_bands, key=valid_bands.get)
            best_band = f"{best_b} ({valid_bands[best_b]:.1f}% WR)"
            worst_band = f"{worst_b} ({valid_bands[worst_b]:.1f}% WR)"
            
        # 5. Asset Performers (Top 10 Best and Worst, minimum 5 trades)
        asset_stats = {}
        for t in all_trades:
            asset = t["asset"]
            is_win = t["outcome"] == "win"
            a_data = asset_stats.setdefault(asset, {"total": 0, "wins": 0, "losses": 0, "profit": 0.0})
            a_data["total"] += 1
            if is_win:
                a_data["wins"] += 1
            else:
                a_data["losses"] += 1
            a_data["profit"] += float(t.get("profit") or 0.0)
            
        ranked_assets = []
        for asset, d in asset_stats.items():
            if d["total"] >= 5:
                wr = d["wins"] / d["total"] * 100.0
                ranked_assets.append({
                    "asset": asset,
                    "total_trades": d["total"],
                    "wins": d["wins"],
                    "losses": d["losses"],
                    "win_rate": round(wr, 1),
                    "profit": round(d["profit"], 2)
                })
                
        best_assets = sorted(ranked_assets, key=lambda x: (x["win_rate"], x["profit"]), reverse=True)[:10]
        worst_assets = sorted(ranked_assets, key=lambda x: (x["win_rate"], x["profit"]))[:10]
        
        return {
            "time_of_day": {"best": best_hour, "worst": worst_hour},
            "day_of_week": {"best": best_day, "worst": worst_day},
            "session_extremes": {"top_wins": top_wins, "top_losses": top_losses},
            "streaks": {"avg_win_streak": round(avg_win_streak, 2), "avg_loss_streak": round(avg_loss_streak, 2)},
            "oteo_scores": {"best_band": best_band, "worst_band": worst_band},
            "asset_performers": {"best_assets": best_assets, "worst_assets": worst_assets}
        }

    def _clean_session_for_api(self, s: Dict[str, Any]) -> Dict[str, Any]:
        """Strip raw trades list for standard list fetch to keep payload size light."""
        cleaned = dict(s)
        if "trades" in cleaned:
            del cleaned["trades"]
        return cleaned

    def _compute_z_regime_winrates(self, all_trades: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Compute win rates for 5 fixed optimal z-score cutoffs per regime.
        Used for filters and AI analysis in Results & Analysis Panel.
        """
        if not all_trades:
            return {}
        cutoffs = [0.3, 0.5, 0.8, 1.2, 2.0]
        from collections import defaultdict
        data = defaultdict(lambda: {c: {"wins": 0, "total": 0} for c in cutoffs})
        for t in all_trades:
            entry = t.get("entry_context") or {}
            regime = entry.get("regime_label") or entry.get("regime") or "unknown"
            try:
                z = float(entry.get("z_score", 0) or 0)
            except (ValueError, TypeError):
                z = 0.0
            outcome = str(t.get("outcome", "")).lower()
            is_win = outcome == "win"
            for c in cutoffs:
                if abs(z) >= c:
                    data[regime][c]["total"] += 1
                    if is_win:
                        data[regime][c]["wins"] += 1
        result = {}
        for regime, cdata in data.items():
            result[regime] = []
            for c in cutoffs:
                d = cdata[c]
                total = d["total"]
                wr = (d["wins"] / total * 100.0) if total > 0 else 0.0
                result[regime].append({
                    "z_cutoff": c,
                    "win_rate": round(wr, 1),
                    "trades": total
                })
        return result

    def update_daily_summaries(self, sessions: List[Dict[str, Any]], kind: str) -> None:
        """Aggregate trade sessions into daily stats summaries saved to disk."""
        stats_dir = self.settings.data_dir / f"{kind}_trades" / "stats"
        stats_dir.mkdir(parents=True, exist_ok=True)

        # Clear existing daily stats files first so deleted sessions are immediately reflected
        if stats_dir.exists():
            for f in stats_dir.glob("*.json"):
                try:
                    f.unlink()
                except Exception as e:
                    logger.warning("Failed to delete old stats file %s: %s", f.name, e)

        daily_trades: Dict[str, List[Dict[str, Any]]] = {}

        for session in sessions:
            for trade in session.get("trades", []):
                ts = trade.get("timestamp")
                if not ts:
                    continue
                date_str = datetime.utcfromtimestamp(float(ts)).strftime("%Y-%m-%d")
                if date_str not in daily_trades:
                    daily_trades[date_str] = []
                daily_trades[date_str].append(trade)

        for date_str, trades in daily_trades.items():
            wins = sum(1 for t in trades if str(t.get("outcome", "")).lower() == "win")
            losses = sum(1 for t in trades if str(t.get("outcome", "")).lower() == "loss")
            voids = sum(1 for t in trades if str(t.get("outcome", "")).lower() == "void")
            total = len(trades)
            
            profit = 0.0
            for t in trades:
                p = t.get("profit")
                profit += float(p) if p is not None else 0.0

            win_rate = (wins / (wins + losses)) * 100.0 if (wins + losses) > 0 else 0.0

            # Asset breakdown
            asset_breakdown = {}
            for t in trades:
                asset = t.get("asset", "unknown")
                if asset not in asset_breakdown:
                    asset_breakdown[asset] = {"total": 0, "wins": 0, "losses": 0, "profit": 0.0}
                item = asset_breakdown[asset]
                item["total"] += 1
                outcome = str(t.get("outcome", "")).lower()
                if outcome == "win":
                    item["wins"] += 1
                elif outcome == "loss":
                    item["losses"] += 1
                p = t.get("profit")
                item["profit"] += float(p) if p is not None else 0.0

            # Expiry breakdown
            expiry_breakdown = {}
            for t in trades:
                exp = str(t.get("expiration_seconds", "60"))
                if exp not in expiry_breakdown:
                    expiry_breakdown[exp] = {"total": 0, "wins": 0, "losses": 0, "profit": 0.0}
                item = expiry_breakdown[exp]
                item["total"] += 1
                outcome = str(t.get("outcome", "")).lower()
                if outcome == "win":
                    item["wins"] += 1
                elif outcome == "loss":
                    item["losses"] += 1
                p = t.get("profit")
                item["profit"] += float(p) if p is not None else 0.0

            # Hour breakdown
            hour_breakdown = {}
            for t in trades:
                ts = t.get("timestamp")
                hour = datetime.utcfromtimestamp(float(ts)).hour if ts else 0
                hour_str = f"{hour:02d}:00"
                if hour_str not in hour_breakdown:
                    hour_breakdown[hour_str] = {"total": 0, "wins": 0, "losses": 0, "profit": 0.0}
                item = hour_breakdown[hour_str]
                item["total"] += 1
                outcome = str(t.get("outcome", "")).lower()
                if outcome == "win":
                    item["wins"] += 1
                elif outcome == "loss":
                    item["losses"] += 1
                p = t.get("profit")
                item["profit"] += float(p) if p is not None else 0.0

            summary = {
                "date": date_str,
                "total_trades": total,
                "wins": wins,
                "losses": losses,
                "voids": voids,
                "profit": profit,
                "win_rate": win_rate,
                "assets": asset_breakdown,
                "expirations": expiry_breakdown,
                "hours": hour_breakdown,
            }

            filepath = stats_dir / f"{date_str}.json"
            filepath.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    def load_daily_stats_files(self, kind: str) -> List[Dict[str, Any]]:
        """Load all daily stats JSON summary files from disk."""
        stats_dir = self.settings.data_dir / f"{kind}_trades" / "stats"
        summaries = []
        if stats_dir.exists():
            for filepath in stats_dir.glob("*.json"):
                try:
                    summaries.append(json.loads(filepath.read_text(encoding="utf-8")))
                except Exception as e:
                    logger.error("Failed to parse daily stats file %s: %s", filepath.name, e)
        summaries.sort(key=lambda s: s.get("date", ""), reverse=True)
        return summaries

    async def run_ai_refinement(self, session_id: str, kind: str, filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Perform token-efficient logs review via Grok 4.3 API.
        filters can include z_cutoff, regimes to filter trades and analyze optimal z/regime combos.
        """
        session_dir = self.settings.data_dir / f"{kind}_trades" / "sessions"
        filepath = session_dir / f"{session_id}.jsonl"
        session_data = self.parse_session_file(filepath, kind)

        if not session_data:
            return {"error": f"Session {session_id} not found or has no trades."}

        filters = filters or {}
        z_cutoff = filters.get("z_cutoff")
        selected_regimes = filters.get("regimes") or []

        # Summarize session details to stay within prompt limits
        trades_summary = []
        for t in session_data.get("trades", []):
            entry_ctx = t.get("entry_context") or {}
            market_ctx = entry_ctx.get("market_context") or {}
            manipulation = entry_ctx.get("manipulation") or {}
            
            # Helper to calculate manipulation severity
            def _get_sev(v: Any) -> float:
                if isinstance(v, bool):
                    return 1.0 if v else 0.0
                try:
                    return float(v)
                except (ValueError, TypeError):
                    return 1.0 if v else 0.0
            
            manip_sev = max((_get_sev(val) for val in manipulation.values()), default=0.0)
            
            z_val = entry_ctx.get("z_score") or 0
            try:
                z_val = float(z_val)
            except (ValueError, TypeError):
                z_val = 0.0
            regime = entry_ctx.get("regime_label") or market_ctx.get("regime_label") or market_ctx.get("adx_regime") or "unknown"

            # Apply filters if provided
            if z_cutoff is not None and abs(z_val) < float(z_cutoff):
                continue
            if selected_regimes and regime not in selected_regimes:
                continue

            trades_summary.append({
                "asset": t.get("asset"),
                "dir": t.get("direction"),
                "outcome": t.get("outcome"),
                "profit": t.get("profit"),
                "oteo": t.get("oteo_score"),
                "level": t.get("strategy_level"),
                "expiry": t.get("expiration_seconds"),
                "regime": regime,
                "regime_confidence": entry_ctx.get("regime_confidence") or market_ctx.get("regime_confidence") or 0,
                "regime_stable": entry_ctx.get("regime_stable") or market_ctx.get("regime_stable") or False,
                "z_score": round(z_val, 2) if z_val else "N/A",
                "velocity": entry_ctx.get("velocity") or "N/A",
                "adx_power": market_ctx.get("adx") or "N/A",
                "tick_health": market_ctx.get("tick_health") or "N/A",
                "nearest_sr_atr": market_ctx.get("nearest_structure_atr") or "N/A",
                "manip_severity": round(manip_sev, 2),
                "manip_type": list(manipulation.keys()) if isinstance(manipulation, dict) else []
            })

        # Compute optimal z-regime for the (filtered) session trades for AI analysis of filters
        session_z_regime = self._compute_z_regime_winrates([
            {"entry_context": {"regime_label": t.get("regime"), "z_score": t.get("z_score")},
             "outcome": t.get("outcome")}
            for t in trades_summary
        ])

        # Grok system prompt
        system_prompt = (
            "You are Grok 4.3, the expert AI Trading Analyst. Your task is to analyze this session's trades, "
            "identify why losses occurred, identify missing pattern behaviors, suggest optimal parameters "
            "(like whether 30s, 1m, or 2m is better), and produce actionable advice to maximize win rate."
        )

        prompt_body = (
            f"Please review the following session summary:\n"
            f"Session ID: {session_id}\n"
            f"Kind: {kind}\n"
            f"Total Trades: {session_data['total_trades']}\n"
            f"Wins: {session_data['wins']}, Losses: {session_data['losses']}\n"
            f"Net Profit: ${session_data['profit']:.2f}\n"
            f"Win Rate: {session_data['win_rate']:.1f}%\n\n"
            f"Active Filters Applied (if any): z_cutoff={z_cutoff}, regimes={selected_regimes}\n\n"
            f"Trades Log Summary (enriched with Z-score, velocity, ADX power, S/R distance, and tick health):\n"
            f"{json.dumps(trades_summary[:50], indent=2)}\n\n"
            f"Optimal 5 z-score cutoffs and Win Rates by Regime (for filter analysis):\n"
            f"{json.dumps(session_z_regime, indent=2)}\n\n"
            f"Analyze and format your response clearly. Focus on how indicators like Z-score, velocity, tick health, "
            f"and manipulation severity correlated with win vs loss outcomes. Include a section named 'Discovered Patterns' "
            f"where you list specific repeating characteristics (e.g. 'Level 2 False Reversals'). "
            f"Also analyze the optimal z-score thresholds per regime shown above and recommend which z-score cutoffs + regimes "
            f"would be best to add as filters in the Ghost Controller for execution quality. Suggest specific 5 optimal combinations "
            f"and expected impact on win rate.\n\n"
            f"Conclude with a concise audio-friendly summary script. "
            f"IMPORTANT FOR VOICE: At the very end of your response, output ONLY the short spoken briefing version (natural, conversational, "
            f"under ~550 characters preferred) delimited EXACTLY as follows (do not add extra commentary outside the delimiters):\n"
            f"---VOICE_SCRIPT_START---\n"
            f"[Your concise spoken summary script here. Use short sentences suitable for listening. Focus on key insights, optimal filters, and actionable advice.]\n"
            f"---VOICE_SCRIPT_END---"
        )

        ai_service = get_ai_service()
        
        # Build prompt using AI chat format
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_body}
        ]
        
        # Call AI provider
        ai_service = get_ai_service()
        chat_req = AIChatRequest(
            messages=[AIMessage(role=m["role"], content=m["content"]) for m in messages],
            model=ai_service.settings.ai_model,  # respect AI Settings / profile model
            context=AIContext(
                asset=session_data["assets"][0] if session_data["assets"] else None,
                balance=None,
                session_pnl=session_data["profit"],
                win_rate=session_data["win_rate"],
                total_trades=session_data["total_trades"]
            )
        )
        
        ai_res = await ai_service.chat(chat_req)
        ai_text = ai_res.text

        # Extract dedicated short voice script (for fast/low-cost Grok TTS playback)
        # The prompt forces a clear delimited section so we can serve a concise version
        # to the voice path without sending the entire verbose report to TTS.
        voice_script = None
        try:
            if "---VOICE_SCRIPT_START---" in ai_text and "---VOICE_SCRIPT_END---" in ai_text:
                after_start = ai_text.split("---VOICE_SCRIPT_START---", 1)[1]
                candidate = after_start.split("---VOICE_SCRIPT_END---", 1)[0].strip()
                if candidate:
                    # Basic clean for speaking (remove leftover markdown)
                    voice_script = candidate.replace('*', '').replace('#', '').replace('`', '').strip()
        except Exception as ex:
            logger.warning("Failed to extract VOICE_SCRIPT: %s", ex)

        if not voice_script:
            # Fallback: take a reasonable tail of the response (last few sentences)
            try:
                tail = ai_text.strip().split('\n')[-6:]
                voice_script = ' '.join(tail).replace('*', '').replace('#', '').replace('`', '').strip()[:600]
            except Exception:
                voice_script = None

        # Extract patterns and save to pattern memory
        # We can scan the AI response for bullet points or lists of patterns
        patterns_found = []
        try:
            # Look for lines mentioning patterns
            for line in ai_text.split("\n"):
                if "pattern:" in line.lower() or "discovered:" in line.lower():
                    patterns_found.append(line.strip("- *"))
            
            if not patterns_found:
                # Fallback pattern if none structured
                patterns_found = [f"Regime specific trend anomalies in {session_id}"]
            
            for p in patterns_found[:3]:
                self.save_pattern({
                    "name": p,
                    "session_id": session_id,
                    "kind": kind,
                    "regime": trades_summary[0]["regime"] if trades_summary else "unknown",
                    "win_rate": session_data["win_rate"],
                    "advisory_notes": f"Identified in session {session_id} analysis."
                })
        except Exception as ex:
            logger.warning("Failed to extract patterns from AI response: %s", ex)

        return {
            "session_id": session_id,
            "report": ai_text,
            "voice_script": voice_script,
            "patterns": self.load_patterns(),
        }

_ANALYSIS_SERVICE: AnalysisService | None = None

def get_analysis_service() -> AnalysisService:
    global _ANALYSIS_SERVICE
    if _ANALYSIS_SERVICE is None:
        _ANALYSIS_SERVICE = AnalysisService()
    return _ANALYSIS_SERVICE
