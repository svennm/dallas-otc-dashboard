from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_roles
from app.models import Client, Instrument, Position, User, UserRole
from app.schemas import PositionOut

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("", response_model=list[PositionOut])
async def get_positions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.viewer, UserRole.trader, UserRole.risk, UserRole.admin)),
) -> list[PositionOut]:
    stmt = (
        select(Position, Client.name, Instrument.symbol)
        .join(Client, Position.client_id == Client.id)
        .join(Instrument, Position.instrument_id == Instrument.id)
        .order_by(desc(Position.usd_exposure))
    )
    rows = (await db.execute(stmt)).all()

    return [
        PositionOut(
            client_id=position.client_id,
            client_name=client_name,
            instrument_id=position.instrument_id,
            instrument_symbol=instrument_symbol,
            net_size=float(position.net_size),
            avg_price=float(position.avg_price),
            usd_exposure=float(position.usd_exposure),
            updated_at=position.updated_at,
        )
        for position, client_name, instrument_symbol in rows
    ]
