# -*- coding: utf-8 -*-
"""
Import sanity check for PocketOptionSession implementation.
Run from: c:\\QuFLX\\v2
Command:  python -m pytest ssid_integration_package/tests/test_imports.py -v
"""
import sys
import os

# Ensure the package root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_global_value_imports():
    import pocketoptionapi.global_value as gv
    assert hasattr(gv, 'reset_all'), "reset_all() missing from global_value"
    assert hasattr(gv, 'reset_trading_state'), "reset_trading_state() missing from global_value"


def test_reset_all_clears_state():
    import pocketoptionapi.global_value as gv
    gv.SSID = "test_ssid"
    gv.DEMO = True
    gv.balance = 1234.56
    gv.websocket_is_connected = True
    gv.reset_all()
    assert gv.SSID is None
    assert gv.DEMO is None
    assert gv.balance is None
    assert gv.websocket_is_connected is False


def test_reset_trading_state_preserves_ssid():
    import pocketoptionapi.global_value as gv
    gv.SSID = "test_ssid"
    gv.DEMO = True
    gv.balance = 999.0
    gv.reset_trading_state()
    # SSID and DEMO must be preserved
    assert gv.SSID == "test_ssid"
    assert gv.DEMO is True
    # Trading state must be cleared
    assert gv.balance is None


def test_pocket_option_api_import():
    from pocketoptionapi.api import PocketOptionAPI
    assert PocketOptionAPI is not None


def test_pocket_option_stable_api_import():
    from pocketoptionapi.stable_api import PocketOption
    assert PocketOption is not None
    assert hasattr(PocketOption, 'connect')
    assert hasattr(PocketOption, 'disconnect')


def test_session_import():
    from core.session import PocketOptionSession, SSIDParseError, ConnectionError
    assert PocketOptionSession is not None
    assert SSIDParseError is not None
    assert ConnectionError is not None


def test_ssid_connector_import():
    from core.ssid_connector import SSIDConnector
    assert SSIDConnector is not None


def test_ssid_parse_valid():
    from core.session import PocketOptionSession
    ssid = '42["auth",{"session":"abc123","isDemo":1,"uid":999}]'
    data = PocketOptionSession._parse_ssid(ssid)
    assert data['session'] == 'abc123'
    assert data['isDemo'] == 1


def test_ssid_parse_demo_detection():
    from core.session import PocketOptionSession
    demo_ssid = '42["auth",{"session":"abc","isDemo":1,"uid":1}]'
    real_ssid = '42["auth",{"session":"abc","isDemo":0,"uid":1}]'
    demo_data = PocketOptionSession._parse_ssid(demo_ssid)
    real_data = PocketOptionSession._parse_ssid(real_ssid)
    assert bool(demo_data.get('isDemo', 0)) is True
    assert bool(real_data.get('isDemo', 0)) is False


def test_ssid_parse_invalid_raises():
    from core.session import PocketOptionSession, SSIDParseError
    import pytest
    with pytest.raises(SSIDParseError):
        PocketOptionSession._parse_ssid("not_valid")
    with pytest.raises(SSIDParseError):
        PocketOptionSession._parse_ssid("")
    with pytest.raises(SSIDParseError):
        PocketOptionSession._parse_ssid('42["wrong_event",{}]')
    with pytest.raises(SSIDParseError):
        PocketOptionSession._parse_ssid('42["auth",{"session":"abc"}]')  # missing isDemo


def test_asset_manager():
    from pocketoptionapi.ws.objects.asset import Asset, AssetManager
    mgr = AssetManager()
    # Simulate raw asset data: [id, symbol, name, ?, ?, ?, ?, ?, profit%, ?, ?, is_available, ?, category]
    raw_data = [
        [1, "EURUSD_otc", "EUR/USD OTC", 0, 0, 0, 0, 0, 85.0, 0, 0, 1, 0, "otc"],
        [2, "GBPUSD_otc", "GBP/USD OTC", 0, 0, 0, 0, 0, 80.0, 0, 0, 0, 0, "otc"],
        [3, "EURUSD",     "EUR/USD",     0, 0, 0, 0, 0, 75.0, 0, 0, 1, 0, "forex"],
    ]
    mgr.process_assets(raw_data)
    assert len(mgr.assets) == 3
    assert mgr.get_asset_by_symbol("EURUSD_otc").profit_percent == 85.0
    assert mgr.get_asset_by_symbol("GBPUSD_otc").is_available is False
    otc = mgr.get_assets_by_type("otc")
    assert len(otc) == 2
    profitable = mgr.get_profitable_assets()
    assert profitable[0].symbol == "EURUSD_otc"  # highest profit, available
    stats = mgr.analyze_by_category()
    assert stats["otc"]["total"] == 2
    assert stats["otc"]["available"] == 1
    assert stats["forex"]["available"] == 1


def test_base_objects_import():
    from pocketoptionapi.ws.objects.base import Base
    from pocketoptionapi.ws.channels.base import Base as ChannelBase
    assert Base is not None
    assert ChannelBase is not None
