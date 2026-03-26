"""Pocket Option asset normalization and verified OTC asset list."""

from __future__ import annotations

from ..base import Asset, AssetType, BrokerType


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
