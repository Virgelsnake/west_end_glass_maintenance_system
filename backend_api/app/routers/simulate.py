from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ..database import get_db
from ..services.message_processor import process_inbound_message

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
