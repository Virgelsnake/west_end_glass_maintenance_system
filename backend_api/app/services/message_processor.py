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

from bson import ObjectId
from .ticket_service import get_open_tickets_for_machine
from .audit_service import log_event
from . import claude_agent


async def _set_user_context(db, phone_number: str, **kwargs) -> None:
    """Update user session context fields (active_machine_id, active_ticket_id, etc.)."""
    if kwargs:
        await db.users.update_one(
            {"phone_number": phone_number},
            {"$set": kwargs},
        )


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

    # ── 4. Route to ticket (state-driven session context) ─────────
    ticket = None
    msg_upper = (message_text or "").upper().strip()

    # 4a. Machine ID scan — start or restart a machine session
    if msg_upper.startswith("WEG-MACHINE-"):
        machine_id = msg_upper
        tickets = await get_open_tickets_for_machine(db, machine_id)
        if not tickets:
            await _set_user_context(db, phone_number, active_machine_id=machine_id, active_ticket_id=None)
            return {
                "authorized": True,
                "response_text": f"No open tickets for {machine_id}.",
                "ticket_id": None,
                "ticket_title": None,
                "ticket_status": None,
                "machine_id": machine_id,
                "assigned_to": phone_number,
            }
        if len(tickets) == 1:
            ticket = tickets[0]
            await _set_user_context(
                db, phone_number,
                active_machine_id=machine_id,
                active_ticket_id=str(ticket["_id"]),
            )
        else:
            # Multiple tickets — store machine context, wait for selection
            await _set_user_context(db, phone_number, active_machine_id=machine_id, active_ticket_id=None)
            ticket_list = "\n".join([
                f"{i+1}. {t['title']} (status: {t['status']})"
                for i, t in enumerate(tickets)
            ])
            return {
                "authorized": True,
                "response_text": (
                    f"Found {len(tickets)} tickets for {machine_id}:\n\n"
                    f"{ticket_list}\n\n"
                    "Reply with the number of the ticket to work on."
                ),
                "ticket_id": None,
                "ticket_title": None,
                "ticket_status": None,
                "machine_id": machine_id,
                "assigned_to": phone_number,
            }

    # 4b. Bare digit — selecting from a machine's open ticket list
    elif msg_upper.isdigit() and user.get("active_machine_id") and not user.get("active_ticket_id"):
        ticket_num = int(msg_upper)
        machine_id = user["active_machine_id"]
        tickets = await get_open_tickets_for_machine(db, machine_id)
        if not tickets or ticket_num < 1 or ticket_num > len(tickets):
            count = len(tickets) if tickets else 0
            return {
                "authorized": True,
                "response_text": f"Invalid selection. Reply with a number between 1 and {count}.",
                "ticket_id": None,
                "ticket_title": None,
                "ticket_status": None,
                "machine_id": machine_id,
                "assigned_to": phone_number,
            }
        ticket = tickets[ticket_num - 1]
        await _set_user_context(db, phone_number, active_ticket_id=str(ticket["_id"]))
        # Reframe the digit message so Claude knows this is a fresh selection
        message_text = f"I'm working on ticket {ticket_num}: {ticket.get('title', 'Untitled')}"

    # 4b2. Show/list tickets request mid-ticket, or switch request
    elif user.get("active_ticket_id") and any(
        keyword in msg_upper for keyword in ["CHANGE", "SWITCH", "OTHER", "BACK", "DIFFERENT", "SHOW", "LIST", "WHAT TICKETS", "WHAT DO I HAVE"]
    ):
        machine_id = user.get("active_machine_id")
        if machine_id:
            tickets = await get_open_tickets_for_machine(db, machine_id)
            await _set_user_context(db, phone_number, active_ticket_id=None)
            if len(tickets) > 1:
                ticket_list = "\n".join([
                    f"{i+1}. {t['title']} (status: {t['status']})"
                    for i, t in enumerate(tickets)
                ])
                return {
                    "authorized": True,
                    "response_text": (
                        f"Tickets for {machine_id}:\n\n"
                        f"{ticket_list}\n\n"
                        "Reply with the number to switch, or continue with your current ticket."
                    ),
                    "ticket_id": None,
                    "ticket_title": None,
                    "ticket_status": None,
                    "machine_id": machine_id,
                    "assigned_to": phone_number,
                }
            else:
                # Only one ticket
                return {
                    "authorized": True,
                    "response_text": f"Only one ticket open for {machine_id}. Continue with it.",
                    "ticket_id": None,
                    "ticket_title": None,
                    "ticket_status": None,
                    "machine_id": machine_id,
                    "assigned_to": phone_number,
                }

    # 4c. Active ticket session — already picked or mid-flow
    if ticket is None and user.get("active_ticket_id"):
        tid = user["active_ticket_id"]
        if ObjectId.is_valid(str(tid)):
            ticket = await db.tickets.find_one({"_id": ObjectId(str(tid))})
        if not ticket or ticket.get("status") == "closed":
            # Stale context — clear it and fall through to 4d
            await _set_user_context(db, phone_number, active_ticket_id=None)
            ticket = None

    # 4d. Fallback — oldest assigned open/in_progress ticket
    if ticket is None:
        ticket = await db.tickets.find_one(
            {"assigned_to": phone_number, "status": {"$in": ["open", "in_progress"]}},
            sort=[("priority", -1), ("created_at", 1)],
        )
        if ticket:
            await _set_user_context(
                db, phone_number,
                active_machine_id=ticket.get("machine_id"),
                active_ticket_id=str(ticket["_id"]),
            )

    if ticket is None:
        return {
            "authorized": True,
            "response_text": (
                "No active ticket. Scan an NFC tag or contact your administrator."
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
