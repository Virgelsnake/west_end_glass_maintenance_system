from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from datetime import datetime
import logging

from ..auth import get_current_admin
from ..database import get_db
from ..models.ticket_type import TicketTypeCreate
from ..services.audit_service import log_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ticket-types", tags=["ticket-types"])


def _serialize(doc) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@router.get("")
async def list_ticket_types(current_admin: dict = Depends(get_current_admin)):
    db = get_db()
    types = await db.ticket_types.find().sort("name", 1).to_list(length=None)
    return [_serialize(t) for t in types]


@router.post("", status_code=201)
async def create_ticket_type(
    body: TicketTypeCreate,
    current_admin: dict = Depends(get_current_admin),
):
    db = get_db()
    existing = await db.ticket_types.find_one({"name": body.name})
    if existing:
        raise HTTPException(status_code=409, detail=f"Ticket type '{body.name}' already exists")

    doc = {
        "name": body.name.strip(),
        "description": body.description,
        "created_at": datetime.utcnow(),
        "created_by": current_admin["username"],
    }
    result = await db.ticket_types.insert_one(doc)
    type_id = str(result.inserted_id)

    await log_event(
        db,
        event="ticket_type_created",
        actor=current_admin["username"],
        actor_type="admin",
        payload={"ticket_type_id": type_id, "name": body.name},
    )

    return {**doc, "_id": type_id}


@router.delete("/{ticket_type_id}", status_code=204)
async def delete_ticket_type(
    ticket_type_id: str,
    current_admin: dict = Depends(get_current_admin),
):
    if not ObjectId.is_valid(ticket_type_id):
        raise HTTPException(status_code=400, detail="Invalid ticket type ID")

    db = get_db()
    existing = await db.ticket_types.find_one({"_id": ObjectId(ticket_type_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Ticket type not found")

    # Guard: cannot delete if tickets reference this type
    count = await db.tickets.count_documents({"ticket_type_id": ticket_type_id})
    if count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete: {count} ticket(s) use this type",
        )

    await db.ticket_types.delete_one({"_id": ObjectId(ticket_type_id)})

    await log_event(
        db,
        event="ticket_type_deleted",
        actor=current_admin["username"],
        actor_type="admin",
        payload={"ticket_type_id": ticket_type_id, "name": existing.get("name")},
    )
