"""
asset_utils.py — Shared Asset Name Normalization
=================================================
Single source of truth for asset name normalization across the OTC SNIPER backend.

Aligned with QuFLX-v2 canonical standard (backend/utils/asset_utils.py).

Three normalization contexts:
  Context 1 — Internal Key:     EURUSDOTC  (Redis keys, filesystem, cache, subscriptions)
  Context 2 — PocketOption API: EURUSD_otc (trade execution WebSocket format)
  Context 3 — UI Display:       EUR/USD OTC (human-readable labels — handled in frontend)

Usage:
    from asset_utils import normalize_asset, to_pocket_option_format

    normalize_asset("EURUSD_OTC")   → "EURUSDOTC"
    normalize_asset("EURUSD_otc")   → "EURUSDOTC"
    normalize_asset("#EURUSD")      → "EURUSDOTC"  (# stripped — intentional for internal keys)
    normalize_asset("EURUSD-OTC")   → "EURUSDOTC"
    normalize_asset("OTCQ-EURUSD")  → "OTCQEURUSD" (prefix preserved as alphanumeric)
    normalize_asset("eurusd_otc")   → "EURUSDOTC"
    normalize_asset("")             → ""

    to_pocket_option_format("EURUSDOTC")  → "EURUSD_otc"
    to_pocket_option_format("BTCUSDOTC")  → "BTCUSD_otc"
    to_pocket_option_format("AAPLOTC")    → "AAPL_otc"
"""

import re


def normalize_asset(raw: str) -> str:
    """
    Normalize an asset name to the canonical internal key format.

    Strips ALL non-alphanumeric characters and converts to uppercase.
    This is Context 1 normalization — used for Redis keys, filesystem
    directories, cache keys, tick matching, and Socket.IO room names.

    Examples:
        normalize_asset("EURUSD_otc")   → "EURUSDOTC"
        normalize_asset("EUR/USD OTC")  → "EURUSDOTC"
        normalize_asset("EURUSD_OTC")   → "EURUSDOTC"
        normalize_asset("BTCUSD_otc")   → "BTCUSDOTC"
        normalize_asset("#AAPL_otc")    → "AAPLOTC"   (# stripped — intentional)
        normalize_asset("eurusd")       → "EURUSD"    (non-OTC Forex pair)

    NOTE: Stock symbols with '#' prefix (e.g. '#AAPL_otc') will have
    the '#' stripped → 'AAPLOTC'. This is intentional for internal key
    consistency. Use to_pocket_option_format() when sending to the API.

    Returns:
        Canonical uppercase alphanumeric key, e.g. "EURUSDOTC".
        Empty string if input is empty or None.
    """
    if not raw:
        return ""
    return re.sub(r"[^A-Za-z0-9]", "", str(raw)).upper()


def to_pocket_option_format(asset: str) -> str:
    """
    Convert a canonical internal key to PocketOption API format.

    This is Context 2 normalization — used ONLY when sending trade orders
    to the PocketOption WebSocket API. The API expects UPPERCASE base with
    lowercase '_otc' suffix.

    Examples:
        to_pocket_option_format("EURUSDOTC")  → "EURUSD_otc"
        to_pocket_option_format("BTCUSDOTC")  → "BTCUSD_otc"
        to_pocket_option_format("AAPLOTC")    → "AAPL_otc"
        to_pocket_option_format("EURUSD")     → "EURUSD"  (non-OTC, no suffix added)

    NOTE: This function assumes the input is already in canonical format
    (output of normalize_asset()). Do not pass raw PocketOption strings.

    Returns:
        PocketOption API format string, e.g. "EURUSD_otc".
        Empty string if input is empty or None.
    """
    if not asset:
        return ""
    s = str(asset).strip().upper()
    if s.endswith("OTC"):
        base = s[:-3]  # strip trailing OTC
        return f"{base}_otc"
    return s
