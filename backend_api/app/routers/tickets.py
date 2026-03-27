from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from typing import Optional
from ..auth import get_current_admin
from ..database import get_db
from ..models.ticket import TicketCreate, TicketUpdate
from ..services.audit_service import log_event
from datetime import datetime

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _serialize(doc) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@router.get("")
async def list_tickets(
    status: Optional[str] = None,
    machine_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    current_admin: dict = Depends(get_current_admin)
):
    db = get_db()
    query = {}
    if status:
        query["status"] = status
    if machine_id:
        query["machine_id"] = machine_id
    if assigned_to:
        query["assigned_to"] = assigned_to
    tickets = await db.tickets.find(query).sort("created_at", -1).to_list(length=None)
    return [_serialize(t) for t in tickets]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_ticket(ticket: TicketCreate, current_admin: dict = Depends(get_current_admin)):
    db = get_db()
    doc = ticket.model_dump()
    doc["status"] = "open"
    doc["created_by"] = current_admin["username"]
    doc["created_at"] = datetime.utcnow()
    result = await db.tickets.insert_one(doc)
    ticket_id = str(result.inserted_id)
    await log_event(db, "ticket_created", actor=current_admin["username"], actor_type="admin",
                    ticket_id=ticket_id, machine_id=ticket.machine_id)
    return {**doc, "_id": ticket_id}


@router.get("/{ticket_id}")
async def get_ticket(ticket_id: str, current_admin: dict = Depends(get_current_admin)):
    db = get_db()
    if not ObjectId.is_valid(ticket_id):
        raise HTTPException(status_code=400, detail="Invalid ticket ID")
    ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _serialize(ticket)


@router.patch("/{ticket_id}")
async def update_ticket(
    ticket_id: str,
    update: TicketUpdate,
    current_admin: dict = Depends(get_current_admin)
):
    db = get_db()
    if not ObjectId.is_valid(ticket_id):
        raise HTTPException(status_code=400, detail="Invalid ticket ID")
    changes = {k: v for k, v in update.model_dump().items() if v is not None}
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Handle steps serialization
    if "steps" in changes:
        changes["steps"] = [s if isinstance(s, dict) else s.model_dump() for s in changes["steps"]]

    result = await db.tickets.update_one({"_id": ObjectId(ticket_id)}, {"$set": changes})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    await log_event(db, "ticket_updated", actor=current_admin["username"], actor_type="admin",
                    ticket_id=ticket_id, machine_id=ticket.get("machine_id"),
                    payload={"changes": list(changes.keys())})
    return {"updated": True}


@router.post("/{ticket_id}/close")
async def close_ticket_admin(ticket_id: str, current_admin: dict = Depends(get_current_admin)):
    db = get_db()
    if not ObjectId.is_valid(ticket_id):
        raise HTTPException(status_code=400, detail="Invalid ticket ID")
    await db.tickets.update_one(
        {"_id": ObjectId(ticket_id)},
        {"$set": {"status": "closed", "closed_at": datetime.utcnow(), "closed_by": current_admin["username"]}}
    )
    ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    await log_event(db, "ticket_closed", actor=current_admin["username"], actor_type="admin",
                    ticket_id=ticket_id, machine_id=ticket.get("machine_id"))
    return {"closed": True}


@router.post("/{ticket_id}/reopen")
async def reopen_ticket(ticket_id: str, current_admin: dict = Depends(get_current_admin)):
    db = get_db()
    if not ObjectId.is_valid(ticket_id):
        raise HTTPException(status_code=400, detail="Invalid ticket ID")
    await db.tickets.update_one(
        {"_id": ObjectId(ticket_id)},
        {"$set": {"status": "open", "closed_at": None, "closed_by": None}}
    )
    ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    await log_event(db, "ticket_reopened", actor=current_admin["username"], actor_type="admin",
                    ticket_id=ticket_id, machine_id=ticket.get("machine_id"))
    return {"reopened": True}
