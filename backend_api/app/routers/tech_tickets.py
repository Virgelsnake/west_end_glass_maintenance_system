from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from bson import ObjectId
from datetime import datetime
import os, shutil
from ..auth import get_current_technician
from ..database import get_db
from ..config import settings
from ..services.audit_service import log_event
from pydantic import BaseModel

router = APIRouter(prefix="/tech", tags=["tech-tickets"])


def _serialize(doc) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@router.get("/my-tickets")
async def get_my_tickets(tech: dict = Depends(get_current_technician)):
    """Return all open/in_progress tickets where this technician is primary or secondary."""
    db = get_db()
    phone = tech["phone_number"]
    tickets = await db.tickets.find({
        "status": {"$in": ["open", "in_progress"]},
        "$or": [{"assigned_to": phone}, {"secondary_assigned_to": phone}],
    }).sort([("status", 1), ("priority", -1)]).to_list(length=None)
    return [_serialize(t) for t in tickets]


@router.post("/tickets/{ticket_id}/steps/{step_index}/complete")
async def complete_step(
    ticket_id: str,
    step_index: int,
    tech: dict = Depends(get_current_technician),
):
    if not ObjectId.is_valid(ticket_id):
        raise HTTPException(status_code=400, detail="Invalid ticket ID")
    db = get_db()
    ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    steps = ticket.get("steps", [])
    if step_index >= len(steps):
        raise HTTPException(status_code=404, detail="Step not found")

    now = datetime.utcnow()
    await db.tickets.update_one(
        {"_id": ObjectId(ticket_id)},
        {"$set": {
            f"steps.{step_index}.completed": True,
            f"steps.{step_index}.completed_at": now,
            f"steps.{step_index}.completed_by": tech["phone_number"],
            "status": "in_progress",
        }}
    )
    await log_event(db, "step_completed", actor=tech["phone_number"], actor_type="technician",
                    ticket_id=ticket_id, payload={"step_index": step_index})
    return {"completed": True}


class NoteBody(BaseModel):
    note_text: str


@router.post("/tickets/{ticket_id}/steps/{step_index}/note")
async def add_note_to_step(
    ticket_id: str,
    step_index: int,
    body: NoteBody,
    tech: dict = Depends(get_current_technician),
):
    if not ObjectId.is_valid(ticket_id):
        raise HTTPException(status_code=400, detail="Invalid ticket ID")
    db = get_db()
    ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    now = datetime.utcnow()
    await db.tickets.update_one(
        {"_id": ObjectId(ticket_id)},
        {"$set": {
            f"steps.{step_index}.completed": True,
            f"steps.{step_index}.completed_at": now,
            f"steps.{step_index}.completed_by": tech["phone_number"],
            f"steps.{step_index}.note_text": body.note_text,
            "status": "in_progress",
        }}
    )
    await log_event(db, "note_added", actor=tech["phone_number"], actor_type="technician",
                    ticket_id=ticket_id, payload={"step_index": step_index})
    return {"saved": True}


@router.post("/tickets/{ticket_id}/steps/{step_index}/photo")
async def upload_photo_to_step(
    ticket_id: str,
    step_index: int,
    photo: UploadFile = File(...),
    tech: dict = Depends(get_current_technician),
):
    if not ObjectId.is_valid(ticket_id):
        raise HTTPException(status_code=400, detail="Invalid ticket ID")

    # Validate content type
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
    if photo.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    db = get_db()
    ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    save_dir = os.path.join(settings.photo_storage_path, ticket_id)
    os.makedirs(save_dir, exist_ok=True)
    ext = os.path.splitext(photo.filename or "photo.jpg")[1] or ".jpg"
    filename = f"step_{step_index}_{int(datetime.utcnow().timestamp())}{ext}"
    file_path = os.path.join(save_dir, filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(photo.file, f)

    now = datetime.utcnow()
    await db.tickets.update_one(
        {"_id": ObjectId(ticket_id)},
        {"$set": {
            f"steps.{step_index}.completed": True,
            f"steps.{step_index}.completed_at": now,
            f"steps.{step_index}.completed_by": tech["phone_number"],
            f"steps.{step_index}.photo_path": filename,
            "status": "in_progress",
        }}
    )
    await log_event(db, "photo_attached", actor=tech["phone_number"], actor_type="technician",
                    ticket_id=ticket_id, payload={"step_index": step_index, "filename": filename})
    return {"saved": True, "filename": filename}
