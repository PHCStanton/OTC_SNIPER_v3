"""
Settings Manager — B7 (2026-03-21)
===================================
Manages platform-wide global settings, broker settings, and account settings.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict

import sys
from pathlib import Path

# Ensure backend directory is in sys.path for broker imports
_backend_dir = str(Path(__file__).resolve().parents[1])
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from brokers.base import BrokerType

logger = logging.getLogger("SettingsManager")

class SettingsManager:
    """Manages system configuration using JSON files."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.settings_dir = self.data_dir / "settings"
        self.global_path = self.settings_dir / "global.json"
        
        # Ensure directories exist
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        (self.settings_dir / "brokers").mkdir(parents=True, exist_ok=True)
        (self.settings_dir / "accounts").mkdir(parents=True, exist_ok=True)
        
        # Create default global.json if missing
        if not self.global_path.exists():
            self._write_default_global()

    def _write_default_global(self) -> None:
        """Create the default global settings file."""
        default_global = {
            "version": 1,
            "theme": "dark",
            "timezone": "UTC",
            "language": "en",
            "data_retention_days": 30,
            "log_level": "INFO",
            "oteo": {
                "warmup_ticks": 50,
                "cooldown_ticks": 30,
                "multi_timeframe": True,
                "manipulation_suppression": True,
                "volatility_adaptive": True
            },
            "ghost_trading": {
                "enabled": False,
                "default_amount": 10.0,
                "auto_record_high_signals": True
            },
            "tick_logging": {
                "enabled": True,
                "ticks_per_file": 500,
                "expiry_minutes": 30,
                "archive_expired": True
            },
            "multi_chart": {
                "default_grid": "2x2",
                "max_assets": 9,
                "render_throttle_ms": 100
            },
            "trading": {
                "max_concurrent_trades": 3,
                "default_amount": 10.0,
                "default_expiration": 60,
                "allow_same_asset_trades": False,
                "cooldown_between_trades_ms": 1000
            }
        }
        try:
            with open(self.global_path, "w", encoding="utf-8") as f:
                json.dump(default_global, f, indent=2)
            logger.info("Created default global.json settings file.")
        except IOError as e:
            logger.error("Failed to write default global settings: %s", e)

    def get_global(self) -> Dict[str, Any]:
        """Get platform-wide settings."""
        try:
            with open(self.global_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.error("Failed to read global settings: %s", e)
            return {}

    def get_broker(self, broker: BrokerType) -> Dict[str, Any]:
        """Get broker-specific settings. (Phase F stub)"""
        return {}

    def get_account(self, broker: BrokerType, account: str) -> Dict[str, Any]:
        """Get account-specific settings. (Phase F stub)"""
        return {}

    def update(self, scope: str, key: str, value: Any) -> None:
        """Update a setting. (Phase C stub)"""
        pass

    def export_for_migration(self) -> dict:
        """Export all settings for database migration. (Phase F stub)"""
        return {}
