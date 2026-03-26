from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List

from ..brokers.base import BrokerType
from ..data.repository import DataRepository
from ..dependencies import get_data_repository
from ..models.domain import TradeRecord
from ..models.requests import TradeExecutionRequest
from ..models.responses import TradeExecutionResponse
from ..services.trade_service import TradeService

router = APIRouter(prefix="/api/brokers")

def get_trade_service(repo: DataRepository = Depends(get_data_repository)) -> TradeService:
    return TradeService(repository=repo)

@router.post("/{broker}/trade", response_model=TradeExecutionResponse)
async def execute_trade(
    broker: str, 
    request: TradeExecutionRequest, 
    service: TradeService = Depends(get_trade_service)
) -> TradeExecutionResponse:
    try:
        broker_type = BrokerType(broker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown broker: {broker}") from exc

    try:
        result = await service.execute_trade(broker_type, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return TradeExecutionResponse(
        success=result["success"],
        broker=broker,
        asset_id=request.asset_id,
        direction=request.direction,
        amount=request.amount,
        expiration=request.expiration,
        message=result["message"],
        trade_id=result["trade_id"],
        session_id=result["session_id"],
        entry_price=result.get("entry_price"),
        connection_status=result["connection_status"],
    )

@router.get("/{broker}/trades", response_model=List[TradeRecord])
async def get_trades(
    broker: str,
    session_id: str = Query(..., min_length=1, description="Active session ID to retrieve trades for"),
    limit: int = Query(50, ge=1, le=500),
    repo: DataRepository = Depends(get_data_repository)
):
    try:
        broker_type = BrokerType(broker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown broker: {broker}") from exc

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id param is required")

    try:
        trades = await repo.get_trades(session_id, limit)
        return trades
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
