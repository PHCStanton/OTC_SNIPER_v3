#!/usr/bin/env python3
"""
SSID Integration Package - OTC Trade Executor
Extracted from working otc_trade_executor.py (the CLI that works)

⭐ CRITICAL: This is the PROVEN method for real OTC trades
- No demo fallback (like broken TUI had)
- Hardcoded OTC asset validation
- Connection check before each trade
"""

import os
import sys
import time
import logging
import threading
from typing import Dict, Any, Tuple, Optional
from enum import Enum

# Add PocketOptionAPI to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'PocketOptionAPI-v2'))


class TradeDirection(Enum):
    """Trade direction enum (matches working CLI)"""
    BUY = "call"     # CALL/BUY (Price goes UP)
    SELL = "put"     # PUT/SELL (Price goes DOWN)


class OTCExecutor:
    """
    OTC Trade Executor - PROVEN WORKING PATTERN

    ⭐ CRITICAL INSIGHTS from fixing TUI:
    - Hardcoded OTC assets from working CLI (NOT dynamic/dynamic failed)
    - Always check_connection() before trade
    - Use exact parameters from working CLI
    - NO demo fallback condition
    """

    # ⭐ CRITICAL: Hardcoded OTC assets from WORKING CLI
    # These are the ONLY assets that work reliably
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
        "AUDJPY_otc"
    ]

    def __init__(self, connector):
        """
        Initialize OTC executor with SSID connector

        Args:
            connector: SSIDConnector instance (must be connected)
        """
        self.connector = connector
        self.logger = logging.getLogger(__name__)
        self._lock = threading.Lock()

        if not connector.is_connected:
            raise ValueError("SSIDConnector must be connected before creating OTCExecutor")

        self.logger.info("OTC Executor initialized with working pattern")

    def execute_trade(self, asset: str, direction: str, amount: float = 10.0,
                     expiration: int = 300) -> Dict[str, Any]:
        """
        Execute REAL OTC trade - THE WORKING PATTERN

        ⭐ CRITICAL: This matches the exact pattern from otc_trade_executor.py

        Args:
            asset: OTC asset symbol (e.g., 'EURUSD_otc')
            direction: 'call' or 'put' (string, not enum)
            amount: Trade amount in USD
            expiration: Expiration time in seconds

        Returns:
            Dict with trade result
        """
        # Validate inputs (CLI-style validation)
        validation_error = self._validate_trade_params(asset, direction, amount)
        if validation_error:
            return self._error_response(validation_error)

        # ⭐ CRITICAL INSIGHT: Always check connection before trade
        if not self.connector.check_connection():
            return self._error_response("Connection lost before trade")

        try:
            self.logger.info("=" * 60)
            self.logger.info("EXECUTING REAL OTC TRADE")
            self.logger.info("=" * 60)
            self.logger.info(f"  Asset:      {asset}")
            self.logger.info(f"  Direction:  {direction.upper()}")
            self.logger.info(f"  Amount:     ${amount}")
            self.logger.info(f"  Expiration: {expiration}s")
            self.logger.info(f"  Balance:    ${self.connector.balance:,.2f}")
            self.logger.info("=" * 60)

            # ⭐ CRITICAL: This is the EXACT same call as working CLI
            # Wrapped in lock for thread safety (parallel execution support)
            with self._lock:
                result = self.connector.api.buy(
                    amount=amount,
                    active=asset,
                    action=direction.lower(),  # "call"/"put" - string
                    expirations=expiration
                )

            # Parse result (same as working CLI)
            if result and result[0]:
                order_id = result[1]
                self.logger.info(f"✅ TRADE EXECUTED SUCCESSFULLY")
                self.logger.info(f"   Order ID: {order_id}")
                self.logger.info(f"   Timestamp: {time.time()}")

                return {
                    'success': True,
                    'order_id': str(order_id),
                    'asset': asset,
                    'direction': direction,
                    'amount': amount,
                    'expiration': expiration,
                    'message': f"✅ Trade executed. Order ID: {order_id}",
                    'timestamp': time.time()
                }
            else:
                error_msg = f"API returned: {result}"
                self.logger.error(f"❌ TRADE FAILED: {error_msg}")
                return self._error_response(error_msg)

        except Exception as e:
            self.logger.error(f"❌ Exception during trade: {e}")
            return self._error_response(str(e))

    def _validate_trade_params(self, asset: str, direction: str, amount: float) -> Optional[str]:
        """
        Validate trade parameters (CLI-style)

        Args:
            asset: Asset symbol
            direction: 'call' or 'put'
            amount: Trade amount

        Returns:
            Error message or None
        """
        # Asset must be OTC format
        if not asset.endswith('_otc'):
            return f"Invalid asset. Must end with '_otc': {asset}"

        # ⭐ CRITICAL: Asset must be in hardcoded working list
        if asset not in self.OTC_ASSETS:
            available = ', '.join(self.OTC_ASSETS[:5]) + "..."
            return f"Asset not in verified OTC list. Available: {available}"

        # Direction validation
        if direction.lower() not in ['call', 'put']:
            return "Direction must be 'call' or 'put'"

        # Amount validation
        if amount <= 0:
            return "Amount must be greater than 0"

        # Balance check (CLI-style)
        if self.connector.balance and amount > self.connector.balance:
            return f"Insufficient balance: ${self.connector.balance} < ${amount}"

        return None

    def check_trade_result(self, order_id: str) -> Dict[str, Any]:
        """
        Check if trade won or lost

        Args:
            order_id: Order ID from execute_trade

        Returns:
            Dict with result
        """
        if not self.connector.is_connected:
            return {
                'success': False,
                'error': 'Not connected to Pocket Option'
            }

        try:
            with self._lock:
                result = self.connector.api.check_win(order_id)

            # Parse result (matches working CLI pattern)
            if isinstance(result, tuple) and len(result) >= 2:
                profit, status = result[0], result[1]
                win = status == "win"
                return {
                    'success': True,
                    'win': win,
                    'profit': float(profit),
                    'message': f'{"WIN" if win else "LOSS"}: ${profit:,.2f}'
                }
            elif isinstance(result, dict):
                profit = result.get('profit', 0.0)
                win = profit > 0
                return {
                    'success': True,
                    'win': win,
                    'profit': float(profit),
                    'message': f'{"WIN" if win else "LOSS"}: ${profit:,.2f}'
                }
            else:
                return {
                    'success': True,
                    'pending': True,
                    'message': 'Result pending...'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f"Check result error: {str(e)}"
            }

    def get_available_assets(self) -> list:
        """
        Get list of verified OTC assets

        Returns:
            List of asset symbols
        """
        return self.OTC_ASSETS.copy()

    def is_valid_asset(self, asset: str) -> bool:
        """
        Check if asset is valid for trading

        Args:
            asset: Asset symbol to check

        Returns:
            bool: True if in verified list
        """
        return asset in self.OTC_ASSETS

    def _error_response(self, message: str) -> Dict[str, Any]:
        """Generate error response"""
        return {
            'success': False,
            'error': message,
            'timestamp': time.time()
        }


# Quick usage example
if __name__ == "__main__":
    import json
    from ssid_connector import SSIDConnector

    # Load example SSID
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'pocket_option_config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        ssid = config.get('ssid')
    except:
        print("No config found - run test_ssid_fixed.py first")
        sys.exit(1)

    # Connect and trade
    connector = SSIDConnector(ssid, demo=False)

    success, msg = connector.connect()
    if not success:
        print(f"Connection failed: {msg}")
        connector.disconnect()
        sys.exit(1)

    print(f"Connected! Balance: ${connector.balance}")

    # Execute sample trade
    executor = OTCExecutor(connector)

    result = executor.execute_trade(
        asset="EURUSD_otc",
        direction="call",
        amount=10.0,
        expiration=300
    )

    if result['success']:
        print(f"Trade executed: {result['message']}")

        # Wait and check result
        print("Waiting 5 minutes for trade result...")
        time.sleep(300)

        result_check = executor.check_trade_result(result['order_id'])
        print(f"Result: {result_check['message']}")

    else:
        print(f"Trade failed: {result['error']}")

    connector.disconnect()
