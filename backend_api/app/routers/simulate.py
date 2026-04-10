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

    ALSO sends the response back to the user's WhatsApp number so they see it
    on their phone in real-time (not just on screen).
    """
    db = get_db()
    result = await process_inbound_message(
        db=db,
        phone_number=body.phone_number,
        message_text=body.message_text,
        media_id=body.media_id,
    )
    
    # Send response back to WhatsApp (so user sees it on their phone)
    try:
        from ..services import whatsapp as wa_service
        response_text = result.get("response_text", "")
        if response_text:
            phone = body.phone_number
            print(f"[SIMULATE] Sending to: {phone}")
            print(f"[SIMULATE] Message preview: {response_text[:100]}...")
            await wa_service.send_text_message(phone, response_text)
            print(f"[SIMULATE] ✓ Message sent successfully to WhatsApp")
        else:
            print(f"[SIMULATE] No response text to send")
    except Exception as e:
        # Log error but don't fail the response — user still sees it on screen
        import traceback
        print(f"[SIMULATE] ❌ FAILED to send response to WhatsApp: {e}")
        print(f"[SIMULATE] Traceback: {traceback.format_exc()}")
    
    return result


class SimulateTemplateRequest(BaseModel):
    phone_number: str
    name: str = "Test User"
    datetime_str: str = ""
    title: str = "Test Ticket"
    machine: str = "Test Machine"


@router.post("/template")
async def simulate_template(body: SimulateTemplateRequest):
    """
    Fire the test_maintenance_chat WhatsApp template with custom text.
    Use this to re-open the 24h conversation window or test template delivery.
    """
    from ..services import whatsapp as wa_service
    from datetime import datetime as dt

    datetime_str = body.datetime_str or dt.utcnow().strftime("%B %d, %Y at %I:%M %p UTC")

    result = await wa_service.send_ticket_assignment_notification(
        to=body.phone_number,
        tech_name=body.name,
        machine_id=body.machine,
    )
    return {"status": "sent", "meta_response": result}


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


@router.post("/ref-photo")
async def simulate_ref_photo_upload(
    ticket_id: str,
    phone_number: str,
    photo: UploadFile = File(...),
):
    """
    Simulate an admin attaching a reference photo to a ticket and 'sending' it via WhatsApp.

    This endpoint is for CLI testing only — it mocks WhatsApp delivery (no real Meta API call).
    Auth is the technician phone whitelist.
    """
    from fastapi import HTTPException
    from ..auth import is_phone_authorized

    db = get_db()

    if not await is_phone_authorized(phone_number, db):
        raise HTTPException(status_code=401, detail="Phone number not authorized")

    if not ObjectId.is_valid(ticket_id):
        raise HTTPException(status_code=400, detail="Invalid ticket ID")

    ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    _MAX_REFERENCE_PHOTOS = 5
    existing = ticket.get("reference_photos", [])
    if len(existing) >= _MAX_REFERENCE_PHOTOS:
        raise HTTPException(
            status_code=400,
            detail=f"Ticket already has {_MAX_REFERENCE_PHOTOS} reference photos",
        )

    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
    if photo.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    save_dir = os.path.join(settings.photo_storage_path, ticket_id)
    os.makedirs(save_dir, exist_ok=True)
    ext = os.path.splitext(photo.filename or "photo.jpg")[1] or ".jpg"
    filename = f"ref_{len(existing)}_{int(datetime.utcnow().timestamp())}{ext}"
    file_path = os.path.join(save_dir, filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(photo.file, f)

    await db.tickets.update_one(
        {"_id": ObjectId(ticket_id)},
        {"$push": {"reference_photos": filename}},
    )

    assigned_to = ticket.get("assigned_to")

    await log_event(
        db,
        event="reference_photo_added",
        actor=phone_number,
        actor_type="technician",
        ticket_id=ticket_id,
        payload={"filename": filename, "whatsapp_simulated": True},
    )

    return {
        "saved": True,
        "filename": filename,
        "whatsapp_simulated": True,
        "would_send_to": assigned_to,
    }

