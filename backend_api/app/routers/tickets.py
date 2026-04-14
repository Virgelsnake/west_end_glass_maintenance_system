from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from bson import ObjectId
from typing import Optional, List
from ..auth import get_current_admin
from ..database import get_db
from ..models.ticket import TicketCreate, TicketUpdate
from ..services.audit_service import log_event
from ..services import whatsapp as wa_service
from ..config import settings
from ..utils.exif import extract_photo_metadata
from datetime import datetime
import logging
import os
import shutil

logger = logging.getLogger(__name__)

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
    
    # Send WhatsApp assignment notification if ticket was assigned at creation
    if ticket.assigned_to:
        display_id = ticket.machine_id or ticket.ticket_type_id or "General"
        try:
            tech = await db.users.find_one({"phone_number": ticket.assigned_to})
            tech_name = tech["name"] if tech else ticket.assigned_to
            await wa_service.send_ticket_assignment_notification(
                to=ticket.assigned_to,
                tech_name=tech_name,
                machine_id=display_id,
                ticket_title=ticket.title,
            )
            logger.info("Assignment notification sent to %s for new ticket", ticket.assigned_to)
        except Exception as exc:
            logger.warning("WhatsApp assignment notification failed on creation: %s", exc, exc_info=True)

        try:
            await wa_service.send_start_ticket_button(
                to=ticket.assigned_to,
                ticket_id=ticket_id,
                ticket_title=ticket.title,
                machine_id=display_id,
                description=ticket.description or "",
                priority=ticket.priority or 0,
            )
        except Exception as exc:
            logger.warning("Start-ticket button failed on creation: %s", exc)
    
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

    # Capture old assigned_to before update for notification comparison
    old_ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    old_assigned = old_ticket.get("assigned_to") if old_ticket else None

    result = await db.tickets.update_one({"_id": ObjectId(ticket_id)}, {"$set": changes})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    await log_event(db, "ticket_updated", actor=current_admin["username"], actor_type="admin",
                    ticket_id=ticket_id, machine_id=ticket.get("machine_id"),
                    payload={"changes": list(changes.keys())})

    # Send WhatsApp assignment notification if tech was newly assigned
    new_assigned = changes.get("assigned_to")
    if new_assigned and new_assigned != old_assigned:
        display_id = ticket.get("machine_id") or ticket.get("ticket_type_id") or "General"
        try:
            tech = await db.users.find_one({"phone_number": new_assigned})
            tech_name = tech["name"] if tech else new_assigned
            await wa_service.send_ticket_assignment_notification(
                to=new_assigned,
                tech_name=tech_name,
                machine_id=display_id,
                ticket_title=ticket.get("title", ""),
            )
            logger.info("Assignment notification sent to %s", new_assigned)
        except Exception as exc:
            logger.warning("WhatsApp assignment notification failed: %s", exc, exc_info=True)

        try:
            await wa_service.send_start_ticket_button(
                to=new_assigned,
                ticket_id=ticket_id,
                ticket_title=ticket.get("title", ""),
                machine_id=display_id,
                description=ticket.get("description") or "",
                priority=ticket.get("priority") or 0,
            )
        except Exception as exc:
            logger.warning("Start-ticket button failed on update: %s", exc)

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


_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
_MAX_REFERENCE_PHOTOS = 5


@router.post("/{ticket_id}/reference_photos")
async def add_reference_photos(
    ticket_id: str,
    photos: List[UploadFile] = File(...),
    current_admin: dict = Depends(get_current_admin),
):
    """Attach up to 5 admin reference photos to a ticket and optionally send via WhatsApp."""
    if not ObjectId.is_valid(ticket_id):
        raise HTTPException(status_code=400, detail="Invalid ticket ID")
    if len(photos) > _MAX_REFERENCE_PHOTOS:
        raise HTTPException(status_code=400, detail=f"Maximum {_MAX_REFERENCE_PHOTOS} photos allowed")

    db = get_db()
    ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Check we won't exceed the cap including already-stored ones
    existing = ticket.get("reference_photos", [])
    if len(existing) + len(photos) > _MAX_REFERENCE_PHOTOS:
        raise HTTPException(
            status_code=400,
            detail=f"Adding {len(photos)} would exceed the {_MAX_REFERENCE_PHOTOS}-photo limit "
                   f"({len(existing)} already attached)",
        )

    save_dir = os.path.join(settings.photo_storage_path, ticket_id)
    os.makedirs(save_dir, exist_ok=True)

    saved_filenames: List[str] = []
    for i, photo in enumerate(photos):
        if photo.content_type not in _ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported image type: {photo.content_type}")
        ext = os.path.splitext(photo.filename or "photo.jpg")[1] or ".jpg"
        filename = f"ref_{len(existing) + i}_{int(datetime.utcnow().timestamp())}{ext}"
        file_path = os.path.join(save_dir, filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(photo.file, f)
        saved_filenames.append(filename)

    # Extract and store EXIF metadata for each saved photo
    meta_updates = {}
    for filename in saved_filenames:
        fp = os.path.join(save_dir, filename)
        meta_updates[f"reference_photo_metadata.{filename}"] = extract_photo_metadata(fp)

    # Push filenames into the ticket document
    await db.tickets.update_one(
        {"_id": ObjectId(ticket_id)},
        {
            "$push": {"reference_photos": {"$each": saved_filenames}},
            "$set": meta_updates,
        },
    )

    # Try to send each photo to the assigned technician via WhatsApp
    whatsapp_sent = False
    assigned_to = ticket.get("assigned_to")
    if assigned_to:
        from ..services import whatsapp
        caption = f"Reference photo for ticket: {ticket.get('title', ticket_id)}"
        for filename in saved_filenames:
            file_path = os.path.join(save_dir, filename)
            try:
                await whatsapp.send_ticket_photo(to=assigned_to, file_path=file_path, caption=caption)
                whatsapp_sent = True
            except Exception:
                # Non-fatal — ticket and photos are already saved
                pass

    await log_event(
        db,
        event="reference_photo_added",
        actor=current_admin["username"],
        actor_type="admin",
        ticket_id=ticket_id,
        machine_id=ticket.get("machine_id"),
        payload={"filenames": saved_filenames, "whatsapp_sent": whatsapp_sent},
    )
    return {"filenames": saved_filenames, "whatsapp_sent": whatsapp_sent}
