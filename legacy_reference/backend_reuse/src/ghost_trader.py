"""
Ghost Trader — C1 (2026-03-23)
==============================
Records and evaluates ghost (paper) trades from OTEO signals.
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("GhostTrader")

class GhostTrader:
    """
    Records and evaluates ghost (paper) trades from OTEO signals.
    """

    def __init__(self, data_dir: Path, default_amount: float = 10.0):
        self.data_dir = Path(data_dir)
        self.sessions_dir = self.data_dir / "ghost_trades" / "sessions"
        self.stats_dir = self.data_dir / "ghost_trades" / "stats"
        self.default_amount = default_amount
        
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.stats_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_start = time.time()
        ts_str = time.strftime("%Y-%m-%d_%H%M", time.localtime(self.session_start))
        self.session_id = f"gs_{ts_str}"
        self.session_file = self.sessions_dir / f"ghost_session_{ts_str}.jsonl"
        
        # Active trades waiting for expiry
        # Dict[str, dict] -> trade_id: trade_data
        self.active_trades: Dict[str, dict] = {}
        
        # Cooldown per asset: Dict[str, float] -> asset: last_trade_timestamp
        self.last_trade_times: Dict[str, float] = {}
        self.cooldown_seconds = 30.0  # Optional cooldown for trades

    def on_signal(
        self,
        asset: str,
        direction: str,
        price: float,
        oteo_score: float,
        expiry: int,
        confidence: str,
        velocity: float = 0.0,
        z_score: float = 0.0,
        manipulation: Optional[dict] = None,
        broker: str = "pocket_option",
        payout_pct: float = 92.0
    ) -> Optional[str]:
        """
        Record a new ghost trade. Only acts on HIGH confidence.
        Returns the trade_id if a trade was created, else None.
        """
        if confidence != "HIGH":
            return None
            
        now = time.time()
        
        # Check cooldown
        if asset in self.last_trade_times:
            if now - self.last_trade_times[asset] < self.cooldown_seconds:
                return None
        
        trade_id = f"gt_{int(now)}_{asset}_{direction}"
        
        trade = {
            "id": trade_id,
            "session_id": self.session_id,
            "asset": asset,
            "direction": direction,
            "entry_price": price,
            "entry_time": now,
            "expiry_seconds": expiry,
            "oteo_score": oteo_score,
            "confidence": confidence,
            "velocity": velocity,
            "z_score": z_score,
            "manipulation_at_entry": manipulation or {"push_snap": False, "pinning": False},
            "broker": broker,
            "payout_pct": payout_pct,
            "simulated_amount": self.default_amount,
            # To be populated on expiry:
            "exit_price": None,
            "exit_time": None,
            "outcome": None,
            "simulated_profit": None
        }
        
        self.active_trades[trade_id] = trade
        self.last_trade_times[asset] = now
        
        logger.info("👻 Ghost trade entered: %s %s @ %s (Expiry: %ss)", direction, asset, price, expiry)
        return trade_id

    def check_expiries(self, current_prices: Dict[str, float]) -> List[dict]:
        """
        Check active trades against current time. If expired, evaluate win/loss.
        Returns a list of completed trade dicts.
        """
        now = time.time()
        completed_trades = []
        
        # Iterate over a list of keys since we might delete from dict
        for trade_id in list(self.active_trades.keys()):
            trade = self.active_trades[trade_id]
            asset = trade["asset"]
            
            # Use the latest price if available, else we can't resolve yet
            if asset not in current_prices:
                continue
                
            expiry_time = trade["entry_time"] + trade["expiry_seconds"]
            if now >= expiry_time:
                # Trade has expired
                exit_price = current_prices[asset]
                trade["exit_price"] = exit_price
                trade["exit_time"] = now
                
                direction = trade["direction"]
                entry_price = trade["entry_price"]
                
                # Evaluate outcome
                if direction == "CALL":
                    if exit_price > entry_price:
                        outcome = "WIN"
                    elif exit_price < entry_price:
                        outcome = "LOSS"
                    else:
                        outcome = "TIE"
                else: # PUT
                    if exit_price < entry_price:
                        outcome = "WIN"
                    elif exit_price > entry_price:
                        outcome = "LOSS"
                    else:
                        outcome = "TIE"
                
                trade["outcome"] = outcome
                
                if outcome == "WIN":
                    trade["simulated_profit"] = trade["simulated_amount"] * (trade["payout_pct"] / 100.0)
                elif outcome == "LOSS":
                    trade["simulated_profit"] = -trade["simulated_amount"]
                else:
                    trade["simulated_profit"] = 0.0
                
                completed_trades.append(trade)
                del self.active_trades[trade_id]
                
                logger.info("👻 Ghost trade completed: %s %s -> %s (P&L: %s)", trade["direction"], asset, outcome, trade["simulated_profit"])
                
                self._save_trade(trade)
                self._update_stats(trade)
                
        return completed_trades

    def _save_trade(self, trade: dict) -> None:
        """Append completed trade to the session JSONL file."""
        try:
            with open(self.session_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(trade, separators=(",", ":")) + "\n")
        except IOError as e:
            logger.error("Failed to save ghost trade: %s", e)

    def _update_stats(self, trade: dict) -> None:
        """Update rolling stats for the asset and aggregate."""
        asset = trade["asset"]
        outcome = trade["outcome"]
        profit = trade["simulated_profit"] or 0.0
        
        # Asset stats
        asset_stats_file = self.stats_dir / f"{asset}_stats.json"
        astats = self._load_json(asset_stats_file, {"trades": 0, "wins": 0, "losses": 0, "ties": 0, "profit": 0.0})
        
        astats["trades"] += 1
        if outcome == "WIN": astats["wins"] += 1
        elif outcome == "LOSS": astats["losses"] += 1
        elif outcome == "TIE": astats["ties"] += 1
        astats["profit"] += profit
        
        self._save_json(asset_stats_file, astats)
        
        # Aggregate stats
        agg_stats_file = self.stats_dir / "_aggregate_stats.json"
        agg = self._load_json(agg_stats_file, {"trades": 0, "wins": 0, "losses": 0, "ties": 0, "profit": 0.0})
        
        agg["trades"] += 1
        if outcome == "WIN": agg["wins"] += 1
        elif outcome == "LOSS": agg["losses"] += 1
        elif outcome == "TIE": agg["ties"] += 1
        agg["profit"] += profit
        
        self._save_json(agg_stats_file, agg)

    def _load_json(self, path: Path, default: Any) -> Any:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (IOError, json.JSONDecodeError):
                pass
        return default

    def _save_json(self, path: Path, data: Any) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.error("Failed to save stats to %s: %s", path, e)

    def get_session_stats(self) -> dict:
        """Get stats for the current session."""
        agg_stats_file = self.stats_dir / "_aggregate_stats.json"
        return self._load_json(agg_stats_file, {"trades": 0, "wins": 0, "losses": 0, "ties": 0, "profit": 0.0})

    def get_asset_stats(self, asset: str) -> dict:
        """Get stats for a specific asset."""
        asset_stats_file = self.stats_dir / f"{asset}_stats.json"
        return self._load_json(asset_stats_file, {"trades": 0, "wins": 0, "losses": 0, "ties": 0, "profit": 0.0})


