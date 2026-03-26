"""Broker adapter registry."""

from __future__ import annotations

import logging
from typing import Dict, List, Type

from .base import BrokerAdapter, BrokerType

logger = logging.getLogger(__name__)


class BrokerRegistry:
    _adapters: Dict[BrokerType, Type[BrokerAdapter]] = {}
    _instances: Dict[str, BrokerAdapter] = {}

    @classmethod
    def register(cls, adapter_class: Type[BrokerAdapter]) -> None:
        if not hasattr(adapter_class, "broker_type") or adapter_class.broker_type is None:
            raise ValueError(f"Adapter {adapter_class.__name__} must define broker_type")
        cls._adapters[adapter_class.broker_type] = adapter_class
        logger.info("Registered broker adapter: %s", adapter_class.__name__)

    @classmethod
    def get_adapter(cls, broker: BrokerType, account_key: str = "primary") -> BrokerAdapter:
        instance_key = f"{broker.value}:{account_key}"
        if instance_key not in cls._instances:
            if broker not in cls._adapters:
                raise KeyError(f"No adapter registered for broker: {broker.value}")
            cls._instances[instance_key] = cls._adapters[broker]()
            logger.info("Created broker adapter instance: %s", instance_key)
        return cls._instances[instance_key]

    @classmethod
    def list_available(cls) -> List[Dict]:
        return [
            {
                "type": broker.value,
                "name": adapter.display_name,
                "supports_otc": adapter.supports_otc,
                "supports_demo": adapter.supports_demo,
            }
            for broker, adapter in cls._adapters.items()
        ]

    @classmethod
    def remove_instance(cls, broker: BrokerType, account_key: str = "primary") -> None:
        cls._instances.pop(f"{broker.value}:{account_key}", None)

    @classmethod
    def clear(cls) -> None:
        cls._instances.clear()
