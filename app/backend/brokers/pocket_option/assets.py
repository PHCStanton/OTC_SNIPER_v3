"""Pocket Option asset normalization and verified OTC asset list."""

from __future__ import annotations

import logging

from ..base import Asset, AssetType, BrokerType

logger = logging.getLogger(__name__)


OTC_ASSETS = [
    "EURUSD_otc",
    "GBPUSD_otc",
    "USDJPY_otc",
    "AUDUSD_otc",
    "USDCAD_otc",
    "USDCHF_otc",
    "NZDUSD_otc",
    "EURJPY_otc",
    "EURGBP_otc",
    "EURAUD_otc",
    "EURCAD_otc",
    "AUDNZD_otc",
    "AUDJPY_otc",
]


def normalize_asset(value: str) -> str:
    if not value:
        return ""

    cleaned = value.strip().upper()
    if cleaned.endswith("_OTC"):
        cleaned = cleaned[:-4]

    for token in ("/", "-", "_", " "):
        cleaned = cleaned.replace(token, "")

    return "".join(ch for ch in cleaned if ch.isalnum())


def to_pocket_option_format(value: str) -> str:
    canonical = normalize_asset(value)
    return f"{canonical}_otc" if canonical else ""


def verify_otc_asset(value: str) -> bool:
    return to_pocket_option_format(value) in OTC_ASSETS


def build_asset_list() -> list[Asset]:
    assets: list[Asset] = []
    for asset_id in OTC_ASSETS:
        canonical = normalize_asset(asset_id)
        assets.append(
            Asset(
                id=canonical,
                name=asset_id.replace("_otc", " OTC"),
                asset_type=AssetType.OTC,
                payout=0.8,
                broker=BrokerType.POCKET_OPTION,
                raw_id=asset_id,
            )
        )
    return assets


def _get_live_payout_map() -> dict[str, float]:
    """
    Attempt to read live payout percentages from the pocketoptionapi asset_manager.

    Returns a dict mapping raw_id (e.g. 'EURUSD_otc') → payout fraction (e.g. 0.85).
    Returns an empty dict if the API is not connected or asset data is unavailable.
    The pocketoptionapi stores profit_percent as an integer percentage (e.g. 85),
    so we divide by 100 to normalise to a fraction.
    """
    try:
        import pocketoptionapi.global_value as gv  # type: ignore
        mgr = getattr(gv, "asset_manager", None)
        if mgr is None:
            return {}

        payout_map: dict[str, float] = {}
        for asset_obj in getattr(mgr, "assets", []):
            symbol = getattr(asset_obj, "symbol", None)
            profit_pct = getattr(asset_obj, "profit_percent", None)
            if symbol and profit_pct is not None:
                try:
                    payout_map[str(symbol)] = float(profit_pct) / 100.0
                except (TypeError, ValueError):
                    pass
        return payout_map
    except Exception as exc:
        logger.warning("Live payout map unavailable (falling back to static 80%%): %s", exc)
        return {}


def build_asset_list_with_live_payouts() -> list[Asset]:
    """
    Build the asset list, enriching each asset with a live payout percentage
    from the broker API when available.  Falls back to 0.80 (80%) when the
    broker has not yet sent asset data (e.g. before first connect).
    """
    live_payouts = _get_live_payout_map()
    if live_payouts:
        logger.debug("Live payout map loaded: %d assets", len(live_payouts))
    else:
        logger.debug("No live payout data available — using static 80%% fallback")

    assets: list[Asset] = []
    for asset_id in OTC_ASSETS:
        canonical = normalize_asset(asset_id)
        payout = live_payouts.get(asset_id, 0.8)
        assets.append(
            Asset(
                id=canonical,
                name=asset_id.replace("_otc", " OTC"),
                asset_type=AssetType.OTC,
                payout=payout,
                broker=BrokerType.POCKET_OPTION,
                raw_id=asset_id,
            )
        )
    return assets
