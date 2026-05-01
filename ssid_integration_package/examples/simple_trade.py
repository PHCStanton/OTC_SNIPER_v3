#!/usr/bin/env python3
"""
SSID Integration Package - Simple Trade Example

Shows how to execute a single OTC trade after successful connection.
⚠️ WARNING: This executes REAL MONEY TRADES!
"""

import os
import sys
import json
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

# Add package to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ssid_integration_package.core.ssid_connector import SSIDConnector
from ssid_integration_package.core.otc_executor import OTCExecutor


def main():
    """Simple trade example"""
    print("💰 SSID Integration Package - Simple Trade Example")
    print("=" * 60)
    print("⚠️  WARNING: This executes REAL MONEY TRADES!")
    print("💵 Test with small amounts ($1-5) first")
    print("=" * 60)

    # Load SSID from config
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'pocket_option_config.json')

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        ssid = config.get('ssid')
        demo = config.get('is_demo', False)

        if not ssid:
            print("❌ ERROR: No SSID found in config")
            print(f"Please update {config_path}")
            return

    except FileNotFoundError:
        print("❌ ERROR: Config file not found")
        print("Please create config/pocket_option_config.json with your SSID")
        return

    # Create connector
    print(f"🔧 Creating SSID Connector (demo={demo})...")
    connector = SSIDConnector(ssid, demo=demo)

    # Connect
    print("📡 Connecting to Pocket Option...")
    success, message = connector.connect()

    if not success:
        print(f"❌ Connection failed: {message}")
        return

    print(f"✅ Connected: {message}")
    print(f"   Current Balance: ${connector.balance:,.2f}")

    # Create executor
    print("\n🚀 Creating OTC Executor...")
    executor = OTCExecutor(connector)

    # Execute trade
    trade_params = {
        'asset': "EURUSD_otc",  # Must be verified asset
        'direction': "call",    # "call" or "put"
        'amount': 5.0,          # Small test amount
        'expiration': 300       # 5 minutes
    }

    print(f"\n📈 Executing trade...")
    print(f"   Asset: {trade_params['asset']}")
    print(f"   Direction: {trade_params['direction'].upper()}")
    print(f"   Amount: ${trade_params['amount']}")
    print(f"   Expiration: {trade_params['expiration']}s")

    result = executor.execute_trade(**trade_params)

    if result['success']:
        print(f"\n✅ Trade executed successfully!")
        print(f"   Order ID: {result['order_id']}")
        print(f"   Message: {result['message']}")

        # Wait for expiration (optional)
        print(f"\n⏳ Waiting {trade_params['expiration'] / 60} minutes for trade result...")
        time.sleep(30)  # Short wait for demo - use real expiration in production

        # Check result
        check_result = executor.check_trade_result(result['order_id'])
        if check_result.get('success'):
            print(f"\n📊 Trade Result: {check_result['message']}")
            if check_result.get('win'):
                print("🎉 WIN!")
            else:
                print("💸 Loss")
            print(f"   Final Balance: ${connector.balance:,.2f}")

    else:
        print(f"\n❌ Trade failed: {result.get('error', 'Unknown error')}")
        print("\n🔧 Troubleshooting:")
        print("1. Check if asset is in verified list")
        print("2. Verify sufficient balance")
        print("3. Ensure connection is active")

    # Disconnect
    connector.disconnect()
    print("\n🔌 Disconnected")
    print("✅ Trade example complete")


if __name__ == "__main__":
    print(f"Python path: {sys.path[:2]}")
    print("⚠️  REAL MONEY TRADING - Run with caution!")
    main()
