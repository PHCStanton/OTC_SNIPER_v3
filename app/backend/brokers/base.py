"""Broker abstraction layer shared across all broker integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional


class BrokerType(str, Enum):
    POCKET_OPTION = "pocket_option"
    DERIV = "deriv"
    BINANCE = "binance"


class AssetType(str, Enum):
    OTC = "otc"
    FOREX = "forex"
    CRYPTO = "crypto"
    STOCK = "stock"


@dataclass(slots=True)
class Asset:
    id: str
    name: str
    asset_type: AssetType
    payout: float
    broker: BrokerType
    raw_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Tick:
    timestamp: float
    asset: str
    price: float
    volume: float = 0.0
    broker: Optional[BrokerType] = None


@dataclass(slots=True)
class TradeOrder:
    asset_id: str
    direction: str
    amount: float
    expiration: int
    order_type: str = "market"
    broker: Optional[BrokerType] = None


@dataclass(slots=True)
class TradeResult:
    success: bool
    trade_id: Optional[str] = None
    message: str = ""
    entry_price: Optional[float] = None
    broker: Optional[BrokerType] = None


@dataclass(slots=True)
class Balance:
    demo: float = 0.0
    real: float = 0.0
    currency: str = "USD"
    broker: Optional[BrokerType] = None


class BrokerAdapter(ABC):
    broker_type: BrokerType
    display_name: str
    supports_otc: bool = False
    supports_demo: bool = False

    @abstractmethod
    async def connect(self, credentials: Dict[str, str]) -> bool:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...

    @abstractmethod
    async def get_assets(self, demo: bool = True) -> List[Asset]:
        ...

    @abstractmethod
    async def subscribe_ticks(self, asset: str) -> AsyncIterator[Tick]:
        ...

    @abstractmethod
    async def execute_trade(self, order: TradeOrder) -> TradeResult:
        ...

    @abstractmethod
    async def get_balance(self, demo: bool = True) -> Balance:
        ...

    @abstractmethod
    async def get_trade_history(self, limit: int = 50) -> List[Dict]:
        ...

    @abstractmethod
    def get_connection_status(self) -> str:
        ...
