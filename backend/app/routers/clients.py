from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_roles
from app.models import User, UserRole
from app.schemas import ClientAnalyticsOut
from app.services.analytics import calculate_client_analytics

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("/{client_id}/analytics", response_model=ClientAnalyticsOut)
async def get_client_analytics(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.viewer, UserRole.trader, UserRole.risk, UserRole.admin)),
) -> ClientAnalyticsOut:
    try:
        return await calculate_client_analytics(db, client_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
