from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Position, RiskLimit, TradeSide
from app.schemas import RiskCheckResult


def _limit_specificity(limit: RiskLimit) -> int:
    score = 0
    if limit.client_id is not None:
        score += 1
    if limit.instrument_id is not None:
        score += 1
    return score


async def get_effective_limit(
    db: AsyncSession, client_id: int, instrument_id: int
) -> RiskLimit | None:
    result = await db.execute(select(RiskLimit).where(RiskLimit.active.is_(True)))
    limits = result.scalars().all()

    candidates: list[RiskLimit] = []
    for limit in limits:
        if limit.client_id is not None and limit.client_id != client_id:
            continue
        if limit.instrument_id is not None and limit.instrument_id != instrument_id:
            continue
        candidates.append(limit)

    if not candidates:
        return None

    candidates.sort(key=_limit_specificity, reverse=True)
    return candidates[0]


async def evaluate_trade_risk(
    db: AsyncSession,
    *,
    client_id: int,
    instrument_id: int,
    side: TradeSide,
    size: float,
    price: float,
) -> RiskCheckResult:
    result = await db.execute(
        select(Position).where(
            Position.client_id == client_id, Position.instrument_id == instrument_id
        )
    )
    position = result.scalar_one_or_none()
    current_net = float(position.net_size) if position else 0.0

    signed_size = size if side == TradeSide.buy else -size
    projected_net = current_net + signed_size
    projected_exposure = abs(projected_net * price)

    limit = await get_effective_limit(db, client_id, instrument_id)
    if limit is None:
        return RiskCheckResult(
            soft_breach=False,
            hard_breach=False,
            projected_exposure_usd=projected_exposure,
            message="No active limit configured",
        )

    soft_limit = float(limit.soft_limit_usd)
    hard_limit = float(limit.hard_limit_usd)
    soft_breach = projected_exposure >= soft_limit
    hard_breach = projected_exposure >= hard_limit

    message = "Within risk limits"
    if hard_breach:
        message = "Hard limit breach"
    elif soft_breach:
        message = "Soft limit breach"

    return RiskCheckResult(
        soft_breach=soft_breach,
        hard_breach=hard_breach,
        projected_exposure_usd=projected_exposure,
        soft_limit_usd=soft_limit,
        hard_limit_usd=hard_limit,
        message=message,
    )


async def apply_trade_to_positions(
    db: AsyncSession,
    *,
    client_id: int,
    instrument_id: int,
    side: TradeSide,
    size: float,
    price: float,
) -> Position:
    result = await db.execute(
        select(Position).where(
            Position.client_id == client_id, Position.instrument_id == instrument_id
        )
    )
    position = result.scalar_one_or_none()

    signed_size = size if side == TradeSide.buy else -size

    if position is None:
        position = Position(
            client_id=client_id,
            instrument_id=instrument_id,
            net_size=signed_size,
            avg_price=price,
            usd_exposure=abs(signed_size * price),
        )
        db.add(position)
        return position

    old_net = float(position.net_size)
    old_avg = float(position.avg_price)
    new_net = old_net + signed_size

    if abs(new_net) < 1e-12:
        new_avg = 0.0
    else:
        old_cost = old_net * old_avg
        new_cost = old_cost + (signed_size * price)
        new_avg = new_cost / new_net

    position.net_size = new_net
    position.avg_price = new_avg
    position.usd_exposure = abs(new_net * price)
    return position
