"""
Core inbound message processing pipeline.

Shared by:
  - The WhatsApp webhook handler (send_text_message is called by the caller)
  - The CLI simulator endpoint

Responsibilities:
  auth check → update last_activity → save inbound message →
  route to ticket → run Claude agent loop →
  save outbound message + audit log → return result dict
"""

from datetime import datetime
from typing import Optional

from .ticket_service import get_open_tickets_for_machine
from .audit_service import log_event
from . import claude_agent


async def _check_ticket_selection(db, phone_number: str, message_text: str) -> Optional[dict]:
    """
    Check if this is a ticket selection response (single digit 1-9).
    If yes, and the last message was a machine ID with multiple tickets, return the selected ticket.
    Otherwise return None.
    """
    # Only process single digit responses
    if not message_text.strip().isdigit() or len(message_text.strip()) > 2:
        return None
    
    ticket_num = int(message_text.strip())
    if ticket_num < 1 or ticket_num > 9:
        return None
    
    # Get the last message from this user (from conversation history)
    last_msg = await db.messages.find_one(
        {"phone_number": phone_number, "direction": "inbound"},
        sort=[("timestamp", -1)],
        skip=1,  # Skip the current message
    )
    
    if not last_msg or not last_msg.get("content"):
        return None
    
    # Check if last message was a machine ID
    if not last_msg["content"].upper().startswith("WEG-MACHINE-"):
        return None
    
    machine_id = last_msg["content"].upper().strip()
    tickets = await get_open_tickets_for_machine(db, machine_id)
    
    # Check if we have the requested ticket
    if ticket_num > len(tickets):
        return None
    
    # Return the selected ticket
    return tickets[ticket_num - 1]


async def process_inbound_message(
    db,
    phone_number: str,
    message_text: str,
    media_id: Optional[str] = None,
    msg_type: str = "text",
) -> dict:
    """
    Run the full message processing pipeline for one inbound message.

    Does NOT call send_text_message — the caller decides how to deliver
    the response (WhatsApp API vs CLI output).

    Returns a dict with:
        authorized    (bool)
        response_text (str)   — always present
        ticket_id     (str | None)
        ticket_title  (str | None)
        ticket_status (str | None)
        machine_id    (str | None)
        assigned_to   (str)
    """

    # ── 1. Auth check ────────────────────────────────────────────
    user = await db.users.find_one({"phone_number": phone_number, "active": True})
    if not user:
        await log_event(
            db,
            "auth_failure",
            actor=phone_number,
            actor_type="technician",
            payload={"reason": "Phone number not in whitelist"},
        )
        return {
            "authorized": False,
            "response_text": (
                "Sorry, this number is not registered. "
                "Please contact your administrator."
            ),
            "ticket_id": None,
            "ticket_title": None,
            "ticket_status": None,
            "machine_id": None,
            "assigned_to": phone_number,
        }

    # ── 2. Update last_activity ───────────────────────────────────
    await db.users.update_one(
        {"phone_number": phone_number},
        {"$set": {"last_activity": datetime.utcnow()}},
    )

    # ── 3. Save inbound message (ticket_id linked after routing) ──
    inbound_doc = {
        "ticket_id": None,
        "direction": "inbound",
        "phone_number": phone_number,
        "content": message_text or f"[image media_id={media_id}]",
        "media_type": msg_type if msg_type != "text" else None,
        "ai_generated": False,
        "timestamp": datetime.utcnow(),
    }
    inbound_result = await db.messages.insert_one(inbound_doc)

    await log_event(
        db,
        "message_received",
        actor=phone_number,
        actor_type="technician",
        payload={"content": message_text or "[image]"},
    )

    # ── 4. Route to ticket ────────────────────────────────────────
    ticket = None

    # First, check if this is a ticket selection response
    selected_ticket = await _check_ticket_selection(db, phone_number, message_text)
    if selected_ticket:
        ticket = selected_ticket
    elif message_text.upper().startswith("WEG-MACHINE-"):
        machine_id = message_text.upper().strip()
        tickets = await get_open_tickets_for_machine(db, machine_id)
        if not tickets:
            return {
                "authorized": True,
                "response_text": f"No open ticket found for {machine_id}.",
                "ticket_id": None,
                "ticket_title": None,
                "ticket_status": None,
                "machine_id": machine_id,
                "assigned_to": phone_number,
            }
        
        # If multiple tickets, ask user to choose
        if len(tickets) > 1:
            ticket_list = "\n".join([
                f"{i+1}. {t['title']} (Status: {t['status']})"
                for i, t in enumerate(tickets)
            ])
            return {
                "authorized": True,
                "response_text": f"Found {len(tickets)} tickets for {machine_id}:\n\n{ticket_list}\n\nReply with the ticket number (1, 2, etc.) to choose which one to work on.",
                "ticket_id": None,
                "ticket_title": None,
                "ticket_status": None,
                "machine_id": machine_id,
                "assigned_to": phone_number,
            }
        
        ticket = tickets[0]
    else:
        # Most recent in-progress ticket for this technician
        ticket = await db.tickets.find_one(
            {"assigned_to": phone_number, "status": "in_progress"},
            sort=[("priority", -1), ("created_at", 1)],
        )
        if not ticket:
            # Fall back to oldest open ticket
            ticket = await db.tickets.find_one(
                {"assigned_to": phone_number, "status": "open"},
                sort=[("priority", -1), ("created_at", 1)],
            )
        if not ticket:
            return {
                "authorized": True,
                "response_text": (
                    "No open tickets assigned to you. "
                    "Tap an NFC tag or contact your administrator."
                ),
                "ticket_id": None,
                "ticket_title": None,
                "ticket_status": None,
                "machine_id": None,
                "assigned_to": phone_number,
            }

    ticket_id = str(ticket["_id"])

    # Link the inbound message to this ticket now that we know it
    await db.messages.update_one(
        {"_id": inbound_result.inserted_id},
        {"$set": {"ticket_id": ticket_id}},
    )

    # ── 5. Load conversation history ──────────────────────────────
    history_cursor = db.messages.find({"ticket_id": ticket_id}).sort("timestamp", 1)
    conversation_history = await history_cursor.to_list(length=200)

    # ── 6. Run Claude agentic loop ────────────────────────────────
    response_text = await claude_agent.run_agent_loop(
        db=db,
        ticket=ticket,
        user=user,
        message_text=message_text,
        media_id=media_id,
        conversation_history=conversation_history,
    )

    # ── 7. Save outbound message + audit log ──────────────────────
    await db.messages.insert_one({
        "ticket_id": ticket_id,
        "direction": "outbound",
        "phone_number": phone_number,
        "content": response_text,
        "ai_generated": True,
        "timestamp": datetime.utcnow(),
    })
    await log_event(
        db,
        "message_sent",
        actor="system",
        actor_type="system",
        ticket_id=ticket_id,
        machine_id=ticket.get("machine_id"),
        payload={"content": response_text[:200]},
    )

    # ── 8. Reload ticket for fresh status ─────────────────────────
    ticket = await db.tickets.find_one({"_id": ticket["_id"]})

    return {
        "authorized": True,
        "response_text": response_text,
        "ticket_id": ticket_id,
        "ticket_title": ticket.get("title"),
        "ticket_status": ticket.get("status"),
        "machine_id": ticket.get("machine_id"),
        "assigned_to": phone_number,
    }
