import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def log_event(
    db: AsyncSession,
    *,
    event_type: str,
    entity_type: str,
    entity_id: str,
    user_id: int | None,
    metadata: dict,
) -> AuditLog:
    previous = await db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
    last = previous.scalar_one_or_none()
    previous_hash = last.immutable_hash if last else "GENESIS"

    payload = {
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "user_id": user_id,
        "metadata": metadata,
        "previous_hash": previous_hash,
    }
    immutable_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    log = AuditLog(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        metadata_json=metadata,
        immutable_hash=immutable_hash,
    )
    db.add(log)
    return log
