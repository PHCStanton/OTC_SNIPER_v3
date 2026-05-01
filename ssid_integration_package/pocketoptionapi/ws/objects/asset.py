"""Module for Pocket Option Asset objects and AssetManager."""

import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


class Asset:
    """Represents a single tradeable asset."""

    def __init__(self, raw: list):
        """
        Initialize from raw asset array received from the server.

        Expected format (14+ elements):
          [id, symbol, name, ?, ?, ?, ?, ?, profit_percent, ?, ?, is_available, ?, category, ...]
        Indices are best-effort based on observed Pocket Option protocol data.
        """
        try:
            self.id = raw[0] if len(raw) > 0 else None
            self.symbol = str(raw[1]) if len(raw) > 1 else "UNKNOWN"
            self.name = str(raw[2]) if len(raw) > 2 else self.symbol
            self.profit_percent = float(raw[8]) if len(raw) > 8 else 0.0
            # is_available: treat any truthy value as available
            self.is_available = bool(raw[11]) if len(raw) > 11 else False
            self.category = str(raw[13]).lower() if len(raw) > 13 else "unknown"
            self._raw = raw
        except Exception as e:
            logger.warning(f"Asset parse warning for raw={raw}: {e}")
            self.id = None
            self.symbol = "UNKNOWN"
            self.name = "UNKNOWN"
            self.profit_percent = 0.0
            self.is_available = False
            self.category = "unknown"
            self._raw = raw

    @property
    def is_trading_allowed(self) -> bool:
        """Whether this asset is currently available for trading."""
        return self.is_available

    def __repr__(self):
        return f"<Asset {self.symbol} available={self.is_available} profit={self.profit_percent}%>"


class AssetManager:
    """Manages the full collection of assets received from the server."""

    def __init__(self):
        self.assets: List[Asset] = []
        self._by_symbol: Dict[str, Asset] = {}
        self._by_category: Dict[str, List[Asset]] = {}

    def process_assets(self, data: list):
        """
        Process raw asset list from server response.

        Args:
            data: List of raw asset arrays (each array has 14+ elements)
        """
        if not isinstance(data, list):
            logger.error(f"process_assets: expected list, got {type(data)}")
            return

        self.assets = []
        self._by_symbol = {}
        self._by_category = {}

        for raw in data:
            try:
                asset = Asset(raw)
                self.assets.append(asset)
                self._by_symbol[asset.symbol] = asset
                cat = asset.category
                if cat not in self._by_category:
                    self._by_category[cat] = []
                self._by_category[cat].append(asset)
            except Exception as e:
                logger.warning(f"Skipping malformed asset entry: {e}")

        logger.debug(f"AssetManager: loaded {len(self.assets)} assets across {len(self._by_category)} categories")

    def get_all_assets(self) -> List[Asset]:
        """Return all known assets."""
        return list(self.assets)

    def get_assets_by_type(self, category: str) -> List[Asset]:
        """Return all assets in a given category (e.g. 'otc', 'forex')."""
        return list(self._by_category.get(category.lower(), []))

    def get_asset_by_symbol(self, symbol: str) -> Optional[Asset]:
        """Return asset by its symbol string, or None if not found."""
        return self._by_symbol.get(symbol)

    def get_profitable_assets(self, min_profit: float = None) -> List[Asset]:
        """
        Return assets sorted by profit_percent descending.

        Args:
            min_profit: Optional minimum profit threshold to filter by.
        """
        candidates = [a for a in self.assets if a.is_available]
        if min_profit is not None:
            candidates = [a for a in candidates if a.profit_percent >= min_profit]
        return sorted(candidates, key=lambda a: a.profit_percent, reverse=True)

    def analyze_by_category(self) -> Dict[str, dict]:
        """
        Return summary statistics grouped by category.

        Returns:
            dict: { category: { 'total': int, 'available': int, 'unavailable': int } }
        """
        result = {}
        for cat, assets in self._by_category.items():
            available = sum(1 for a in assets if a.is_available)
            result[cat] = {
                "total": len(assets),
                "available": available,
                "unavailable": len(assets) - available,
            }
        return result
