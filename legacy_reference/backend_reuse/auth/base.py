"""
Authentication Architecture — Base Classes
========================================
Abstract base class for all authentication providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class Session:
    """User session data."""
    token: str
    user_id: str
    username: str
    role: str
    expires_at: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class AuthProvider(ABC):
    """
    Abstract base class for all auth integrations.
    """

    @abstractmethod
    async def authenticate(self, credentials: Dict[str, str]) -> Session:
        """
        Authenticate a user and return a session.
        """
        ...

    @abstractmethod
    async def validate_session(self, token: str) -> bool:
        """
        Check if a session token is valid.
        """
        ...

    @abstractmethod
    async def refresh_session(self, token: str) -> Session:
        """
        Refresh an existing session.
        """
        ...

    @abstractmethod
    async def revoke_session(self, token: str) -> None:
        """
        Revoke a session token.
        """
        ...
