import asyncio
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db import AsyncSessionLocal, init_db
from app.models import (
    Client,
    Instrument,
    MarketPrice,
    RFQRequest,
    RFQStatus,
    Trade,
    TradeSide,
    User,
    UserRole,
)
from app.seed import ensure_seed_data
from app.services.audit import log_event
from app.services.risk import apply_trade_to_positions

PRICE_BASE = {
    "BTC-USD": 52000.0,
    "ETH-USD": 2800.0,
    "SOL-USD": 115.0,
    "ADA-USD": 0.64,
}


async def seed_mock_data() -> None:
    await init_db()

    async with AsyncSessionLocal() as db:
        await ensure_seed_data(db)

    async with AsyncSessionLocal() as db:
        clients = (await db.execute(select(Client))).scalars().all()
        instruments = (await db.execute(select(Instrument))).scalars().all()
        trader = (
            await db.execute(select(User).where(User.role.in_([UserRole.trader, UserRole.admin])).limit(1))
        ).scalar_one()

        now = datetime.now(timezone.utc)

        for instrument in instruments:
            mid = PRICE_BASE.get(instrument.symbol, 1000.0)
            for idx in range(36):
                drift = random.uniform(-0.002, 0.002)
                mid = max(mid * (1 + drift), 0.0001)
                spread_bps = random.uniform(6.0, 20.0)
                bid = mid * (1 - spread_bps / 20_000)
                ask = mid * (1 + spread_bps / 20_000)
                db.add(
                    MarketPrice(
                        instrument_id=instrument.id,
                        exchange=random.choice(["coinbase", "kraken", "binance"]),
                        bid=round(bid, 8),
                        ask=round(ask, 8),
                        mid=round(mid, 8),
                        spread_bps=round(spread_bps, 4),
                        rolling_vwap=round(mid * (1 + random.uniform(-0.0007, 0.0007)), 8),
                        volatility_5m=round(random.uniform(0.01, 0.08), 6),
                        ts=now - timedelta(seconds=(36 - idx) * 10),
                    )
                )

        await db.flush()

        for _ in range(20):
            client = random.choice(clients)
            instrument = random.choice(instruments)
            side = random.choice([TradeSide.buy, TradeSide.sell])
            size = round(random.uniform(10, 350), 6)
            base_mid = PRICE_BASE.get(instrument.symbol, 1000.0)
            price = round(base_mid * (1 + random.uniform(-0.003, 0.003)), 2)
            expiry = now + timedelta(seconds=random.randint(10, 60))

            rfq = RFQRequest(
                client_id=client.id,
                instrument_id=instrument.id,
                requested_by_user_id=trader.id,
                side=side,
                size=size,
                quoted_price=price,
                quote_expiry=expiry,
                status=RFQStatus.accepted,
            )
            db.add(rfq)
            await db.flush()

            trade = Trade(
                rfq_id=rfq.id,
                client_id=client.id,
                instrument_id=instrument.id,
                side=side,
                size=size,
                price=price,
                notional_usd=abs(size * price),
                executed_by_user_id=trader.id,
                timestamp=now - timedelta(minutes=random.randint(0, 90)),
            )
            db.add(trade)

            await apply_trade_to_positions(
                db,
                client_id=client.id,
                instrument_id=instrument.id,
                side=side,
                size=size,
                price=price,
            )

            await log_event(
                db,
                event_type="seed.trade.executed",
                entity_type="trade",
                entity_id=f"seed-{_}",
                user_id=trader.id,
                metadata={
                    "client_id": client.id,
                    "instrument_id": instrument.id,
                    "side": side.value,
                    "size": size,
                    "price": price,
                },
            )

        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed_mock_data())
