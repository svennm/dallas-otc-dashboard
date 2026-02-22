from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import get_db
from app.deps import require_roles
from app.models import (
    Client,
    Instrument,
    MarketPrice,
    Position,
    RFQRequest,
    RFQStatus,
    User,
    UserRole,
)
from app.schemas import RFQCreate, RFQOut
from app.services.audit import log_event
from app.services.pricing import calculate_quote, clamp_expiry, inventory_skew_bps
from app.services.ws import manager

router = APIRouter(prefix="/rfq", tags=["rfq"])


def _default_mid(symbol: str) -> float:
    defaults = {
        "BTC-USD": 52000.0,
        "ETH-USD": 2800.0,
        "SOL-USD": 115.0,
        "ADA-USD": 0.64,
    }
    return defaults.get(symbol, 1000.0)


@router.get("", response_model=list[RFQOut])
async def list_rfqs(
    active_only: bool = Query(default=True),
    limit: int = Query(default=200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.viewer, UserRole.trader, UserRole.risk, UserRole.admin)),
) -> list[RFQOut]:
    stmt = (
        select(RFQRequest, Client.name, Instrument.symbol)
        .join(Client, RFQRequest.client_id == Client.id)
        .join(Instrument, RFQRequest.instrument_id == Instrument.id)
        .order_by(RFQRequest.created_at.desc())
        .limit(limit)
    )
    if active_only:
        stmt = stmt.where(RFQRequest.status.in_([RFQStatus.pending, RFQStatus.quoted]))

    rows = (await db.execute(stmt)).all()

    now = datetime.now(timezone.utc)
    changed = False
    output: list[RFQOut] = []
    for rfq, client_name, instrument_symbol in rows:
        if rfq.status in {RFQStatus.pending, RFQStatus.quoted} and now > rfq.quote_expiry:
            rfq.status = RFQStatus.expired
            changed = True
            await manager.broadcast(
                "rfq_updates",
                {
                    "channel": "rfq_updates",
                    "data": {"id": str(rfq.id), "status": "expired", "expired_at": now.isoformat()},
                },
            )

        output.append(
            RFQOut(
                id=rfq.id,
                client_id=rfq.client_id,
                client_name=client_name,
                instrument_id=rfq.instrument_id,
                instrument_symbol=instrument_symbol,
                side=rfq.side,
                size=float(rfq.size),
                quoted_price=float(rfq.quoted_price),
                quote_expiry=rfq.quote_expiry,
                status=rfq.status,
                created_at=rfq.created_at,
            )
        )

    if changed:
        await db.commit()

    return output


@router.post("", response_model=RFQOut)
async def create_rfq(
    payload: RFQCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.trader, UserRole.admin)),
) -> RFQOut:
    client = await db.get(Client, payload.client_id)
    instrument = await db.get(Instrument, payload.instrument_id)

    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    if instrument is None:
        raise HTTPException(status_code=404, detail="Instrument not found")

    latest_price_result = await db.execute(
        select(MarketPrice)
        .where(MarketPrice.instrument_id == payload.instrument_id)
        .order_by(MarketPrice.ts.desc())
        .limit(1)
    )
    latest_price = latest_price_result.scalar_one_or_none()
    mid = float(latest_price.mid) if latest_price else _default_mid(instrument.symbol)

    desk_inventory_result = await db.execute(
        select(func.coalesce(func.sum(Position.net_size), 0)).where(
            Position.instrument_id == payload.instrument_id
        )
    )
    desk_inventory = float(desk_inventory_result.scalar_one())

    expiry_seconds = clamp_expiry(
        payload.expiry_seconds,
        settings.rfq_min_expiry_seconds,
        settings.rfq_max_expiry_seconds,
    )

    skew_bps = inventory_skew_bps(desk_inventory, payload.side)
    quote = calculate_quote(
        mid_price=mid,
        side=payload.side,
        spread_buffer_bps=10.0,
        inventory_skew_bps=skew_bps,
        client_markup_bps=client.default_markup_bps,
    )

    expiry_at = datetime.now(timezone.utc) + timedelta(seconds=expiry_seconds)

    rfq = RFQRequest(
        client_id=client.id,
        instrument_id=instrument.id,
        requested_by_user_id=current_user.id,
        side=payload.side,
        size=payload.size,
        quoted_price=quote,
        quote_expiry=expiry_at,
        status=RFQStatus.quoted,
    )
    db.add(rfq)
    await db.flush()

    await log_event(
        db,
        event_type="rfq.quoted",
        entity_type="rfq_request",
        entity_id=str(rfq.id),
        user_id=current_user.id,
        metadata={
            "client_id": client.id,
            "instrument_id": instrument.id,
            "side": payload.side.value,
            "size": payload.size,
            "quoted_price": quote,
            "expiry_seconds": expiry_seconds,
            "inventory_skew_bps": skew_bps,
        },
    )

    await db.commit()
    await db.refresh(rfq)

    message = RFQOut(
        id=rfq.id,
        client_id=client.id,
        client_name=client.name,
        instrument_id=instrument.id,
        instrument_symbol=instrument.symbol,
        side=rfq.side,
        size=float(rfq.size),
        quoted_price=float(rfq.quoted_price),
        quote_expiry=rfq.quote_expiry,
        status=rfq.status,
        created_at=rfq.created_at,
    )

    await manager.broadcast(
        "rfq_updates",
        {
            "channel": "rfq_updates",
            "data": message.model_dump(mode="json"),
        },
    )

    return message


@router.get("/{rfq_id}", response_model=RFQOut)
async def get_rfq_status(
    rfq_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.viewer, UserRole.trader, UserRole.risk, UserRole.admin)),
) -> RFQOut:
    row = await db.execute(
        select(RFQRequest, Client.name, Instrument.symbol)
        .join(Client, RFQRequest.client_id == Client.id)
        .join(Instrument, RFQRequest.instrument_id == Instrument.id)
        .where(RFQRequest.id == rfq_id)
    )
    found = row.one_or_none()

    if found is None:
        raise HTTPException(status_code=404, detail="RFQ not found")

    rfq, client_name, instrument_symbol = found

    now = datetime.now(timezone.utc)
    if rfq.status in {RFQStatus.pending, RFQStatus.quoted} and now > rfq.quote_expiry:
        rfq.status = RFQStatus.expired
        await log_event(
            db,
            event_type="rfq.expired",
            entity_type="rfq_request",
            entity_id=str(rfq.id),
            user_id=None,
            metadata={"expired_at": now.isoformat()},
        )
        await db.commit()

        await manager.broadcast(
            "rfq_updates",
            {
                "channel": "rfq_updates",
                "data": {
                    "id": str(rfq.id),
                    "status": rfq.status.value,
                    "expired_at": now.isoformat(),
                },
            },
        )

    return RFQOut(
        id=rfq.id,
        client_id=rfq.client_id,
        client_name=client_name,
        instrument_id=rfq.instrument_id,
        instrument_symbol=instrument_symbol,
        side=rfq.side,
        size=float(rfq.size),
        quoted_price=float(rfq.quoted_price),
        quote_expiry=rfq.quote_expiry,
        status=rfq.status,
        created_at=rfq.created_at,
    )
