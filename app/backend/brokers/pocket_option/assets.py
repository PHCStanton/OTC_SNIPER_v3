"""Pocket Option asset normalization and live asset list builder."""

from __future__ import annotations

import json
import logging

from ..base import Asset, AssetType, BrokerType

logger = logging.getLogger(__name__)


_FALLBACK_OTC_ASSETS = [
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
    """Strip OTC suffix and non-alphanumeric chars, return uppercase canonical ID."""
    if not value:
        return ""

    cleaned = value.strip().upper()
    if cleaned.endswith("_OTC"):
        cleaned = cleaned[:-4]

    for token in ("/", "-", "_", " "):
        cleaned = cleaned.replace(token, "")

    return "".join(ch for ch in cleaned if ch.isalnum())


def to_pocket_option_format(raw_id: str) -> str:
    """
    Return the raw_id as-is if it already contains an underscore (e.g. 'EURUSD_otc',
    '#BA_otc', 'TSLA_otc'). Only apply normalization + _otc suffix for plain symbols
    that have no underscore (legacy path).
    """
    if not raw_id:
        return ""

    if "_" in raw_id:
        return raw_id

    canonical = normalize_asset(raw_id)
    return f"{canonical}_otc" if canonical else ""


def _infer_asset_type(symbol: str, category: str) -> AssetType:
    symbol_lower = symbol.lower()
    category_lower = category.strip().lower()

    if "_otc" in symbol_lower:
        return AssetType.OTC
    if category_lower == "stock" or symbol.startswith("#"):
        return AssetType.STOCK
    if category_lower == "crypto":
        return AssetType.CRYPTO
    return AssetType.FOREX


def _load_live_assets() -> list[Asset]:
    try:
        import pocketoptionapi.global_value as gv  # type: ignore

        payout_data = getattr(gv, "PayoutData", None)
        if not payout_data:
            return []

        if isinstance(payout_data, bytes):
            payout_data = payout_data.decode("utf-8")

        payload = json.loads(payout_data) if isinstance(payout_data, str) else payout_data
        if not isinstance(payload, list):
            logger.warning("Pocket Option payout payload is not a list: %s", type(payload).__name__)
            return []

        assets: list[Asset] = []
        seen_symbols: set[str] = set()

        for entry in payload:
            if not isinstance(entry, list) or len(entry) < 6:
                continue

            symbol = str(entry[1]).strip() if entry[1] is not None else ""
            if not symbol or symbol in seen_symbols:
                continue

            name = str(entry[2]).strip() if entry[2] is not None else symbol
            category = str(entry[3]).strip() if entry[3] is not None else ""

            try:
                payout = float(entry[5]) / 100.0
            except (TypeError, ValueError):
                payout = 0.0

            assets.append(
                Asset(
                    id=normalize_asset(symbol),
                    name=name or symbol,
                    asset_type=_infer_asset_type(symbol, category),
                    payout=payout,
                    broker=BrokerType.POCKET_OPTION,
                    raw_id=symbol,
                    metadata={"category": category},
                )
            )
            seen_symbols.add(symbol)

        return assets
    except Exception as exc:
        logger.warning("Failed to read Pocket Option payout data: %s", exc)
        return []


def verify_asset_tradeable(raw_id: str) -> bool:
    """Verify if an asset is valid for trading."""
    if not raw_id:
        return False

    asset_id = raw_id.strip()
    pocket_asset = to_pocket_option_format(asset_id)
    live_assets = _load_live_assets()

    if live_assets:
        live_raw_ids = {asset.raw_id for asset in live_assets}
        live_ids = {asset.id for asset in live_assets}
        return asset_id in live_raw_ids or pocket_asset in live_raw_ids or normalize_asset(asset_id) in live_ids

    return asset_id in _FALLBACK_OTC_ASSETS or pocket_asset in _FALLBACK_OTC_ASSETS


def build_asset_list_with_live_payouts() -> list[Asset]:
    """Build the full asset list from the broker's live payout payload."""
    live_assets = _load_live_assets()
    if live_assets:
        logger.debug("Live asset list: %d available assets from Pocket Option payout data", len(live_assets))
        return live_assets

    logger.debug("Broker not connected — returning minimal fallback asset list")
    return [
        Asset(
            id=normalize_asset(asset_id),
            name=asset_id.replace("_otc", " OTC"),
            asset_type=AssetType.OTC,
            payout=0.8,
            broker=BrokerType.POCKET_OPTION,
            raw_id=asset_id,
        )
        for asset_id in _FALLBACK_OTC_ASSETS
    ]
