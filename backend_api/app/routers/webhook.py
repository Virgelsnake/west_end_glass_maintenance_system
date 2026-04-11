import json
import logging
from fastapi import APIRouter, Request, Response, HTTPException, Query
from ..config import settings
from ..database import get_db
from ..utils.webhook_verify import verify_webhook_signature
from ..services import whatsapp as wa_service
from ..services.message_processor import process_inbound_message
from ..services import interactive_handler

logger = logging.getLogger("webhook")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

router = APIRouter(tags=["webhook"])


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Meta Cloud API webhook verification handshake."""
    logger.info(
        "Webhook verification request — mode=%s challenge=%s token_match=%s",
        hub_mode,
        hub_challenge,
        hub_verify_token == settings.meta_verify_token,
    )
    if hub_mode == "subscribe" and hub_verify_token == settings.meta_verify_token:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(request: Request):
    """Receive inbound WhatsApp messages from Meta Cloud API."""
    # ── Log raw headers ──────────────────────────────────────────────
    logger.debug(
        "Webhook POST headers: %s",
        dict(request.headers),
    )

    body_bytes = await verify_webhook_signature(request)
    payload = json.loads(body_bytes)

    # ── Log full raw payload ─────────────────────────────────────────
    logger.info(
        "Webhook raw payload:\n%s",
        json.dumps(payload, indent=2),
    )

    db = get_db()

    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        # Ignore events not destined for our configured phone number
        incoming_phone_id = value.get("metadata", {}).get("phone_number_id")
        if incoming_phone_id != settings.meta_phone_number_id:
            logger.info(
                "Webhook for foreign phone_number_id=%s (ours=%s) — ignoring",
                incoming_phone_id,
                settings.meta_phone_number_id,
            )
            return {"status": "ok"}

        # Ignore status updates (delivery receipts etc.)
        if "messages" not in value:
            logger.info("Webhook payload contains no messages (status update?) — ignoring. value keys: %s", list(value.keys()))
            return {"status": "ok"}

        message = value["messages"][0]
        raw_number = message["from"]
        # Meta omits the leading '+' — normalise to E.164 (+XXXXXXXXXXX)
        phone_number = raw_number if raw_number.startswith("+") else "+" + raw_number
        msg_type = message.get("type", "text")

        logger.info(
            "Inbound message — from=%s type=%s msg_id=%s",
            phone_number,
            msg_type,
            message.get("id"),
        )

        # Extract text and optional media_id
        message_text = ""
        media_id = None

        if msg_type == "text":
            message_text = message["text"]["body"].strip()
            logger.info("Text body: %r", message_text)
        elif msg_type == "image":
            media_id = message["image"]["id"]
            message_text = message.get("image", {}).get("caption", "")
            logger.info("Image — media_id=%s caption=%r", media_id, message_text)
        elif msg_type == "interactive":
            interactive_data = message.get("interactive", {})
            interactive_type = interactive_data.get("type")

            if interactive_type == "button_reply":
                reply_id    = interactive_data["button_reply"]["id"]
                reply_title = interactive_data["button_reply"]["title"]
            elif interactive_type == "list_reply":
                reply_id    = interactive_data["list_reply"]["id"]
                reply_title = interactive_data["list_reply"]["title"]
            else:
                logger.info("Unknown interactive type %r — ignoring", interactive_type)
                return {"status": "ok"}

            logger.info("Interactive reply — id=%s title=%s", reply_id, reply_title)
            ih_result = await interactive_handler.handle_interactive(db, phone_number, reply_id, reply_title)
            await _dispatch_interactive_result(phone_number, ih_result, db)
            return {"status": "ok"}
        else:
            logger.info("Unsupported message type %r — ignoring", msg_type)
            return {"status": "ok"}

        # Run the shared processing pipeline
        result = await process_inbound_message(
            db=db,
            phone_number=phone_number,
            message_text=message_text,
            media_id=media_id,
            msg_type=msg_type,
        )

        logger.info("Response to %s: %r", phone_number, result.get("response_text"))

        # Dispatch based on response type
        if result.get("response_type") == "interactive_list":
            # Machine scan with multiple tickets — send a list picker
            list_payload = interactive_handler.build_ticket_list(
                result["machine_id"], result["tickets"]
            )
            await _send_interactive_payload(phone_number, list_payload)
        else:
            # Standard text response
            await wa_service.send_text_message(phone_number, result["response_text"])

            # Send follow-up interactive buttons if present
            followup = result.get("followup_interactive")
            if followup:
                await _send_interactive_payload(phone_number, followup)

    except Exception as e:
        # Never return a non-200 to Meta or it will retry endlessly
        logger.exception("Webhook processing error: %s", e)

    return {"status": "ok"}


async def _send_interactive_payload(phone_number: str, payload: dict) -> None:
    """Send an interactive payload dict (from interactive_handler builders) via WhatsApp."""
    ptype = payload.get("type")
    if ptype == "buttons":
        await wa_service.send_interactive_buttons(
            to=phone_number,
            body_text=payload["body"],
            buttons=payload["buttons"],
        )
    elif ptype == "list":
        await wa_service.send_interactive_list(
            to=phone_number,
            body_text=payload["body"],
            button_label=payload["button_label"],
            sections=payload["sections"],
        )
    elif ptype == "text":
        await wa_service.send_text_message(phone_number, payload["text"])


async def _dispatch_interactive_result(phone_number: str, result: dict, db) -> None:
    """Dispatch the return value from interactive_handler.handle_interactive()."""
    action = result.get("action")

    if action == "send_buttons":
        await wa_service.send_interactive_buttons(
            to=phone_number,
            body_text=result["body"],
            buttons=result["buttons"],
        )
    elif action == "send_list":
        await wa_service.send_interactive_list(
            to=phone_number,
            body_text=result["body"],
            button_label=result["button_label"],
            sections=result["sections"],
        )
    elif action == "send_text":
        await wa_service.send_text_message(phone_number, result["text"])
    elif action == "route_to_claude":
        # Run through full message_processor pipeline as a text message
        proc_result = await process_inbound_message(
            db=db,
            phone_number=phone_number,
            message_text=result.get("message_text", ""),
            msg_type="text",
        )
        await wa_service.send_text_message(phone_number, proc_result["response_text"])
        followup = proc_result.get("followup_interactive")
        if followup:
            await _send_interactive_payload(phone_number, followup)
