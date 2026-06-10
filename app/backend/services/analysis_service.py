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

        return {
            "ghost_sessions": [self._clean_session_for_api(s) for s in ghost_sessions],
            "live_sessions": [self._clean_session_for_api(s) for s in live_sessions],
            "daily_stats_ghost": daily_stats_ghost,
            "daily_stats_live": daily_stats_live,
        }

    def _clean_session_for_api(self, s: Dict[str, Any]) -> Dict[str, Any]:
        """Strip raw trades list for standard list fetch to keep payload size light."""
        cleaned = dict(s)
        if "trades" in cleaned:
            del cleaned["trades"]
        return cleaned

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

    async def run_ai_refinement(self, session_id: str, kind: str) -> Dict[str, Any]:
        """Perform token-efficient logs review via Grok 4.3 API."""
        session_dir = self.settings.data_dir / f"{kind}_trades" / "sessions"
        filepath = session_dir / f"{session_id}.jsonl"
        session_data = self.parse_session_file(filepath, kind)

        if not session_data:
            return {"error": f"Session {session_id} not found or has no trades."}

        # Summarize session details to stay within prompt limits
        trades_summary = []
        for t in session_data.get("trades", []):
            entry_ctx = t.get("entry_context", {})
            market_ctx = entry_ctx.get("market_context", {})
            manipulation = entry_ctx.get("manipulation", {})
            
            trades_summary.append({
                "asset": t.get("asset"),
                "dir": t.get("direction"),
                "outcome": t.get("outcome"),
                "profit": t.get("profit"),
                "oteo": t.get("oteo_score"),
                "level": t.get("strategy_level"),
                "expiry": t.get("expiration_seconds"),
                "regime": market_ctx.get("adx_regime", "unavailable"),
                "trend": market_ctx.get("trend_direction", "flat"),
                "manip_type": list(manipulation.keys()) if isinstance(manipulation, dict) else []
            })

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
            f"Trades Log Summary:\n{json.dumps(trades_summary[:50], indent=2)}\n\n"
            f"Analyze and format your response clearly. Include a section named 'Discovered Patterns' "
            f"where you list specific repeating characteristics (e.g. 'Level 2 False Reversals') and "
            f"conclude with a concise audio-friendly summary script."
        )

        ai_service = get_ai_service()
        
        # Build prompt using AI chat format
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_body}
        ]
        
        # Call AI provider
        chat_req = AIChatRequest(
            messages=[AIMessage(role=m["role"], content=m["content"]) for m in messages],
            model="grok-4.3",
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
            "patterns": self.load_patterns(),
        }

_ANALYSIS_SERVICE: AnalysisService | None = None

def get_analysis_service() -> AnalysisService:
    global _ANALYSIS_SERVICE
    if _ANALYSIS_SERVICE is None:
        _ANALYSIS_SERVICE = AnalysisService()
    return _ANALYSIS_SERVICE
