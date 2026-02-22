import asyncio
import random
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.db import AsyncSessionLocal
from app.models import Instrument, MarketPrice
from app.services.ws import manager


class MarketDataService:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False
        self._mid_cache: dict[str, float] = {
            "BTC-USD": 52000.0,
            "ETH-USD": 2800.0,
            "SOL-USD": 115.0,
            "ADA-USD": 0.64,
        }

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run(), name="market-data-loop")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        exchanges = ["coinbase", "kraken", "binance"]

        while self._running:
            try:
                async with AsyncSessionLocal() as db:
                    instruments_result = await db.execute(
                        select(Instrument).where(Instrument.is_active.is_(True))
                    )
                    instruments = instruments_result.scalars().all()

                    for instrument in instruments:
                        base_mid = self._mid_cache.get(instrument.symbol, random.uniform(50, 50000))
                        drift = random.uniform(-0.0015, 0.0015)
                        mid = max(base_mid * (1 + drift), 0.0001)
                        self._mid_cache[instrument.symbol] = mid

                        spread_bps = random.uniform(4.0, 25.0)
                        bid = mid * (1 - spread_bps / 20_000)
                        ask = mid * (1 + spread_bps / 20_000)
                        vwap = mid * (1 + random.uniform(-0.0007, 0.0007))
                        vol = random.uniform(0.01, 0.08)

                        tick = MarketPrice(
                            instrument_id=instrument.id,
                            exchange=random.choice(exchanges),
                            bid=round(bid, 8),
                            ask=round(ask, 8),
                            mid=round(mid, 8),
                            spread_bps=round(spread_bps, 4),
                            rolling_vwap=round(vwap, 8),
                            volatility_5m=round(vol, 6),
                            ts=datetime.now(timezone.utc),
                        )
                        db.add(tick)

                        await manager.broadcast(
                            "prices",
                            {
                                "channel": "prices",
                                "data": {
                                    "instrument_id": instrument.id,
                                    "instrument_symbol": instrument.symbol,
                                    "bid": round(bid, 8),
                                    "ask": round(ask, 8),
                                    "mid": round(mid, 8),
                                    "spread_bps": round(spread_bps, 4),
                                    "rolling_vwap": round(vwap, 8),
                                    "volatility_5m": round(vol, 6),
                                    "ts": datetime.now(timezone.utc).isoformat(),
                                },
                            },
                        )

                    await db.commit()
            except Exception:
                pass

            await asyncio.sleep(settings.market_tick_seconds)


market_data_service = MarketDataService()
