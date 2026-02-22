import csv
from datetime import datetime, timezone
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_roles
from app.models import (
    Client,
    Instrument,
    Position,
    RFQRequest,
    RFQStatus,
    Trade,
    TradeSide,
    User,
    UserRole,
)
from app.schemas import TradeCreate, TradeOut, TradesPage
from app.services.audit import log_event
from app.services.risk import apply_trade_to_positions, evaluate_trade_risk
from app.services.ws import manager

router = APIRouter(prefix="/trades", tags=["trades"])


def _build_filters(
    client_id: int | None,
    instrument_id: int | None,
    side: TradeSide | None,
    start: datetime | None,
    end: datetime | None,
) -> list:
    filters = []
    if client_id is not None:
        filters.append(Trade.client_id == client_id)
    if instrument_id is not None:
        filters.append(Trade.instrument_id == instrument_id)
    if side is not None:
        filters.append(Trade.side == side)
    if start is not None:
        filters.append(Trade.timestamp >= start)
    if end is not None:
        filters.append(Trade.timestamp <= end)
    return filters


@router.post("", response_model=TradeOut)
async def create_trade(
    payload: TradeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.trader, UserRole.admin)),
) -> TradeOut:
    client = await db.get(Client, payload.client_id)
    instrument = await db.get(Instrument, payload.instrument_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    if instrument is None:
        raise HTTPException(status_code=404, detail="Instrument not found")

    if payload.rfq_id:
        rfq = await db.get(RFQRequest, payload.rfq_id)
        if rfq is None:
            raise HTTPException(status_code=404, detail="RFQ not found")
        if rfq.status != RFQStatus.quoted:
            raise HTTPException(status_code=400, detail="RFQ is not quote-active")
        if rfq.quote_expiry < datetime.now(timezone.utc):
            rfq.status = RFQStatus.expired
            await db.commit()
            raise HTTPException(status_code=400, detail="RFQ expired")
        rfq.status = RFQStatus.accepted

    risk_check = await evaluate_trade_risk(
        db,
        client_id=payload.client_id,
        instrument_id=payload.instrument_id,
        side=payload.side,
        size=payload.size,
        price=payload.price,
    )

    if risk_check.hard_breach:
        raise HTTPException(
            status_code=409,
            detail={
                "message": risk_check.message,
                "projected_exposure_usd": risk_check.projected_exposure_usd,
                "hard_limit_usd": risk_check.hard_limit_usd,
            },
        )

    notional = abs(payload.size * payload.price)
    trade = Trade(
        rfq_id=payload.rfq_id,
        client_id=payload.client_id,
        instrument_id=payload.instrument_id,
        side=payload.side,
        size=payload.size,
        price=payload.price,
        notional_usd=notional,
        executed_by_user_id=current_user.id,
    )

    db.add(trade)
    await db.flush()

    position = await apply_trade_to_positions(
        db,
        client_id=payload.client_id,
        instrument_id=payload.instrument_id,
        side=payload.side,
        size=payload.size,
        price=payload.price,
    )

    await log_event(
        db,
        event_type="trade.executed",
        entity_type="trade",
        entity_id=str(trade.id),
        user_id=current_user.id,
        metadata={
            "client_id": payload.client_id,
            "instrument_id": payload.instrument_id,
            "side": payload.side.value,
            "size": payload.size,
            "price": payload.price,
            "notional_usd": notional,
            "risk_soft_breach": risk_check.soft_breach,
        },
    )

    if risk_check.soft_breach:
        await log_event(
            db,
            event_type="risk.soft_breach",
            entity_type="trade",
            entity_id=str(trade.id),
            user_id=current_user.id,
            metadata={
                "projected_exposure_usd": risk_check.projected_exposure_usd,
                "soft_limit_usd": risk_check.soft_limit_usd,
            },
        )

    await db.commit()
    await db.refresh(trade)
    await db.refresh(position)

    out = TradeOut(
        id=trade.id,
        client_id=client.id,
        client_name=client.name,
        instrument_id=instrument.id,
        instrument_symbol=instrument.symbol,
        side=trade.side,
        size=float(trade.size),
        price=float(trade.price),
        notional_usd=float(trade.notional_usd),
        timestamp=trade.timestamp,
    )

    await manager.broadcast(
        "trade_updates",
        {
            "channel": "trade_updates",
            "data": out.model_dump(mode="json"),
        },
    )

    await manager.broadcast(
        "positions",
        {
            "channel": "positions",
            "data": {
                "client_id": position.client_id,
                "instrument_id": position.instrument_id,
                "net_size": float(position.net_size),
                "avg_price": float(position.avg_price),
                "usd_exposure": float(position.usd_exposure),
                "soft_breach": risk_check.soft_breach,
            },
        },
    )

    return out


@router.get("", response_model=TradesPage)
async def list_trades(
    client_id: int | None = Query(default=None),
    instrument_id: int | None = Query(default=None),
    side: TradeSide | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.viewer, UserRole.trader, UserRole.risk, UserRole.admin)),
) -> TradesPage:
    filters = _build_filters(client_id, instrument_id, side, start, end)

    count_stmt = select(func.count()).select_from(Trade)
    if filters:
        count_stmt = count_stmt.where(and_(*filters))
    total = int((await db.execute(count_stmt)).scalar_one())

    stmt = (
        select(Trade, Client.name, Instrument.symbol)
        .join(Client, Trade.client_id == Client.id)
        .join(Instrument, Trade.instrument_id == Instrument.id)
        .order_by(desc(Trade.timestamp))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if filters:
        stmt = stmt.where(and_(*filters))

    rows = (await db.execute(stmt)).all()
    items = [
        TradeOut(
            id=trade.id,
            client_id=trade.client_id,
            client_name=client_name,
            instrument_id=trade.instrument_id,
            instrument_symbol=instrument_symbol,
            side=trade.side,
            size=float(trade.size),
            price=float(trade.price),
            notional_usd=float(trade.notional_usd),
            timestamp=trade.timestamp,
        )
        for trade, client_name, instrument_symbol in rows
    ]

    return TradesPage(items=items, page=page, page_size=page_size, total=total)


@router.get("/export.csv")
async def export_trades_csv(
    client_id: int | None = Query(default=None),
    instrument_id: int | None = Query(default=None),
    side: TradeSide | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.viewer, UserRole.trader, UserRole.risk, UserRole.admin)),
) -> Response:
    filters = _build_filters(client_id, instrument_id, side, start, end)

    stmt = (
        select(Trade, Client.name, Instrument.symbol)
        .join(Client, Trade.client_id == Client.id)
        .join(Instrument, Trade.instrument_id == Instrument.id)
        .order_by(desc(Trade.timestamp))
    )
    if filters:
        stmt = stmt.where(and_(*filters))

    rows = (await db.execute(stmt)).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "trade_id",
            "timestamp",
            "client",
            "instrument",
            "side",
            "size",
            "price",
            "notional_usd",
        ]
    )

    for trade, client_name, instrument_symbol in rows:
        writer.writerow(
            [
                trade.id,
                trade.timestamp.isoformat(),
                client_name,
                instrument_symbol,
                trade.side.value,
                float(trade.size),
                float(trade.price),
                float(trade.notional_usd),
            ]
        )

    content = output.getvalue()
    output.close()

    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trades_export.csv"},
    )
