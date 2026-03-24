from datetime import datetime
from typing import Optional


async def log_event(
    db,
    event: str,
    actor: Optional[str] = None,
    actor_type: str = "system",
    ticket_id: Optional[str] = None,
    machine_id: Optional[str] = None,
    payload: Optional[dict] = None,
):
    """Append an audit log entry. Never modifies existing records."""
    entry = {
        "event": event,
        "actor": actor,
        "actor_type": actor_type,
        "ticket_id": ticket_id,
        "machine_id": machine_id,
        "payload": payload or {},
        "timestamp": datetime.utcnow(),
    }
    await db.audit_logs.insert_one(entry)
