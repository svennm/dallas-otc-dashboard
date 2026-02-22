from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client, MarketPrice, Position, RFQRequest, Trade
from app.schemas import ClientAnalyticsOut


async def _latest_mid_map(db: AsyncSession) -> dict[int, float]:
    latest_subquery = (
        select(MarketPrice.instrument_id, func.max(MarketPrice.ts).label("max_ts"))
        .group_by(MarketPrice.instrument_id)
        .subquery()
    )
    stmt = (
        select(MarketPrice.instrument_id, MarketPrice.mid)
        .join(
            latest_subquery,
            (MarketPrice.instrument_id == latest_subquery.c.instrument_id)
            & (MarketPrice.ts == latest_subquery.c.max_ts),
        )
        .order_by(desc(MarketPrice.ts))
    )
    rows = (await db.execute(stmt)).all()

    latest: dict[int, float] = {}
    for instrument_id, mid in rows:
        if instrument_id not in latest:
            latest[instrument_id] = float(mid)
    return latest


async def calculate_client_analytics(db: AsyncSession, client_id: int) -> ClientAnalyticsOut:
    client = await db.get(Client, client_id)
    if client is None:
        raise ValueError("Client not found")

    trades_result = await db.execute(select(Trade).where(Trade.client_id == client_id))
    trades = trades_result.scalars().all()

    total_volume = sum(abs(float(t.size) * float(t.price)) for t in trades)
    trade_count = len(trades)

    latest_mid = await _latest_mid_map(db)

    positions_result = await db.execute(select(Position).where(Position.client_id == client_id))
    positions = positions_result.scalars().all()

    mtm_pnl = 0.0
    for position in positions:
        mid = latest_mid.get(position.instrument_id, float(position.avg_price))
        mtm_pnl += (mid - float(position.avg_price)) * float(position.net_size)

    spread_capture_bps: list[float] = []
    for trade in trades:
        mid = latest_mid.get(trade.instrument_id)
        if not mid:
            continue
        spread_capture_bps.append(abs((float(trade.price) - mid) / mid) * 10_000)

    rfq_result = await db.execute(select(RFQRequest).where(RFQRequest.client_id == client_id))
    rfqs = rfq_result.scalars().all()
    response_seconds: list[float] = [
        (rfq.updated_at - rfq.created_at).total_seconds()
        for rfq in rfqs
        if rfq.updated_at and rfq.created_at
    ]

    return ClientAnalyticsOut(
        client_id=client.id,
        client_name=client.name,
        mark_to_market_pnl=round(mtm_pnl, 2),
        total_volume_usd=round(total_volume, 2),
        avg_spread_capture_bps=round(sum(spread_capture_bps) / len(spread_capture_bps), 2)
        if spread_capture_bps
        else 0.0,
        avg_rfq_response_seconds=round(sum(response_seconds) / len(response_seconds), 2)
        if response_seconds
        else 0.0,
        trade_count=trade_count,
    )
