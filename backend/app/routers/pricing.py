from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_roles
from app.models import Instrument, MarketPrice, User, UserRole
from app.schemas import MarketPriceOut

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.get("/current", response_model=list[MarketPriceOut])
async def get_current_prices(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.viewer, UserRole.trader, UserRole.risk, UserRole.admin)),
) -> list[MarketPriceOut]:
    latest_subquery = (
        select(MarketPrice.instrument_id, func.max(MarketPrice.ts).label("max_ts"))
        .group_by(MarketPrice.instrument_id)
        .subquery()
    )

    stmt = (
        select(MarketPrice, Instrument.symbol)
        .join(Instrument, MarketPrice.instrument_id == Instrument.id)
        .join(
            latest_subquery,
            and_(
                MarketPrice.instrument_id == latest_subquery.c.instrument_id,
                MarketPrice.ts == latest_subquery.c.max_ts,
            ),
        )
        .order_by(Instrument.symbol)
    )

    rows = (await db.execute(stmt)).all()
    return [
        MarketPriceOut(
            instrument_id=price.instrument_id,
            instrument_symbol=symbol,
            bid=float(price.bid),
            ask=float(price.ask),
            mid=float(price.mid),
            spread_bps=float(price.spread_bps),
            rolling_vwap=float(price.rolling_vwap),
            volatility_5m=float(price.volatility_5m),
            ts=price.ts,
        )
        for price, symbol in rows
    ]
