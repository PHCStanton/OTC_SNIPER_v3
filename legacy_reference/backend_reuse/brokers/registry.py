"""
Broker Registry — Discovers and manages broker adapter instances.

Usage:
    from brokers.registry import BrokerRegistry
    from brokers.base import BrokerType

    # Register an adapter (done at import time by each adapter module)
    BrokerRegistry.register(PocketOptionAdapter)

    # Get an adapter instance
    adapter = BrokerRegistry.get_adapter(BrokerType.POCKET_OPTION, "demo")

    # List available brokers
    available = BrokerRegistry.list_available()
"""

import logging
from typing import Dict, List, Type, Optional

from brokers.base import BrokerAdapter, BrokerType

logger = logging.getLogger("BrokerRegistry")


class BrokerRegistry:
    """Central registry for broker adapters. Singleton pattern via class methods."""

    _adapters: Dict[BrokerType, Type[BrokerAdapter]] = {}
    _instances: Dict[str, BrokerAdapter] = {}

    @classmethod
    def register(cls, adapter_class: Type[BrokerAdapter]) -> None:
        """
        Register a broker adapter class.

        Called at import time by each adapter module.

        Args:
            adapter_class: A subclass of BrokerAdapter with broker_type set.

        Raises:
            ValueError: If adapter_class does not have broker_type set.
        """
        if not hasattr(adapter_class, "broker_type") or adapter_class.broker_type is None:
            raise ValueError(
                f"Adapter {adapter_class.__name__} must set broker_type class attribute"
            )
        cls._adapters[adapter_class.broker_type] = adapter_class
        logger.info(
            "Registered broker adapter: %s (%s)",
            adapter_class.display_name,
            adapter_class.broker_type.value,
        )

    @classmethod
    def get_adapter(cls, broker: BrokerType, account_key: str = "default") -> BrokerAdapter:
        """
        Get or create a broker adapter instance.

        Args:
            broker:      BrokerType enum value.
            account_key: Unique key for this account (e.g., "demo", "real").

        Returns:
            BrokerAdapter instance.

        Raises:
            KeyError: If no adapter is registered for the given broker type.
        """
        key = f"{broker.value}:{account_key}"
        if key not in cls._instances:
            if broker not in cls._adapters:
                raise KeyError(f"No adapter registered for broker: {broker.value}")
            cls._instances[key] = cls._adapters[broker]()
            logger.info("Created adapter instance: %s", key)
        return cls._instances[key]

    @classmethod
    def list_available(cls) -> List[Dict]:
        """
        List all registered broker adapters.

        Returns:
            List of dicts with 'type', 'name', 'supports_otc', 'supports_demo'.
        """
        return [
            {
                "type": bt.value,
                "name": cls._adapters[bt].display_name,
                "supports_otc": cls._adapters[bt].supports_otc,
                "supports_demo": cls._adapters[bt].supports_demo,
            }
            for bt in cls._adapters
        ]

    @classmethod
    def remove_instance(cls, broker: BrokerType, account_key: str = "default") -> None:
        """Remove a specific adapter instance (e.g., on disconnect)."""
        key = f"{broker.value}:{account_key}"
        cls._instances.pop(key, None)

    @classmethod
    def clear(cls) -> None:
        """Remove all instances. Used in testing."""
        cls._instances.clear()
