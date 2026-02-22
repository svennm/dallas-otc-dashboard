from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models import Client, Instrument, RiskLimit, User, UserRole


async def ensure_seed_data(db: AsyncSession) -> None:
    user_count = await db.scalar(select(func.count()).select_from(User))
    if user_count == 0:
        users = [
            User(
                username="admin",
                full_name="Desk Administrator",
                role=UserRole.admin,
                hashed_password=get_password_hash("password123!"),
            ),
            User(
                username="trader",
                full_name="Lead Trader",
                role=UserRole.trader,
                hashed_password=get_password_hash("password123!"),
            ),
            User(
                username="risk",
                full_name="Risk Supervisor",
                role=UserRole.risk,
                hashed_password=get_password_hash("password123!"),
            ),
            User(
                username="viewer",
                full_name="Operations Viewer",
                role=UserRole.viewer,
                hashed_password=get_password_hash("password123!"),
            ),
        ]
        db.add_all(users)

    client_count = await db.scalar(select(func.count()).select_from(Client))
    if client_count == 0:
        clients = [
            Client(name="Lone Star Capital", tier="gold", default_markup_bps=1.8),
            Client(name="Red River Macro", tier="silver", default_markup_bps=2.4),
            Client(name="Bluebonnet Treasury", tier="platinum", default_markup_bps=1.2),
        ]
        db.add_all(clients)

    instrument_count = await db.scalar(select(func.count()).select_from(Instrument))
    if instrument_count == 0:
        instruments = []
        for symbol in settings.market_symbols_list():
            base, quote = symbol.split("-")
            instruments.append(
                Instrument(symbol=symbol, base_asset=base, quote_asset=quote, tick_size=0.01)
            )
        db.add_all(instruments)

    await db.flush()

    limits_count = await db.scalar(select(func.count()).select_from(RiskLimit))
    if limits_count == 0:
        clients_result = await db.execute(select(Client))
        clients = clients_result.scalars().all()
        instruments_result = await db.execute(select(Instrument))
        instruments = instruments_result.scalars().all()

        global_limit = RiskLimit(
            client_id=None,
            instrument_id=None,
            soft_limit_usd=2_500_000,
            hard_limit_usd=4_000_000,
            leverage_limit=3.0,
            requires_supervisor=True,
        )
        db.add(global_limit)

        for client in clients:
            for instrument in instruments:
                multiplier = 1.0
                if client.tier == "gold":
                    multiplier = 1.3
                elif client.tier == "platinum":
                    multiplier = 1.7

                base_soft = 1_500_000 * multiplier
                base_hard = 2_200_000 * multiplier

                db.add(
                    RiskLimit(
                        client_id=client.id,
                        instrument_id=instrument.id,
                        soft_limit_usd=base_soft,
                        hard_limit_usd=base_hard,
                        leverage_limit=3.5,
                        requires_supervisor=True,
                    )
                )

    await db.commit()
