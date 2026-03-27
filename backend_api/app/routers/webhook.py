import json
from fastapi import APIRouter, Request, Response, HTTPException, Query
from ..config import settings
from ..database import get_db
from ..utils.webhook_verify import verify_webhook_signature
from ..services import whatsapp as wa_service
from ..services.message_processor import process_inbound_message

router = APIRouter(tags=["webhook"])


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Meta Cloud API webhook verification handshake."""
    if hub_mode == "subscribe" and hub_verify_token == settings.meta_verify_token:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(request: Request):
    """Receive inbound WhatsApp messages from Meta Cloud API."""
    body_bytes = await verify_webhook_signature(request)
    payload = json.loads(body_bytes)

    db = get_db()

    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        # Ignore status updates (delivery receipts etc.)
        if "messages" not in value:
            return {"status": "ok"}

        message = value["messages"][0]
        phone_number = message["from"]
        msg_type = message.get("type", "text")

        # Extract text and optional media_id
        message_text = ""
        media_id = None

        if msg_type == "text":
            message_text = message["text"]["body"].strip()
        elif msg_type == "image":
            media_id = message["image"]["id"]
            message_text = message.get("image", {}).get("caption", "")
        else:
            # Unsupported message type — ignore silently
            return {"status": "ok"}

        # Run the shared processing pipeline
        result = await process_inbound_message(
            db=db,
            phone_number=phone_number,
            message_text=message_text,
            media_id=media_id,
            msg_type=msg_type,
        )

        # Deliver the response via WhatsApp
        await wa_service.send_text_message(phone_number, result["response_text"])

    except Exception as e:
        # Never return a non-200 to Meta or it will retry endlessly
        print(f"Webhook processing error: {e}")

    return {"status": "ok"}
