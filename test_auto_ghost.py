import asyncio
import sys
import logging

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

    print("All tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_auto_ghost())
