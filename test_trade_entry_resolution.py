import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.backend.services.trade_service import TradeService
from app.backend.models.requests import TradeExecutionRequest
from app.backend.brokers.base import BrokerType, TradeResult
from app.backend.models.domain import TradeKind

@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.write_trade = AsyncMock()
    repo.update_trade = AsyncMock()
    return repo

@pytest.fixture
def mock_sio():
    sio = MagicMock()
    sio.emit = AsyncMock()
    return sio

def test_resolve_entry_price_adapter_precedence(mock_repo):
    service = TradeService(repository=mock_repo)
    req = TradeExecutionRequest(
        asset_id="EURUSD_otc",
        direction="call",
        amount=10.0,
        expiration=60,
        entry_context={"price": 1.0850},
    )
    latest_tick = {"p": 1.0845, "t": 1000.0}

    # 1. Adapter price takes priority when present
    price = service._resolve_entry_price(req, latest_tick, adapter_price=1.0855)
    assert price == 1.0855

    # 2. Context price used when adapter price is None
    price = service._resolve_entry_price(req, latest_tick, adapter_price=None)
    assert price == 1.0850

    # 3. Latest tick price used when context price is missing
    req_no_price = TradeExecutionRequest(
        asset_id="EURUSD_otc",
        direction="call",
        amount=10.0,
        expiration=60,
        entry_context={},
    )
    price = service._resolve_entry_price(req_no_price, latest_tick, adapter_price=None)
    assert price == 1.0845

    # 4. Returns None when no sources available
    price = service._resolve_entry_price(req_no_price, None, adapter_price=None)
    assert price is None

@pytest.mark.asyncio
async def test_live_trade_entry_price_resolved_and_emitted(mock_repo, mock_sio, monkeypatch):
    service = TradeService(repository=mock_repo, sio=mock_sio)

    # Mock adapter
    mock_adapter = MagicMock()
    mock_adapter.session_manager.snapshot.return_value = MagicMock(session_id="test-session")
    mock_adapter.get_connection_status.return_value = "connected"
    mock_adapter.execute_trade = AsyncMock(return_value=TradeResult(
        success=True,
        trade_id="live-12345",
        entry_price=None, # Adapter does NOT know entry_price immediately
        message="Trade submitted",
        broker=BrokerType.POCKET_OPTION,
    ))

    from app.backend.brokers.registry import BrokerRegistry
    monkeypatch.setattr(BrokerRegistry, "get_adapter", lambda broker, account_key=None: mock_adapter)

    # Mock _track_trade_outcome to avoid background sleep
    service._track_trade_outcome = AsyncMock()

    req = TradeExecutionRequest(
        asset_id="EURUSD_otc",
        direction="call",
        amount=25.0,
        expiration=60,
        trade_mode="live",
        demo=False,
        entry_context={"price": 1.08523, "z_score": 0.45},
    )

    result = await service.execute_trade(BrokerType.POCKET_OPTION, req)

    assert result["success"] is True
    assert result["entry_price"] == 1.08523
    assert result["trade_id"] == "live-12345"

    # Verify write_trade received resolved entry_price
    assert mock_repo.write_trade.called
    written_trade = mock_repo.write_trade.call_args[0][0]
    assert written_trade.kind == TradeKind.LIVE
    assert written_trade.entry_price == 1.08523

    # Verify Socket.IO emitted trade_entry with resolved entry_price
    assert mock_sio.emit.called
    emit_args = mock_sio.emit.call_args_list[0]
    event_name, payload = emit_args[0][0], emit_args[0][1]
    assert event_name == "trade_entry"
    assert payload["entry_price"] == 1.08523
    assert payload["kind"] == "live"
    assert payload["trade_id"] == "live-12345"
