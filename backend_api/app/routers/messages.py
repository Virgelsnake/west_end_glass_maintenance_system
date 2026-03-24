from fastapi import APIRouter, Depends
from bson import ObjectId
from ..auth import get_current_admin
from ..database import get_db

router = APIRouter(prefix="/tickets", tags=["messages"])


def _serialize(doc) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@router.get("/{ticket_id}/messages")
async def get_ticket_messages(
    ticket_id: str,
    current_admin: str = Depends(get_current_admin)
):
    """Return full conversation thread for a ticket, chronological order."""
    db = get_db()
    messages = await db.messages.find(
        {"ticket_id": ticket_id}
    ).sort("timestamp", 1).to_list(length=None)
    return [_serialize(m) for m in messages]


@router.post("/{ticket_id}/messages")
async def send_message_from_admin(
    ticket_id: str,
    body: dict,
    current_admin: str = Depends(get_current_admin)
):
    """Admin manually sends a WhatsApp message into a ticket conversation."""
    from ..services.whatsapp import send_text_message
    from ..services.audit_service import log_event
    from datetime import datetime

    db = get_db()
    ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    if not ticket:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Ticket not found")

    text = body.get("text", "").strip()
    if not text:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="text field required")

    phone = ticket.get("assigned_to")
    if phone:
        await send_text_message(phone, text)

    await db.messages.insert_one({
        "ticket_id": ticket_id,
        "direction": "outbound",
        "phone_number": phone or "unknown",
        "content": text,
        "ai_generated": False,
        "timestamp": datetime.utcnow(),
    })
    await log_event(db, "message_sent", actor=current_admin, actor_type="admin",
                    ticket_id=ticket_id, machine_id=ticket.get("machine_id"),
                    payload={"content": text})
    return {"sent": True}
