"""Base Filter Class — Abstract interface for decoupled gate plugins in Data Agent."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple


class BaseFilter(ABC):
    """Abstract Base Class for all modular data agent filters/gates."""

    def __init__(self, name: str, enabled: bool = True, config: Dict[str, Any] | None = None):
        self.name = name
        self.enabled = enabled
        self.config = config or {}

    @abstractmethod
    def evaluate(self, tick_data: Dict[str, Any], market_context: Dict[str, Any] | None = None) -> Tuple[bool, str | None]:
        """
        Evaluate filter rules against a tick/signal.

        Returns:
            Tuple[bool, str | None]: (Passed filter, Veto reason if rejected)
        """
        pass
