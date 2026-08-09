"""Data Bridge API — Standalone DaaS REST Endpoints for Data Agent."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional, Set

try:
    from data_agent.src.filters.pipeline_manager import (
        FilterPipelineManager,
        UnknownGateError,
    )
    from data_agent.src.filters.context_provider import (
        ContextResult,
        MarketContextProvider,
        TickFieldContextProvider,
    )
except ImportError:
    try:
        from src.filters.pipeline_manager import FilterPipelineManager, UnknownGateError
        from src.filters.context_provider import (
            ContextResult,
            MarketContextProvider,
            TickFieldContextProvider,
        )
    except ImportError:
        from filters.pipeline_manager import FilterPipelineManager, UnknownGateError
        from filters.context_provider import (
            ContextResult,
            MarketContextProvider,
            TickFieldContextProvider,
        )

logger = logging.getLogger(__name__)

# Trade outcome validation bounds
ALLOWED_TRADE_KEYS: Set[str] = {"asset", "won", "features"}
MAX_FEATURES = 32
MAX_FEATURE_LEN = 64
MAX_ASSET_LEN = 64


class DataBridgeAPI:
    """Standalone Data-as-a-Service (DaaS) REST API Router."""

    def __init__(
        self,
        db_path: str = "data-agent/data/ticks_fallback.db",
        priors_path: str = "app/data/ghost_trades/stats/bayesian_priors.json",
        prior_updater: Optional[Any] = None,
        context_provider: Optional[MarketContextProvider] = None,
    ):
        self.db_path = db_path
        self.priors_path = priors_path
        self.prior_updater = prior_updater
        self.context_provider: MarketContextProvider = (
            context_provider or TickFieldContextProvider()
        )
        self.pipeline_manager = FilterPipelineManager()

    def get_raw_ticks(self, asset: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """Fetch 100% clean, unmutated raw tick data from local fallback DB."""
        if not os.path.exists(self.db_path):
            return {
                "status": "ok",
                "mode": "RAW_CLEAN_DATA",
                "count": 0,
                "ticks": [],
                "notice": "Local SQLite database not initialized yet.",
            }

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            if asset:
                cursor.execute(
                    "SELECT timestamp, asset, price, dir, is_demo, received_at "
                    "FROM ticks WHERE asset=? ORDER BY timestamp DESC LIMIT ?",
                    (asset, limit),
                )
            else:
                cursor.execute(
                    "SELECT timestamp, asset, price, dir, is_demo, received_at "
                    "FROM ticks ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                )
            rows = cursor.fetchall()
            conn.close()

            ticks = [
                {
                    "timestamp": r[0],
                    "asset": r[1],
                    "price": r[2],
                    "dir": r[3],
                    "is_demo": bool(r[4]),
                    "received_at": r[5],
                }
                for r in rows
            ]
            return {
                "status": "ok",
                "mode": "RAW_CLEAN_DATA",
                "count": len(ticks),
                "ticks": ticks,
            }
        except Exception as err:
            logger.error("Error fetching raw ticks: %s", err)
            return {"status": "error", "message": str(err)}

    def get_available_assets(self, collector: Optional[Any] = None) -> Dict[str, Any]:
        """Fetch live broker asset catalog with real-time session payouts."""
        # Baseline catalog definitions
        base_catalog = [
            # Currencies OTC
            {"symbol": "EURUSD_otc", "name": "EUR/USD OTC", "payout": 92, "category": "Currencies"},
            {"symbol": "GBPUSD_otc", "name": "GBP/USD OTC", "payout": 92, "category": "Currencies"},
            {"symbol": "USDJPY_otc", "name": "USD/JPY OTC", "payout": 92, "category": "Currencies"},
            {"symbol": "AUDCAD_otc", "name": "AUD/CAD OTC", "payout": 92, "category": "Currencies"},
            {"symbol": "USDCHF_otc", "name": "USD/CHF OTC", "payout": 92, "category": "Currencies"},
            {"symbol": "USDCAD_otc", "name": "USD/CAD OTC", "payout": 92, "category": "Currencies"},
            {"symbol": "EURGBP_otc", "name": "EUR/GBP OTC", "payout": 92, "category": "Currencies"},
            {"symbol": "EURJPY_otc", "name": "EUR/JPY OTC", "payout": 92, "category": "Currencies"},
            {"symbol": "GBPJPY_otc", "name": "GBP/JPY OTC", "payout": 92, "category": "Currencies"},
            {"symbol": "AUDJPY_otc", "name": "AUD/JPY OTC", "payout": 92, "category": "Currencies"},
            {"symbol": "AUDUSD_otc", "name": "AUD/USD OTC", "payout": 92, "category": "Currencies"},
            {"symbol": "NZDUSD_otc", "name": "NZD/USD OTC", "payout": 92, "category": "Currencies"},
            {"symbol": "CHFJPY_otc", "name": "CHF/JPY OTC", "payout": 90, "category": "Currencies"},
            {"symbol": "EURAUD_otc", "name": "EUR/AUD OTC", "payout": 90, "category": "Currencies"},
            {"symbol": "GBPAUD_otc", "name": "GBP/AUD OTC", "payout": 90, "category": "Currencies"},
            # Emerging Markets OTC
            {"symbol": "ZARUSD_otc", "name": "ZAR/USD OTC", "payout": 92, "category": "Emerging"},
            {"symbol": "NGNUSD_otc", "name": "NGN/USD OTC", "payout": 92, "category": "Emerging"},
            {"symbol": "USDARS_otc", "name": "USD/ARS OTC", "payout": 92, "category": "Emerging"},
            {"symbol": "USDBRL_otc", "name": "USD/BRL OTC", "payout": 92, "category": "Emerging"},
            {"symbol": "USDTRY_otc", "name": "USD/TRY OTC", "payout": 92, "category": "Emerging"},
            {"symbol": "USDMXN_otc", "name": "USD/MXN OTC", "payout": 90, "category": "Emerging"},
            # Commodities & Crypto
            {"symbol": "GOLD_otc", "name": "Gold OTC", "payout": 90, "category": "Commodities"},
            {"symbol": "SILVER_otc", "name": "Silver OTC", "payout": 90, "category": "Commodities"},
            {"symbol": "CRUDE_otc", "name": "Crude Oil OTC", "payout": 90, "category": "Commodities"},
            {"symbol": "BTCUSD", "name": "Bitcoin / USD", "payout": 85, "category": "Crypto"},
            {"symbol": "ETHUSD", "name": "Ethereum / USD", "payout": 85, "category": "Crypto"},
            {"symbol": "SOLUSD", "name": "Solana / USD", "payout": 85, "category": "Crypto"},
            {"symbol": "XRPUSD", "name": "Ripple / USD", "payout": 85, "category": "Crypto"},
        ]

        live_assets = set()
        if collector is not None:
            live_assets = set(getattr(collector, "assets", set()) or set())
            subscribed_set = set(getattr(collector, "_subscribed_assets", set()) or set())
            live_assets.update(subscribed_set)

        result_assets = []
        for item in base_catalog:
            sym = item["symbol"]
            is_live = sym in live_assets
            result_assets.append({
                "symbol": sym,
                "name": item["name"],
                "payout": item["payout"],
                "category": item["category"],
                "live": is_live,
            })

        # Include custom subscribed assets not in base catalog
        known_symbols = {a["symbol"] for a in result_assets}
        for custom_sym in sorted(live_assets):
            if custom_sym not in known_symbols:
                result_assets.insert(0, {
                    "symbol": custom_sym,
                    "name": custom_sym,
                    "payout": None,
                    "category": "Custom",
                    "live": True,
                })

        return {
            "status": "ok",
            "count": len(result_assets),
            "assets": result_assets,
        }

    def get_tick_velocity(
        self,
        asset: Optional[str] = None,
        limit: int = 15,
        interval_sec: int = 5,
    ) -> Dict[str, Any]:
        """Generate rolling time-bucketed tick density and volatility timeseries."""
        if not os.path.exists(self.db_path):
            return {"status": "ok", "asset": asset, "count": 0, "points": []}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Fetch recent ticks ordered by timestamp ascending
            if asset:
                cursor.execute(
                    "SELECT timestamp, price FROM ticks WHERE asset=? ORDER BY timestamp DESC LIMIT ?",
                    (asset, limit * 20),
                )
            else:
                cursor.execute(
                    "SELECT timestamp, price FROM ticks ORDER BY timestamp DESC LIMIT ?",
                    (limit * 20,),
                )
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return {"status": "ok", "asset": asset, "count": 0, "points": []}

            # Group rows into interval_sec buckets
            import datetime
            buckets: Dict[int, List[float]] = {}
            for ts, price in rows:
                bucket_key = int(ts // interval_sec) * interval_sec
                buckets.setdefault(bucket_key, []).append(float(price))

            points = []
            for b_time in sorted(buckets.keys())[-limit:]:
                prices = buckets[b_time]
                count = len(prices)
                ticks_per_min = int(round(count * (60.0 / interval_sec)))

                # Calculate normalized volatility
                if len(prices) > 1:
                    high_p = max(prices)
                    low_p = min(prices)
                    mean_p = sum(prices) / len(prices)
                    spread_pts = (high_p - low_p) / (mean_p or 1.0) * 10000.0
                    vol_score = max(10, min(100, int(round(spread_pts * 10 + 20))))
                else:
                    vol_score = 30

                time_str = datetime.datetime.fromtimestamp(
                    b_time, tz=datetime.timezone.utc
                ).strftime("%H:%M:%S")

                points.append({
                    "time": time_str,
                    "ticks_per_min": ticks_per_min,
                    "vol": vol_score,
                    "sample_count": count,
                })

            return {
                "status": "ok",
                "asset": asset,
                "count": len(points),
                "points": points,
            }
        except Exception as err:
            logger.error("Error computing tick velocity: %s", err)
            return {"status": "error", "message": str(err), "points": []}

    def get_filtered_ticks(
        self,
        asset: Optional[str] = None,
        limit: int = 100,
        gates_str: str = "bayesian,volatility,liquidity",
    ) -> Dict[str, Any]:
        """Fetch raw ticks overlaid with dynamic filter evaluation results."""
        raw_res = self.get_raw_ticks(asset=asset, limit=limit)
        if raw_res.get("status") != "ok":
            return raw_res

        active_gates = [g.strip() for g in gates_str.split(",") if g.strip()]
        unknown = self.pipeline_manager.unknown_gates(active_gates)
        if unknown:
            return {
                "status": "error",
                "code": "unknown_gates",
                "message": f"Unknown filter gate(s): {', '.join(unknown)}",
                "unknown_gates": unknown,
                "http_status": 400,
            }

        ticks = raw_res.get("ticks", [])
        annotated_ticks = []

        for t in ticks:
            asset_name = str(t.get("asset") or asset or "UNKNOWN")
            ctx: ContextResult = self.context_provider.get_context(t, asset_name)
            market_ctx = dict(ctx.values) if ctx.available else {}

            try:
                passed, veto_reasons = self.pipeline_manager.evaluate_pipeline(
                    t,
                    active_gates=active_gates,
                    market_context=market_ctx,
                )
            except UnknownGateError as err:
                return {
                    "status": "error",
                    "code": "unknown_gates",
                    "message": str(err),
                    "unknown_gates": err.unknown_gates,
                    "http_status": 400,
                }

            t_copy = dict(t)
            t_copy["filter_evaluation"] = {
                "active_gates": active_gates,
                "passed": passed,
                "veto_reasons": veto_reasons,
                "context_available": ctx.available,
                "context_source": ctx.source,
                "context_reason": ctx.reason,
            }
            annotated_ticks.append(t_copy)

        return {
            "status": "ok",
            "mode": "DYNAMIC_FILTERED_OVERLAY",
            "active_gates": active_gates,
            "count": len(annotated_ticks),
            "ticks": annotated_ticks,
        }

    def get_market_context(self, asset: str = "EURUSD_otc") -> Dict[str, Any]:
        """
        Return market context without fabricating scores.

        Until a live analytics producer is injected, report explicit unavailability.
        """
        probe_tick: Dict[str, Any] = {"asset": asset}
        ctx = self.context_provider.get_context(probe_tick, asset)
        return {
            "status": "ok",
            "asset": asset,
            "available": ctx.available,
            "source": ctx.source,
            "reason": ctx.reason
            or (
                None
                if ctx.available
                else "No live analytics producer configured; context not fabricated."
            ),
            "market_context": dict(ctx.values),
        }

    def get_bayesian_priors(self) -> Dict[str, Any]:
        """Return active Bayesian prior win-rate statistics matrix via shared store retries."""
        try:
            if self.prior_updater is not None:
                priors = self.prior_updater.load_current_priors()
            else:
                from shared.bayesian_prior_store import BayesianPriorStore

                priors = BayesianPriorStore(self.priors_path).read()
            if not os.path.exists(self.priors_path):
                return {
                    "status": "ok",
                    "priors": priors,
                    "notice": "Bayesian priors file not found, using default prior distribution.",
                }
            return {"status": "ok", "priors": priors}
        except Exception as err:
            logger.error("Error loading Bayesian priors: %s", err)
            return {
                "status": "error",
                "message": str(err),
                "http_status": 500,
            }

    def record_trade_outcome(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record a validated trade outcome into the shared Bayesian prior updater.

        Returns recorded:true only after the prior transaction commits.
        """
        validation_error = self._validate_trade_payload(trade_data)
        if validation_error is not None:
            return validation_error

        asset = trade_data["asset"].strip()
        won = trade_data["won"]
        features = self._normalize_features(trade_data.get("features", []))

        if self.prior_updater is None:
            logger.error("record_trade_outcome called without prior_updater")
            return {
                "status": "error",
                "code": "updater_unavailable",
                "message": "Bayesian prior updater is not configured.",
                "recorded": False,
                "http_status": 503,
            }

        try:
            updated = self.prior_updater.update_priors_from_trades(
                [{"won": won, "features": features, "asset": asset}]
            )
        except Exception as err:
            logger.error("Failed to persist trade outcome for %s: %s", asset, err)
            return {
                "status": "error",
                "code": "persistence_failed",
                "message": str(err),
                "recorded": False,
                "asset": asset,
                "http_status": 500,
            }

        outcome = "WIN" if won else "LOSS"
        logger.info("Recorded trade outcome for %s: %s", asset, outcome)
        return {
            "status": "ok",
            "recorded": True,
            "asset": asset,
            "outcome": outcome,
            "total_wins": updated.get("total_wins"),
            "total_losses": updated.get("total_losses"),
            "total_trades": updated.get("total_trades"),
            "http_status": 200,
        }

    def _validate_trade_payload(self, trade_data: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(trade_data, dict):
            return {
                "status": "error",
                "code": "invalid_payload",
                "message": "Trade payload must be a JSON object.",
                "recorded": False,
                "http_status": 400,
            }

        unknown = sorted(set(trade_data.keys()) - ALLOWED_TRADE_KEYS)
        if unknown:
            return {
                "status": "error",
                "code": "unknown_fields",
                "message": f"Unknown field(s): {', '.join(unknown)}",
                "recorded": False,
                "unknown_fields": unknown,
                "http_status": 400,
            }

        asset = trade_data.get("asset")
        if not isinstance(asset, str) or not asset.strip():
            return {
                "status": "error",
                "code": "invalid_asset",
                "message": "asset must be a non-empty string.",
                "recorded": False,
                "http_status": 400,
            }
        if len(asset.strip()) > MAX_ASSET_LEN:
            return {
                "status": "error",
                "code": "invalid_asset",
                "message": f"asset exceeds max length {MAX_ASSET_LEN}.",
                "recorded": False,
                "http_status": 400,
            }

        if "won" not in trade_data:
            return {
                "status": "error",
                "code": "invalid_won",
                "message": "won is required and must be a JSON boolean.",
                "recorded": False,
                "http_status": 400,
            }
        won = trade_data["won"]
        if not isinstance(won, bool):
            return {
                "status": "error",
                "code": "invalid_won",
                "message": "won must be a JSON boolean (true/false), not a string or number.",
                "recorded": False,
                "http_status": 400,
            }

        if "features" in trade_data and trade_data["features"] is not None:
            if not isinstance(trade_data["features"], list):
                return {
                    "status": "error",
                    "code": "invalid_features",
                    "message": "features must be a list of strings when provided.",
                    "recorded": False,
                    "http_status": 400,
                }
            if len(trade_data["features"]) > MAX_FEATURES:
                return {
                    "status": "error",
                    "code": "invalid_features",
                    "message": f"features exceeds max count {MAX_FEATURES}.",
                    "recorded": False,
                    "http_status": 400,
                }
            for feat in trade_data["features"]:
                if not isinstance(feat, str):
                    return {
                        "status": "error",
                        "code": "invalid_features",
                        "message": "each feature must be a string.",
                        "recorded": False,
                        "http_status": 400,
                    }
                cleaned = feat.strip()
                if not cleaned or len(cleaned) > MAX_FEATURE_LEN:
                    return {
                        "status": "error",
                        "code": "invalid_features",
                        "message": (
                            f"each feature must be a non-empty string "
                            f"up to {MAX_FEATURE_LEN} characters."
                        ),
                        "recorded": False,
                        "http_status": 400,
                    }

        return None

    @staticmethod
    def _normalize_features(features: Any) -> List[str]:
        if not features:
            return []
        return [str(f).strip() for f in features if str(f).strip()]


