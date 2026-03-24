import json
from fastapi import APIRouter, Request, Response, HTTPException, Query
from ..config import settings
from ..database import get_db
from ..auth import get_authorized_user
from ..utils.webhook_verify import verify_webhook_signature
from ..services import whatsapp as wa_service, claude_agent
from ..services.ticket_service import get_open_tickets_for_machine
from ..services.audit_service import log_event
from datetime import datetime

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

        # Authorize phone number
        user = await get_authorized_user(phone_number, db)
        if not user:
            await log_event(db, "auth_failure", actor=phone_number, actor_type="technician",
                            payload={"reason": "Phone number not in whitelist"})
            await wa_service.send_text_message(
                phone_number,
                "Sorry, this number is not registered. Please contact your administrator."
            )
            return {"status": "ok"}

        # Update last_activity
        await db.users.update_one(
            {"phone_number": phone_number},
            {"$set": {"last_activity": datetime.utcnow()}}
        )

        # Log inbound message
        await db.messages.insert_one({
            "ticket_id": None,  # will update below if ticket found
            "direction": "inbound",
            "phone_number": phone_number,
            "content": message_text or f"[image media_id={media_id}]",
            "media_type": msg_type if msg_type != "text" else None,
            "ai_generated": False,
            "timestamp": datetime.utcnow(),
        })
        await log_event(db, "message_received", actor=phone_number, actor_type="technician",
                        payload={"content": message_text or f"[image]"})

        # Determine which ticket we're working on
        # If message looks like a machine ID (e.g. WEG-MACHINE-XXXX), look up that machine
        ticket = None
        if message_text.upper().startswith("WEG-MACHINE-"):
            machine_id = message_text.upper().strip()
            tickets = await get_open_tickets_for_machine(db, machine_id)
            if not tickets:
                await wa_service.send_text_message(
                    phone_number,
                    f"No open ticket found for {machine_id}."
                )
                return {"status": "ok"}
            ticket = tickets[0]
        else:
            # Find the most recent in-progress ticket for this technician
            ticket = await db.tickets.find_one(
                {"assigned_to": phone_number, "status": "in_progress"},
                sort=[("priority", -1), ("created_at", 1)]
            )
            if not ticket:
                # Fall back to any open ticket assigned to them
                ticket = await db.tickets.find_one(
                    {"assigned_to": phone_number, "status": "open"},
                    sort=[("priority", -1), ("created_at", 1)]
                )
            if not ticket:
                await wa_service.send_text_message(
                    phone_number,
                    "No open tickets assigned to you. Tap an NFC tag or contact your administrator."
                )
                return {"status": "ok"}

        ticket_id = str(ticket["_id"])

        # Load conversation history for this ticket
        history_cursor = db.messages.find(
            {"ticket_id": ticket_id}
        ).sort("timestamp", 1)
        conversation_history = await history_cursor.to_list(length=200)

        # Run Claude agentic loop
        response_text = await claude_agent.run_agent_loop(
            db=db,
            ticket=ticket,
            user=user,
            message_text=message_text,
            media_id=media_id,
            conversation_history=conversation_history,
        )

        # Send response to technician
        await wa_service.send_text_message(phone_number, response_text)

        # Log outbound message
        await db.messages.insert_one({
            "ticket_id": ticket_id,
            "direction": "outbound",
            "phone_number": phone_number,
            "content": response_text,
            "ai_generated": True,
            "timestamp": datetime.utcnow(),
        })
        await log_event(db, "message_sent", actor="system", actor_type="system",
                        ticket_id=ticket_id,
                        machine_id=ticket.get("machine_id"),
                        payload={"content": response_text[:200]})

    except Exception as e:
        # Never return a non-200 to Meta or it will retry endlessly
        print(f"Webhook processing error: {e}")

    return {"status": "ok"}
