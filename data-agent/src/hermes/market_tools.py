"""
Hermes Agent Market Intelligence Tools

Provides structured analytical tools for the Hermes AI Agent to query
Bayesian prior distributions, monitor VPS tick streaming metrics, and format WhatsApp alerts.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from data_agent.src.bayesian.prior_updater import BayesianPriorUpdater
except ImportError:
    try:
        from src.bayesian.prior_updater import BayesianPriorUpdater
    except ImportError:
        from bayesian.prior_updater import BayesianPriorUpdater

logger = logging.getLogger("data_agent.hermes_tools")


class HermesMarketTools:
    """
    Tool registry for Hermes Agent.
    """

    def __init__(self, priors_updater: Optional[BayesianPriorUpdater] = None):
        self.priors_updater = priors_updater or BayesianPriorUpdater()

    def get_bayesian_summary(self) -> Dict[str, Any]:
        """Query current Bayesian prior distributions and aggregate stats."""
        priors = self.priors_updater.load_current_priors()
        total_wins = priors.get("total_wins", 0)
        total_losses = priors.get("total_losses", 0)
        total_trades = priors.get("total_trades", 0)

        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 50.0

        top_features = []
        for feat, counts in priors.get("feature_counts", {}).items():
            w = counts.get("win", 0)
            l = counts.get("loss", 0)
            t = w + l
            if t >= 10:
                feat_win_rate = (w / t) * 100
                top_features.append({
                    "feature": feat,
                    "win_rate": round(feat_win_rate, 2),
                    "samples": t,
                })

        top_features.sort(key=lambda x: x["win_rate"], reverse=True)

        return {
            "total_trades": total_trades,
            "overall_win_rate": round(win_rate, 2),
            "top_performing_features": top_features[:5],
        }

    def format_whatsapp_alert(
        self,
        asset: str,
        direction: str,
        confidence: float,
        bayesian_prob: float,
        reason: str,
    ) -> str:
        """Format trade signal notification for WhatsApp rendering."""
        icon = "🟢 CALL" if direction.upper() == "CALL" else "🔴 PUT"
        return (
            f"🎯 *OTC SNIPER - HIGH CONFIDENCE SIGNAL*\n\n"
            f"Asset: *{asset}*\n"
            f"Action: *{icon}*\n"
            f"Signal Confidence: *{confidence * 100:.1f}%*\n"
            f"Bayesian Probability: *{bayesian_prob * 100:.1f}%*\n"
            f"Rationale: {reason}\n\n"
            f"_Sent via VPS Data Agent & Hermes Supervisor_"
        )
