"""
Broker Abstraction Layer — Base Classes & Data Models
=====================================================
Every broker integration (Pocket Option, Deriv, Binance, etc.) MUST implement
the BrokerAdapter abstract base class defined here.

To add a new broker:
  1. Copy brokers/_template/ to brokers/{broker_name}/
  2. Implement all abstract methods in adapter.py
  3. Register the adapter in brokers/registry.py

Data models (Asset, Tick, TradeOrder, TradeResult, Balance) are shared across
all brokers to ensure consistent data flow through the system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, Dict, List, Optional, Any


class BrokerType(str, Enum):
    """Supported broker identifiers. Add new brokers here."""
    POCKET_OPTION = "pocket_option"
    DERIV = "deriv"
    BINANCE = "binance"


class AssetType(str, Enum):
    """Asset classification."""
    OTC = "otc"
    FOREX = "forex"
    CRYPTO = "crypto"
    STOCK = "stock"


@dataclass
class Asset:
    """Normalized asset representation shared across all brokers."""
    id: str                              # Normalized ID (e.g., "EURUSD")
    name: str                            # Display name (e.g., "EUR/USD OTC")
    asset_type: AssetType                # OTC, FOREX, CRYPTO, STOCK
    payout: float                        # Payout percentage (binary options)
    broker: BrokerType                   # Which broker this asset belongs to
    raw_id: str                          # Broker's native ID (for API calls)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Tick:
    """Single price tick from any broker."""
    timestamp: float                     # Unix timestamp
    asset: str                           # Normalized asset name
    price: float                         # Current price
    volume: float = 0.0                  # Volume (0.0 if unavailable)
    broker: Optional[BrokerType] = None  # Source broker


@dataclass
class TradeOrder:
    """Trade order submitted to a broker."""
    asset_id: str                        # Normalized asset ID
    direction: str                       # "call" / "put" / "buy" / "sell"
    amount: float                        # Trade amount in account currency
    expiration: int                      # Seconds (binary options) or 0 (spot)
    order_type: str = "market"           # "market" / "limit"
    broker: Optional[BrokerType] = None  # Target broker


@dataclass
class TradeResult:
    """Result of a trade execution."""
    success: bool
    trade_id: Optional[str] = None
    message: str = ""
    entry_price: Optional[float] = None
    broker: Optional[BrokerType] = None


@dataclass
class Balance:
    """Account balance from a broker."""
    demo: float = 0.0
    real: float = 0.0
    currency: str = "USD"
    broker: Optional[BrokerType] = None


class BrokerAdapter(ABC):
    """
    Abstract base class for all broker integrations.

    Every broker adapter MUST implement all abstract methods.
    The adapter is the single point of contact between the OTC SNIPER
    platform and a specific broker's API.

    Class attributes (set by subclass):
        broker_type:   BrokerType enum value
        display_name:  Human-readable broker name
        supports_otc:  Whether this broker offers OTC assets
        supports_demo: Whether this broker offers demo accounts
    """

    broker_type: BrokerType
    display_name: str
    supports_otc: bool = False
    supports_demo: bool = False

    @abstractmethod
    async def connect(self, credentials: Dict[str, str]) -> bool:
        """
        Connect to the broker using provided credentials.

        Args:
            credentials: Broker-specific credentials dict.
                Pocket Option: {"ssid": "..."}
                Deriv:         {"api_token": "..."}
                Binance:       {"api_key": "...", "api_secret": "..."}

        Returns:
            True if connection successful, False otherwise.
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the broker. Clean up resources."""
        ...

    @abstractmethod
    async def get_assets(self, demo: bool = True) -> List[Asset]:
        """
        Fetch available assets from the broker.

        Args:
            demo: If True, fetch demo assets. If False, fetch real assets.

        Returns:
            List of Asset objects with normalized IDs.
        """
        ...

    @abstractmethod
    async def subscribe_ticks(self, asset: str) -> AsyncIterator[Tick]:
        """
        Subscribe to live tick data for an asset.

        Args:
            asset: Normalized asset ID (e.g., "EURUSD")

        Yields:
            Tick objects as they arrive from the broker.
        """
        ...

    @abstractmethod
    async def execute_trade(self, order: TradeOrder) -> TradeResult:
        """
        Execute a trade on the broker.

        Args:
            order: TradeOrder with asset, direction, amount, expiration.

        Returns:
            TradeResult indicating success/failure.
        """
        ...

    @abstractmethod
    async def get_balance(self, demo: bool = True) -> Balance:
        """
        Get current account balance.

        Args:
            demo: If True, return demo balance. If False, return real balance.

        Returns:
            Balance object with demo and/or real amounts.
        """
        ...

    @abstractmethod
    async def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """
        Get recent trade history.

        Args:
            limit: Maximum number of trades to return.

        Returns:
            List of trade dicts (broker-specific format is acceptable).
        """
        ...

    @abstractmethod
    def get_connection_status(self) -> str:
        """
        Get current connection status.

        Returns:
            One of: "connected", "disconnected", "connecting", "error"
        """
        ...
