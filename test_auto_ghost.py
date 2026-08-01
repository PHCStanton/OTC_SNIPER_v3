import asyncio
import sys
import logging
import pytest

from app.backend.services.auto_ghost import AutoGhostService, AutoGhostConfig
from app.backend.services.trade_service import TradeService
from app.backend.brokers.base import BrokerType
from app.backend.models.requests import TradeExecutionRequest

logging.basicConfig(level=logging.DEBUG)

class MockTradeService:
    def __init__(self):
        self.trades = []

    async def execute_trade(self, broker: BrokerType, request: TradeExecutionRequest):
        self.trades.append(request)
        return {"success": True, "message": "trade executed"}

@pytest.mark.asyncio
async def test_auto_ghost():
    print("Starting Auto-Ghost smoke test...")
    trade_service = MockTradeService()
    service = AutoGhostService(trade_service, config=AutoGhostConfig(
        enabled=True,
        amount=1.5,
        expiration_seconds=10,
        max_concurrent_trades=2,
        per_asset_cooldown_seconds=5,
        block_on_manipulation=True
    ))
    service.CONFIRMATION_TICKS = 1

    # Signal 1: valid signal
    oteo_result = {
        "recommended": "CALL",
        "actionable": True,
        "confidence": "HIGH",
        "oteo_score": 85.0
    }
    res1 = await service.consider_signal(
        asset="EURUSD",
        price=1.1,
        timestamp=1000.0,
        oteo_result=oteo_result,
        manipulation={}
    )
    assert res1 and res1["success"] is True, "Trade 1 should succeed"
    assert len(trade_service.trades) == 1
    print("Test 1 passed: Valid signal triggers trade.")

    # Signal 2: same asset during cooldown/active
    res2 = await service.consider_signal(
        asset="EURUSD",
        price=1.1,
        timestamp=1001.0,
        oteo_result=oteo_result,
        manipulation={}
    )
    assert res2 is None, "Trade 2 should be rejected (same asset active)"
    assert len(trade_service.trades) == 1
    print("Test 2 passed: Same asset blocked.")

    # Signal 3: second asset valid signal
    res3 = await service.consider_signal(
        asset="GBPUSD",
        price=1.2,
        timestamp=1002.0,
        oteo_result=oteo_result,
        manipulation={}
    )
    assert res3 and res3["success"] is True, "Trade 3 should succeed"
    assert len(trade_service.trades) == 2
    print("Test 3 passed: Second asset triggers trade.")

    # Signal 4: third asset valid signal (should fail due to max_concurrent_trades=2)
    res4 = await service.consider_signal(
        asset="USDJPY",
        price=1.3,
        timestamp=1003.0,
        oteo_result=oteo_result,
        manipulation={}
    )
    assert res4 is None, "Trade 4 should be rejected (max concurrent trades reached)"
    assert len(trade_service.trades) == 2
    print("Test 4 passed: Max concurrent trades blocks new trades.")

    # Signal 5: manipulation
    trade_service.trades.clear()
    service._active_assets.clear() # clear for next test
    res5 = await service.consider_signal(
        asset="AUDUSD",
        price=1.4,
        timestamp=1004.0,
        oteo_result=oteo_result,
        manipulation={"flag": "high_velocity"}
    )
    assert res5 is None, "Trade 5 should be rejected (manipulation blocked)"
    assert len(trade_service.trades) == 0
    print("Test 5 passed: Manipulation blocked.")

    # Signal 6: Timeframe trade limit (max 2 trades per 10 seconds)
    print("Starting Test 6 (Timeframe limits)...")
    service.update_config(
        max_trades_per_timeframe=2,
        timeframe_seconds=10,
        block_on_manipulation=False  # disable manipulation filter for this test
    )
    trade_service.trades.clear()
    service._trade_timestamps.clear()
    service._active_assets.clear()
    service._cooldown_until.clear()

    # Trade 1 at t=1000 (success)
    res_t1 = await service.consider_signal(
        asset="EURUSD", price=1.1, timestamp=1000.0, oteo_result=oteo_result, manipulation={}
    )
    assert res_t1 and res_t1["success"] is True
    assert len(trade_service.trades) == 1

    # Trade 2 at t=1001 (success)
    service._active_assets.clear() # clear active asset state to bypass concurrency check
    res_t2 = await service.consider_signal(
        asset="GBPUSD", price=1.2, timestamp=1001.0, oteo_result=oteo_result, manipulation={}
    )
    assert res_t2 and res_t2["success"] is True
    assert len(trade_service.trades) == 2

    # Trade 3 at t=1002 (blocked - limit reached)
    service._active_assets.clear()
    res_t3 = await service.consider_signal(
        asset="USDJPY", price=1.3, timestamp=1002.0, oteo_result=oteo_result, manipulation={}
    )
    assert res_t3 is None, "Trade 3 should be blocked because max trades (2) in timeframe (10s) reached"
    assert len(trade_service.trades) == 2

    # Trade 4 at t=1011 (success - rolling window expires oldest trade at 1000.0)
    service._active_assets.clear()
    res_t4 = await service.consider_signal(
        asset="USDJPY", price=1.3, timestamp=1011.0, oteo_result=oteo_result, manipulation={}
    )
    assert res_t4 and res_t4["success"] is True, "Trade 4 should succeed as oldest trade timestamp (1000.0) is expired"
    assert len(trade_service.trades) == 3
    print("Test 6 passed: Timeframe limits successfully enforced and expired.")

    # Signal 7: Z-Score Gates (min and max Z-Score checks)
    print("Starting Test 7 (Z-Score Gates)...")
    service.update_config(
        min_zscore_enabled=True,
        min_zscore=-0.5,
        max_zscore_enabled=True,
        max_zscore=1.5,
        max_trades_per_timeframe=0, # disable timeframe limit
    )
    trade_service.trades.clear()
    service._active_assets.clear()
    service._cooldown_until.clear()

    # Signal 7.1: valid Z-score (0.5)
    oteo_res_z1 = {
        "recommended": "CALL",
        "actionable": True,
        "confidence": "HIGH",
        "oteo_score": 85.0,
        "z_score": 0.5
    }
    res_z1 = await service.consider_signal(
        asset="EURUSD", price=1.1, timestamp=2000.0, oteo_result=oteo_res_z1, manipulation={}
    )
    assert res_z1 and res_z1["success"] is True, "Should succeed as Z=0.5 is within [-0.5, 1.5]"
    assert len(trade_service.trades) == 1

    # Signal 7.2: z_score too low (-0.6)
    service._active_assets.clear()
    oteo_res_z2 = {
        "recommended": "CALL",
        "actionable": True,
        "confidence": "HIGH",
        "oteo_score": 85.0,
        "z_score": -0.6
    }
    res_z2 = await service.consider_signal(
        asset="GBPUSD", price=1.2, timestamp=2001.0, oteo_result=oteo_res_z2, manipulation={}
    )
    assert res_z2 is None, "Should be blocked because Z=-0.6 < min_zscore=-0.5"
    assert len(trade_service.trades) == 1

    # Signal 7.3: z_score too high (1.6)
    oteo_res_z3 = {
        "recommended": "CALL",
        "actionable": True,
        "confidence": "HIGH",
        "oteo_score": 85.0,
        "z_score": 1.6
    }
    res_z3 = await service.consider_signal(
        asset="GBPUSD", price=1.2, timestamp=2002.0, oteo_result=oteo_res_z3, manipulation={}
    )
    assert res_z3 is None, "Should be blocked because Z=1.6 > max_zscore=1.5"
    assert len(trade_service.trades) == 1

    # Signal 7.4: disabled bounds allow extreme Z-scores
    service.update_config(min_zscore_enabled=False, max_zscore_enabled=False)
    res_z4 = await service.consider_signal(
        asset="GBPUSD", price=1.2, timestamp=2003.0, oteo_result=oteo_res_z3, manipulation={}
    )
    assert res_z4 and res_z4["success"] is True, "Should succeed as Z gates are disabled"
    assert len(trade_service.trades) == 2
    print("Test 7 passed: Z-Score gates verified.")

    # Signal 8: Market Regime Gates
    print("Starting Test 8 (Market Regime Gates)...")
    service.update_config(
        regime_gate_enabled=True,
        allowed_regimes=["RANGE_BOUND", "TREND_REVERSAL"],
        require_regime_stable=True
    )
    trade_service.trades.clear()
    service._active_assets.clear()
    service._cooldown_until.clear()

    # Signal 8.1: Allowed and Stable regime
    oteo_res_reg1 = {
        "recommended": "CALL",
        "actionable": True,
        "confidence": "HIGH",
        "oteo_score": 85.0,
        "regime_label": "RANGE_BOUND",
        "regime_stable": True
    }
    res_reg1 = await service.consider_signal(
        asset="EURUSD", price=1.1, timestamp=3000.0, oteo_result=oteo_res_reg1, manipulation={}
    )
    assert res_reg1 and res_reg1["success"] is True, "Should succeed as RANGE_BOUND is allowed and stable"
    assert len(trade_service.trades) == 1

    # Signal 8.2: Disallowed regime (STRONG_MOMENTUM)
    service._active_assets.clear()
    oteo_res_reg2 = {
        "recommended": "CALL",
        "actionable": True,
        "confidence": "HIGH",
        "oteo_score": 85.0,
        "regime_label": "STRONG_MOMENTUM",
        "regime_stable": True
    }
    res_reg2 = await service.consider_signal(
        asset="GBPUSD", price=1.2, timestamp=3001.0, oteo_result=oteo_res_reg2, manipulation={}
    )
    assert res_reg2 is None, "Should be blocked because STRONG_MOMENTUM is not allowed"
    assert len(trade_service.trades) == 1

    # Signal 8.3: Allowed but Unstable regime
    oteo_res_reg3 = {
        "recommended": "CALL",
        "actionable": True,
        "confidence": "HIGH",
        "oteo_score": 85.0,
        "regime_label": "TREND_REVERSAL",
        "regime_stable": False
    }
    res_reg3 = await service.consider_signal(
        asset="GBPUSD", price=1.2, timestamp=3002.0, oteo_result=oteo_res_reg3, manipulation={}
    )
    assert res_reg3 is None, "Should be blocked because regime stable is required but stable is False"
    assert len(trade_service.trades) == 1

    # Signal 8.4: Allowed but Unstable when require_regime_stable is False
    service.update_config(require_regime_stable=False)
    res_reg4 = await service.consider_signal(
        asset="GBPUSD", price=1.2, timestamp=3003.0, oteo_result=oteo_res_reg3, manipulation={}
    )
    assert res_reg4 and res_reg4["success"] is True, "Should succeed since require_regime_stable is False"
    assert len(trade_service.trades) == 2

    # Signal 8.5: Empty allowed regimes allows any regime
    service.update_config(allowed_regimes=[])
    service._active_assets.clear()
    res_reg5 = await service.consider_signal(
        asset="USDJPY", price=1.3, timestamp=3004.0, oteo_result=oteo_res_reg2, manipulation={}
    )
    assert res_reg5 and res_reg5["success"] is True, "Should succeed as allowed_regimes is empty (allow all)"
    assert len(trade_service.trades) == 3

    # Signal 8.6: regime_gate_enabled is False, allowed_regimes set but shouldn't block
    service.update_config(
        regime_gate_enabled=False,
        allowed_regimes=["RANGE_BOUND"],
        require_regime_stable=True
    )
    service._active_assets.clear()
    service._cooldown_until.clear()
    res_reg6 = await service.consider_signal(
        asset="USDJPY", price=1.3, timestamp=3005.0, oteo_result=oteo_res_reg2, manipulation={}
    )
    assert res_reg6 and res_reg6["success"] is True, "Should succeed as regime_gate_enabled is False"
    assert len(trade_service.trades) == 4
    print("Test 8 passed: Market Regime gates verified.")

    # Test 9: Asset blacklisting
    print("Starting Test 9 (Asset Blacklisting)...")
    service.update_config(
        blacklist_assets=["EURUSD", "GBPUSD"]
    )
    # Signal for blacklisted asset EURUSD
    res_bl1 = await service.consider_signal(
        asset="EURUSD", price=1.1, timestamp=4000.0, oteo_result=oteo_result, manipulation={}
    )
    assert res_bl1 is None, "Should be rejected because EURUSD is blacklisted"
    assert service._last_reject_reason_by_asset.get("EURUSD") == "asset_blacklisted"

    # Signal for non-blacklisted asset USDJPY
    service._active_assets.clear()
    service._cooldown_until.clear()
    res_bl2 = await service.consider_signal(
        asset="USDJPY", price=1.3, timestamp=4001.0, oteo_result=oteo_result, manipulation={}
    )
    assert res_bl2 and res_bl2["success"] is True, "Should succeed as USDJPY is not blacklisted"
    print("Test 9 passed: Asset blacklisting verified.")

    # Test 10: Extension Manager plugin discovery & dynamic toggles
    print("Starting Test 10 (Extension Manager plugin discovery)...")
    from app.backend.services.extensions.manager import ExtensionManager
    service.extension_manager = ExtensionManager()
    
    # Verify extensions are discovered
    exts = service.extension_manager.get_active_extensions()
    assert len(exts) >= 2, "Should discover active plugin extensions"
    
    # Find the extension instances
    adaptive_ext = next((e for e in exts if e.__class__.__name__ == "VolatilityAdaptiveExpiry"), None)
    vol_liq_ext = next((e for e in exts if e.__class__.__name__ == "VolatilityLiquidityGates"), None)
    
    assert adaptive_ext is not None, "VolatilityAdaptiveExpiry extension should be discovered"
    assert vol_liq_ext is not None, "VolatilityLiquidityGates extension should be discovered"
    
    # Test clear_plugin_cache propagates status
    service.update_config(volatility_gate_enabled=True)
    service.clear_plugin_cache()
    assert vol_liq_ext.enabled is True

    print("Test 10 passed: Extension Manager plugin discovery verified.")

    # Test 11: Volatility & Liquidity Gates
    print("Starting Test 11 (Volatility & Liquidity Gates)...")
    service.update_config(
        volatility_gate_enabled=True,
        min_volatility=20.0,
        max_volatility=80.0,
        liquidity_gate_enabled=True,
        min_liquidity=30.0,
        max_liquidity=70.0
    )
    
    # 11a. Reject due to Volatility too high (vol=90, liq=50)
    service._active_assets.clear()
    service._cooldown_until.clear()
    res_vol1 = await service.consider_signal(
        asset="USDJPY", price=1.3, timestamp=5000.0,
        oteo_result={
            "recommended": "CALL", "actionable": True, "confidence": "HIGH", "oteo_score": 85.0,
            "market_context": {"volatility_score": 90.0, "liquidity_score": 50.0}
        },
        manipulation={}
    )
    assert res_vol1 is None, "Should be rejected because Volatility is too high"
    assert service._last_reject_reason_by_asset.get("USDJPY") == "volatility_gate"

    # 11b. Reject due to Liquidity too low (vol=50, liq=10)
    service._active_assets.clear()
    res_liq1 = await service.consider_signal(
        asset="USDJPY", price=1.3, timestamp=5001.0,
        oteo_result={
            "recommended": "CALL", "actionable": True, "confidence": "HIGH", "oteo_score": 85.0,
            "market_context": {"volatility_score": 50.0, "liquidity_score": 10.0}
        },
        manipulation={}
    )
    assert res_liq1 is None, "Should be rejected because Liquidity is too low"
    assert service._last_reject_reason_by_asset.get("USDJPY") == "liquidity_gate"

    # 11c. Accept valid Volatility & Liquidity (vol=50, liq=50)
    service._active_assets.clear()
    res_ok = await service.consider_signal(
        asset="USDJPY", price=1.3, timestamp=5002.0,
        oteo_result={
            "recommended": "CALL", "actionable": True, "confidence": "HIGH", "oteo_score": 85.0,
            "market_context": {"volatility_score": 50.0, "liquidity_score": 50.0}
        },
        manipulation={}
    )
    assert res_ok and res_ok["success"] is True, "Should succeed as Vol & Liq are in range"
    print("Test 11 passed: Volatility & Liquidity gates verified.")

    # Test 12: ADX & CCI Gates
    print("Starting Test 12 (ADX & CCI Gates)...")
    service.update_config(
        volatility_gate_enabled=False,
        liquidity_gate_enabled=False,
        adx_gate_enabled=True,
        cci_gate_enabled=True
    )

    # 12a. Reject due to Strong ADX and not reversal friendly
    service._active_assets.clear()
    res_adx = await service.consider_signal(
        asset="USDJPY", price=1.3, timestamp=6000.0,
        oteo_result={
            "recommended": "CALL", "actionable": True, "confidence": "HIGH", "oteo_score": 85.0,
            "market_context": {"adx_regime": "STRONG", "reversal_friendly": False}
        },
        manipulation={}
    )
    assert res_adx is None, "Should be rejected due to strong ADX without reversal friendliness"
    assert service._last_reject_reason_by_asset.get("USDJPY") == "adx_gate_trend_block"

    # 12b. Reject due to CCI Extreme Overbought on CALL
    service._active_assets.clear()
    res_cci = await service.consider_signal(
        asset="USDJPY", price=1.3, timestamp=6001.0,
        oteo_result={
            "recommended": "CALL", "actionable": True, "confidence": "HIGH", "oteo_score": 85.0,
            "market_context": {"cci_state": "OVERBOUGHT"}
        },
        manipulation={}
    )
    assert res_cci is None, "Should be rejected due to CCI overbought on CALL signal"
    assert service._last_reject_reason_by_asset.get("USDJPY") == "cci_gate_overbought_call"

    # 12c. Accept when ADX and CCI align
    service._active_assets.clear()
    service._cooldown_until.clear()
    res_ok2 = await service.consider_signal(
        asset="USDJPY", price=1.3, timestamp=6002.0,
        oteo_result={
            "recommended": "CALL", "actionable": True, "confidence": "HIGH", "oteo_score": 85.0,
            "market_context": {"adx_regime": "WEAK", "reversal_friendly": True, "cci_state": "NEUTRAL"}
        },
        manipulation={}
    )
    assert res_ok2 and res_ok2["success"] is True, "Should succeed as ADX & CCI are friendly"
    print("Test 12 passed: ADX & CCI gates verified.")

    # Test 13: Dynamic Knowledge Base Outcome Logging
    print("Starting Test 13 (Dynamic KB Outcome Logging)...")
    from app.backend.services.ai_review import KnowledgeBaseLoader
    from pathlib import Path
    import os
    
    kb_loader = KnowledgeBaseLoader.get_instance()
    # Mock kb_path to temporary file
    temp_kb_path = Path("c:/v3/OTC_SNIPER/scratch_test_kb.json")
    original_kb_path = kb_loader.kb_path
    original_patterns = list(kb_loader.patterns)
    original_metadata = dict(kb_loader.metadata)
    
    kb_loader.kb_path = temp_kb_path
    kb_loader.patterns = []
    kb_loader.metadata = {}
    kb_loader.loaded = True  # force loaded
    
    # Report a win
    entry_context = {
        "oteo_score": 88.5,
        "level3_enabled": True,
        "regime_label": "RANGE_BOUND",
        "recommended": "CALL"
    }
    service.report_outcome(
        trade_id="trade_test_13",
        outcome="win",
        profit=5.0,
        asset="USDJPY",
        entry_context=entry_context,
        direction="CALL"
    )
    
    assert len(kb_loader.patterns) == 1, "Should have added exactly 1 new pattern to the KB list"
    new_pattern = kb_loader.patterns[0]
    assert new_pattern["pattern_key"] == "USDJPY|level3|85-92|RANGE_BOUND|CALL"
    assert new_pattern["sample_size"] == 1
    assert new_pattern["win_rate_pct"] == 100.0
    assert new_pattern["net_profit"] == 5.0
    assert temp_kb_path.exists(), "Dynamic KB JSON file should be created/updated on disk"
    
    # Report a loss for the same pattern
    service.report_outcome(
        trade_id="trade_test_13_2",
        outcome="loss",
        profit=-5.0,
        asset="USDJPY",
        entry_context=entry_context,
        direction="CALL"
    )
    assert len(kb_loader.patterns) == 1, "Should still have 1 pattern key"
    assert new_pattern["sample_size"] == 2
    assert new_pattern["win_rate_pct"] == 50.0
    assert new_pattern["net_profit"] == 0.0
    
    # Clean up temp file and restore original state
    if temp_kb_path.exists():
        os.remove(temp_kb_path)
    kb_loader.kb_path = original_kb_path
    kb_loader.patterns = original_patterns
    kb_loader.metadata = original_metadata
    print("Test 13 passed: Dynamic KB outcome logging verified.")

    # Test 14: Adaptive Expiry Toggle Check
    from app.backend.services.extensions.volatility_adaptive_expiry import VolatilityAdaptiveExpiry
    ext = VolatilityAdaptiveExpiry({"enabled": True, "min_adaptive_expiry": 30})
    
    # When enabled = True, volatility score < 30 maps to 300s expiry
    oteo_res = {"recommended": "CALL", "actionable": True, "oteo_score": 80.0}
    mkt_ctx = {"volatility_score": 20.0}
    ext.on_tick_processed("EURUSD", 1.1, 1000.0, oteo_res, mkt_ctx)
    assert oteo_res.get("override_expiration_seconds") == 300, "Should override expiration to 300s when enabled"
    
    # When enabled = False, on_tick_processed does NOT inject override_expiration_seconds
    ext.enabled = False
    oteo_res_disabled = {"recommended": "CALL", "actionable": True, "oteo_score": 80.0}
    ext.on_tick_processed("EURUSD", 1.1, 1000.0, oteo_res_disabled, mkt_ctx)
    assert "override_expiration_seconds" not in oteo_res_disabled, "Should NOT set override_expiration_seconds when extension disabled"
    print("Test 14 passed: Adaptive Expiry toggle (enabled vs disabled) verified.")

    print("All tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_auto_ghost())
