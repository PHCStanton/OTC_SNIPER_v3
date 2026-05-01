#!/usr/bin/env python3
"""
SSID Integration Package - Basic Connection Example

Shows how to establish a valid SSID connection to Pocket Option.
This is the foundation - must work before trading.
"""

import os
import sys
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

# Add package to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ssid_integration_package.core.ssid_connector import SSIDConnector


def main():
    """Basic connection example"""
    print("🔌 SSID Integration Package - Basic Connection Example")
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
        print(f"Please create {config_path} with your SSID")
        print("\nExample config:")
        print('''
{
  "ssid": "42[\\"auth\\",{\\"session\\":\\"your_ssid_here\\",\\"isDemo\\":0,\\"uid\\":12345,\\"platform\\":2}]",
  "is_demo": false
}
        ''')
        return

    # Create connector
    print(f"🔧 Creating SSID Connector (demo={demo})...")
    connector = SSIDConnector(ssid, demo=demo)

    # Test connection
    print("📡 Attempting connection to Pocket Option...")
    success, message = connector.connect()

    print(f"\nResult: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"Message: {message}")

    if success:
        print("📊 Account Information:")
        print(f"   Balance: ${connector.balance:,.2f}")
        print(f"   Connection: {'Demo' if demo else 'Real'} Trading")

        # Test connection health
        print("\n🔍 Testing connection health...")
        is_connected = connector.check_connection()
        print(f"Connection Status: {'✅ Active' if is_connected else '❌ Lost'}")

        if is_connected:
            print(f"Current Balance: ${connector.balance:,.2f}")

        # Disconnect cleanly
        print("\n🔌 Disconnecting...")
        connector.disconnect()
        print("✅ Disconnected successfully")

    else:
        print("\n🔧 Troubleshooting:")
        print("1. Verify SSID is correct and current")
        print("2. Check internet connection")
        print("3. Ensure Pocket Option account is active")
        print("4. Try with demo=True first to test connection")


if __name__ == "__main__":
    print(f"Python path: {sys.path[:2]}")
    main()
