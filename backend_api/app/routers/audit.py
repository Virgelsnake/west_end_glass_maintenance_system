from fastapi import APIRouter, Depends
from typing import Optional
from ..auth import get_current_admin
from ..database import get_db

router = APIRouter(prefix="/audit", tags=["audit"])


def _serialize(doc) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@router.get("")
async def get_audit_logs(
    ticket_id: Optional[str] = None,
    machine_id: Optional[str] = None,
    actor: Optional[str] = None,
    event: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    current_admin: dict = Depends(get_current_admin),
):
    """Return audit log entries with optional filters. Most recent first."""
    db = get_db()
    query = {}
    if ticket_id:
        query["ticket_id"] = ticket_id
    if machine_id:
        query["machine_id"] = machine_id
    if actor:
        query["actor"] = actor
    if event:
        query["event"] = event

    logs = (
        await db.audit_logs.find(query)
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
        .to_list(length=limit)
    )
    return [_serialize(log) for log in logs]
