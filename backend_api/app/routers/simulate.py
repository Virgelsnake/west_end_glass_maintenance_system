from typing import Optional

from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from bson import ObjectId

from ..database import get_db
from ..services.message_processor import process_inbound_message
from ..services.audit_service import log_event
from ..config import settings
from datetime import datetime
import os
import shutil

router = APIRouter(prefix="/simulate", tags=["simulate"])


class SimulateMessageRequest(BaseModel):
    phone_number: str
    message_text: str
    media_id: Optional[str] = None


@router.get("/users")
async def list_simulate_users():
    """
    Return active technicians for the CLI picker.
    No admin auth required — only whitelisted phones can send messages anyway.
    """
    db = get_db()
    cursor = db.users.find(
        {"active": True},
        {"_id": 0, "phone_number": 1, "name": 1, "language": 1},
    )
    return await cursor.to_list(length=None)


@router.post("/message")
async def simulate_message(body: SimulateMessageRequest):
    """
    Simulate an inbound WhatsApp message through the full processing pipeline.

    Auth is the phone number whitelist — exactly the same as a real WhatsApp
    message.  Runs ticket routing → Claude agent loop → saves all messages and
    audit log, then returns the bot's response text plus ticket context.

    Does NOT call send_text_message — the CLI renders the response directly.
    """
    db = get_db()
    return await process_inbound_message(
        db=db,
        phone_number=body.phone_number,
        message_text=body.message_text,
        media_id=body.media_id,
    )


@router.post("/photo")
async def simulate_photo_upload(
    ticket_id: str,
    step_index: int,
    phone_number: str,
    photo: UploadFile = File(...),
):
    """
    Simulate a photo upload from the CLI (for testing without technician portal).
    
    Auth is the phone number whitelist — must be an active technician.
    Saves photo to ticket storage and marks step as complete.
    """
    db = get_db()
    
    # Auth check: verify phone number is active
    from ..auth import is_phone_authorized
    if not await is_phone_authorized(phone_number, db):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Phone number not authorized")
    
    # Validate ticket and step
    if not ObjectId.is_valid(ticket_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid ticket ID")
    
    ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    if not ticket:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Validate content type
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
    if photo.content_type not in allowed_types:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Unsupported image type")
    
    # Save photo
    save_dir = os.path.join(settings.photo_storage_path, ticket_id)
    os.makedirs(save_dir, exist_ok=True)
    ext = os.path.splitext(photo.filename or "photo.jpg")[1] or ".jpg"
    filename = f"step_{step_index}_{int(datetime.utcnow().timestamp())}{ext}"
    file_path = os.path.join(save_dir, filename)
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(photo.file, f)
    
    # Mark step as complete
    now = datetime.utcnow()
    await db.tickets.update_one(
        {"_id": ObjectId(ticket_id)},
        {"$set": {
            f"steps.{step_index}.completed": True,
            f"steps.{step_index}.completed_at": now,
            f"steps.{step_index}.completed_by": phone_number,
            f"steps.{step_index}.photo_path": filename,
            "status": "in_progress",
        }}
    )
    
    # Log event
    await log_event(
        db,
        event="photo_attached",
        actor=phone_number,
        actor_type="technician",
        ticket_id=ticket_id,
        payload={"step_index": step_index, "filename": filename}
    )
    
    return {"saved": True, "filename": filename}

