import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog


async def write_entry(
    session: AsyncSession,
    actor_type: str,
    actor_id: int,
    action: str,
    entity_type: str,
    entity_id: int,
    payload: dict,
) -> AuditLog:
    entry = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )
    session.add(entry)
    await session.flush()
    return entry


async def get_last_n(session: AsyncSession, n: int = 10) -> list[AuditLog]:
    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.action == "mark_session")
        .order_by(AuditLog.created_at.desc())
        .limit(n)
    )
    return list(result.scalars().all())
