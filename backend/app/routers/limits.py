from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_roles
from app.models import Client, Instrument, Position, RiskLimit, User, UserRole
from app.schemas import RiskLimitOut, RiskOverrideRequest, RiskOverrideResponse
from app.services.audit import log_event
from app.services.risk import get_effective_limit

router = APIRouter(prefix="/limits", tags=["risk_limits"])


@router.get("", response_model=list[RiskLimitOut])
async def list_limits(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.viewer, UserRole.trader, UserRole.risk, UserRole.admin)),
) -> list[RiskLimitOut]:
    stmt = (
        select(RiskLimit, Client.name, Instrument.symbol)
        .outerjoin(Client, RiskLimit.client_id == Client.id)
        .outerjoin(Instrument, RiskLimit.instrument_id == Instrument.id)
        .order_by(RiskLimit.id)
    )
    rows = (await db.execute(stmt)).all()

    return [
        RiskLimitOut(
            id=limit.id,
            client_id=limit.client_id,
            client_name=client_name,
            instrument_id=limit.instrument_id,
            instrument_symbol=instrument_symbol,
            soft_limit_usd=float(limit.soft_limit_usd),
            hard_limit_usd=float(limit.hard_limit_usd),
            leverage_limit=float(limit.leverage_limit),
            requires_supervisor=limit.requires_supervisor,
            active=limit.active,
        )
        for limit, client_name, instrument_symbol in rows
    ]


@router.get("/alerts")
async def list_limit_alerts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.viewer, UserRole.trader, UserRole.risk, UserRole.admin)),
) -> dict:
    positions = (await db.execute(select(Position))).scalars().all()
    alerts = []

    for position in positions:
        limit = await get_effective_limit(db, position.client_id, position.instrument_id)
        if limit is None:
            continue

        exposure = abs(float(position.usd_exposure))
        soft_limit = float(limit.soft_limit_usd)
        hard_limit = float(limit.hard_limit_usd)

        if exposure >= hard_limit:
            severity = "hard"
        elif exposure >= soft_limit:
            severity = "soft"
        else:
            continue

        client = await db.get(Client, position.client_id)
        instrument = await db.get(Instrument, position.instrument_id)

        alerts.append(
            {
                "client_id": position.client_id,
                "client_name": client.name if client else None,
                "instrument_id": position.instrument_id,
                "instrument_symbol": instrument.symbol if instrument else None,
                "exposure_usd": exposure,
                "soft_limit_usd": soft_limit,
                "hard_limit_usd": hard_limit,
                "severity": severity,
            }
        )

    return {"alerts": alerts}


@router.post("/override", response_model=RiskOverrideResponse)
async def request_override(
    payload: RiskOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.risk, UserRole.admin)),
) -> RiskOverrideResponse:
    limit = await get_effective_limit(db, payload.client_id, payload.instrument_id)

    status = "approved"
    message = "Override approved"
    if limit and limit.requires_supervisor and current_user.role != UserRole.admin:
        status = "pending_supervisor_approval"
        message = "Override request logged; supervisor approval required"

    await log_event(
        db,
        event_type="risk.override_requested",
        entity_type="risk_limit",
        entity_id=f"{payload.client_id}:{payload.instrument_id}",
        user_id=current_user.id,
        metadata={
            "client_id": payload.client_id,
            "instrument_id": payload.instrument_id,
            "proposed_notional_usd": payload.proposed_notional_usd,
            "reason": payload.reason,
            "status": status,
        },
    )
    await db.commit()

    return RiskOverrideResponse(
        status=status,
        approved_by_role=current_user.role.value,
        message=message,
    )
