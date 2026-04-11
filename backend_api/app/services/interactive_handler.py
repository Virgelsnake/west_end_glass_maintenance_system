"""
WhatsApp Interactive Message Handler
=====================================
Handles inbound interactive replies (button taps and list selections) from
WhatsApp technicians.

The key principle: structured button taps bypass Claude entirely.
The tech taps a button → we call ticket_service directly → instant response.
Claude is only called for free text, help requests, and edge cases.

Button ID convention (underscore-delimited, no spaces):
  ticket_select_{ticket_id}            — tap from ticket list picker
  step_done_{ticket_id}_{step_index}   — confirm step complete
  step_issue_{ticket_id}_{step_index}  — flag an issue on a step
  step_note_{ticket_id}_{step_index}_{slug} — preset note (normal/low/critical)
  ticket_close_{ticket_id}             — close ticket after all steps done
  ticket_review_{ticket_id}            — review all steps (routes to Claude)
  ticket_switch_{machine_id}           — switch ticket on current machine

Return value from handle_interactive():
  {"action": "send_buttons",  "body": str, "buttons": [...]}
  {"action": "send_list",     "body": str, "button_label": str, "sections": [...]}
  {"action": "send_text",     "text": str}
  {"action": "route_to_claude", "message_text": str, "ticket_id": str|None}
"""

import logging
from bson import ObjectId
from . import ticket_service

logger = logging.getLogger("interactive_handler")

# Priority badge for list display
PRIORITY_BADGE = {1: "P1 🔴", 2: "P2 🟡", 3: "P3 🟢"}

# Preset note slugs → display text saved to DB
NOTE_SLUG_MAP = {
    "normal":   "Normal",
    "low":      "Low",
    "critical": "CRITICAL — immediate attention required",
}


# ── ID parsing ────────────────────────────────────────────────────────────────

def parse_reply_id(reply_id: str) -> dict:
    """
    Parse a button/list reply ID into a structured dict.

    Examples:
      "step_done_abc123_0"          → {"action": "step_done", "ticket_id": "abc123", "step_index": 0}
      "ticket_select_abc123"        → {"action": "ticket_select", "ticket_id": "abc123"}
      "step_note_abc123_2_low"      → {"action": "step_note", "ticket_id": "abc123", "step_index": 2, "slug": "low"}
      "ticket_close_abc123"         → {"action": "ticket_close", "ticket_id": "abc123"}
      "ticket_switch_WEG-ARRISOR-01" → {"action": "ticket_switch", "machine_id": "WEG-ARRISOR-01"}
    """
    parts = reply_id.split("_", 3)  # at most 4 parts

    if len(parts) < 2:
        return {"action": "unknown"}

    prefix = parts[0]   # "ticket" or "step"
    action = parts[1]   # "select", "done", "issue", "note", "close", "review", "switch"

    # ── ticket_* actions ─────────────────────────────────────────────────────
    if prefix == "ticket":
        if action == "select" and len(parts) >= 3:
            return {"action": "ticket_select", "ticket_id": parts[2]}

        if action == "close" and len(parts) >= 3:
            return {"action": "ticket_close", "ticket_id": parts[2]}

        if action == "review" and len(parts) >= 3:
            return {"action": "ticket_review", "ticket_id": parts[2]}

        if action == "switch" and len(parts) >= 3:
            # machine_id may contain hyphens — rejoin everything after "switch_"
            machine_id = reply_id.split("ticket_switch_", 1)[1]
            return {"action": "ticket_switch", "machine_id": machine_id}

    # ── step_* actions ────────────────────────────────────────────────────────
    elif prefix == "step":
        if action in ("done", "issue") and len(parts) >= 4:
            try:
                step_index = int(parts[3])
            except ValueError:
                return {"action": "unknown"}
            return {
                "action": f"step_{action}",
                "ticket_id": parts[2],
                "step_index": step_index,
            }

        if action == "note" and len(parts) >= 4:
            # parts[3] is "{step_index}_{slug}" — split once more
            remainder = parts[3].split("_", 1)
            if len(remainder) < 2:
                return {"action": "unknown"}
            try:
                step_index = int(remainder[0])
            except ValueError:
                return {"action": "unknown"}
            slug = remainder[1]
            return {
                "action": "step_note",
                "ticket_id": parts[2],
                "step_index": step_index,
                "slug": slug,
            }

    return {"action": "unknown"}


# ── Payload builders ─────────────────────────────────────────────────────────

def build_step_buttons(ticket: dict) -> dict | None:
    """
    Build an interactive button payload for the next incomplete step.
    Returns None if all steps are complete (caller should offer close-ticket buttons).

    For photo steps: returns a plain text dict instead (no buttons needed — tech
    sends the photo directly).
    """
    ticket_id = str(ticket["_id"])

    for step in ticket.get("steps", []):
        if step.get("completed", False):
            continue

        idx = step["step_index"]
        label = step["label"]
        ctype = step.get("completion_type", "confirmation")

        if ctype == "photo":
            # No interactive buttons — just a text prompt
            return {
                "type": "text",
                "text": f"📷 Step {idx + 1}: {label}\n\nJust send a photo — no need to type anything.",
            }

        if ctype in ("confirmation", "manual"):
            return {
                "type": "buttons",
                "body": f"Step {idx + 1} of {len(ticket['steps'])}: {label}",
                "buttons": [
                    {"id": f"step_done_{ticket_id}_{idx}", "title": "Done"},
                    {"id": f"step_issue_{ticket_id}_{idx}", "title": "Report Issue"},
                ],
            }

        if ctype == "note":
            return {
                "type": "buttons",
                "body": f"Step {idx + 1} of {len(ticket['steps'])}: {label}\n\n(Or type a custom note)",
                "buttons": [
                    {"id": f"step_note_{ticket_id}_{idx}_normal",   "title": "Normal"},
                    {"id": f"step_note_{ticket_id}_{idx}_low",      "title": "Low"},
                    {"id": f"step_note_{ticket_id}_{idx}_critical", "title": "Critical"},
                ],
            }

        # Unknown type — fallback to done/issue buttons
        return {
            "type": "buttons",
            "body": f"Step {idx + 1}: {label}",
            "buttons": [
                {"id": f"step_done_{ticket_id}_{idx}", "title": "Done"},
                {"id": f"step_issue_{ticket_id}_{idx}", "title": "Report Issue"},
            ],
        }

    # All steps complete
    return None


def build_close_ticket_buttons(ticket: dict) -> dict:
    """Build the 'all steps done — close ticket?' button payload."""
    ticket_id = str(ticket["_id"])
    total = len(ticket.get("steps", []))
    return {
        "type": "buttons",
        "body": f"All {total} steps complete! Ready to close this ticket?",
        "buttons": [
            {"id": f"ticket_close_{ticket_id}",  "title": "Close Ticket"},
            {"id": f"ticket_review_{ticket_id}", "title": "Review Steps"},
        ],
    }


def build_ticket_list(machine_id: str, tickets: list) -> dict:
    """
    Build an interactive list picker payload for a machine's open tickets.
    Truncates title to 24 chars (Meta limit).
    """
    rows = []
    for t in tickets[:10]:  # Meta max 10 rows
        tid = str(t["_id"])
        priority = t.get("priority", 3)
        badge = PRIORITY_BADGE.get(priority, "")
        title = t.get("title", "Untitled")[:24]
        status = t.get("status", "open")
        rows.append({
            "id": f"ticket_select_{tid}",
            "title": title,
            "description": f"{badge} · {status}",
        })

    return {
        "type": "list",
        "body": f"Open tickets for {machine_id} — tap to select one:",
        "button_label": "View Tickets",
        "sections": [{"title": machine_id, "rows": rows}],
    }


# ── Main entry point ─────────────────────────────────────────────────────────

async def handle_interactive(
    db,
    phone_number: str,
    reply_id: str,
    reply_title: str,
) -> dict:
    """
    Main entry point for interactive replies from webhook.py.

    Returns one of:
      {"action": "send_buttons",  "body": str, "buttons": list}
      {"action": "send_list",     "body": str, "button_label": str, "sections": list}
      {"action": "send_text",     "text": str}
      {"action": "route_to_claude", "message_text": str, "ticket_id": str|None}
    """
    parsed = parse_reply_id(reply_id)
    action = parsed.get("action", "unknown")
    logger.info("Interactive action=%s parsed=%s", action, parsed)

    # ── ticket_select: tech picked a ticket from the list ─────────────────────
    if action == "ticket_select":
        ticket_id = parsed["ticket_id"]
        await db.users.update_one(
            {"phone_number": phone_number},
            {"$set": {"active_ticket_id": ticket_id}},
        )
        # Route to Claude to greet the ticket and present first step
        return {
            "action": "route_to_claude",
            "message_text": f"Starting on: {reply_title}",
            "ticket_id": ticket_id,
        }

    # ── step_done: tech confirmed a step ─────────────────────────────────────
    elif action == "step_done":
        ticket_id = parsed["ticket_id"]
        step_index = parsed["step_index"]
        ticket = await ticket_service.check_off_step(db, ticket_id, step_index, phone_number)
        if ticket is None:
            return {"action": "send_text", "text": "Could not find that ticket. Please scan the NFC tag again."}

        # Reload fresh ticket
        ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
        next_payload = build_step_buttons(ticket)

        if next_payload is None:
            # All steps done — offer close
            payload = build_close_ticket_buttons(ticket)
        else:
            payload = next_payload

        step_count = sum(1 for s in ticket.get("steps", []) if s.get("completed"))
        total = len(ticket.get("steps", []))

        if payload["type"] == "text":
            return {"action": "send_text", "text": payload["text"]}

        return {
            "action": "send_buttons",
            "body": f"Step {step_index + 1} done ({step_count}/{total} complete).\n\n{payload['body']}",
            "buttons": payload["buttons"],
        }

    # ── step_issue: tech flagged a problem — hand off to Claude ──────────────
    elif action == "step_issue":
        ticket_id = parsed["ticket_id"]
        step_index = parsed["step_index"]
        ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
        step_label = ""
        if ticket:
            for s in ticket.get("steps", []):
                if s["step_index"] == step_index:
                    step_label = s["label"]
                    break
        return {
            "action": "route_to_claude",
            "message_text": f"I have an issue with step {step_index + 1}: {step_label}",
            "ticket_id": ticket_id,
        }

    # ── step_note: tech tapped a preset note value ────────────────────────────
    elif action == "step_note":
        ticket_id = parsed["ticket_id"]
        step_index = parsed["step_index"]
        slug = parsed.get("slug", "normal")
        note_text = NOTE_SLUG_MAP.get(slug, slug.capitalize())

        ticket = await ticket_service.attach_note_to_step(db, ticket_id, step_index, note_text, phone_number)
        if ticket is None:
            return {"action": "send_text", "text": "Could not save note. Please try again."}

        ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
        next_payload = build_step_buttons(ticket)

        if next_payload is None:
            payload = build_close_ticket_buttons(ticket)
        else:
            payload = next_payload

        if payload["type"] == "text":
            return {"action": "send_text", "text": f"Note saved: {note_text}\n\n{payload['text']}"}

        return {
            "action": "send_buttons",
            "body": f"Note saved: {note_text}\n\n{payload['body']}",
            "buttons": payload["buttons"],
        }

    # ── ticket_close: tech confirmed close ────────────────────────────────────
    elif action == "ticket_close":
        ticket_id = parsed["ticket_id"]
        closed_ticket = await ticket_service.close_ticket(db, ticket_id, phone_number)
        machine_id = closed_ticket.get("machine_id") if closed_ticket else None

        await db.users.update_one(
            {"phone_number": phone_number},
            {"$set": {"active_ticket_id": None}},
        )

        if machine_id:
            remaining = await ticket_service.get_open_tickets_for_machine(db, machine_id)
            if remaining:
                if len(remaining) == 1:
                    # Auto-select the only remaining ticket and route to Claude
                    await db.users.update_one(
                        {"phone_number": phone_number},
                        {"$set": {"active_ticket_id": str(remaining[0]["_id"])}},
                    )
                    return {
                        "action": "route_to_claude",
                        "message_text": f"Starting on: {remaining[0]['title']}",
                        "ticket_id": str(remaining[0]["_id"]),
                    }
                else:
                    list_payload = build_ticket_list(machine_id, remaining)
                    return {
                        "action": "send_list",
                        "body": f"Ticket closed. {len(remaining)} ticket(s) still open on {machine_id}:",
                        "button_label": list_payload["button_label"],
                        "sections": list_payload["sections"],
                    }

        return {"action": "send_text", "text": "Ticket closed. No more open tickets. Great work!"}

    # ── ticket_review: show all steps — route to Claude ──────────────────────
    elif action == "ticket_review":
        ticket_id = parsed["ticket_id"]
        return {
            "action": "route_to_claude",
            "message_text": "Show me a summary of all steps on this ticket.",
            "ticket_id": ticket_id,
        }

    # ── ticket_switch: tech wants to change ticket ────────────────────────────
    elif action == "ticket_switch":
        machine_id = parsed["machine_id"]
        tickets = await ticket_service.get_open_tickets_for_machine(db, machine_id)
        await db.users.update_one(
            {"phone_number": phone_number},
            {"$set": {"active_ticket_id": None, "active_machine_id": machine_id}},
        )
        if not tickets:
            return {"action": "send_text", "text": f"No open tickets for {machine_id}."}
        if len(tickets) == 1:
            await db.users.update_one(
                {"phone_number": phone_number},
                {"$set": {"active_ticket_id": str(tickets[0]["_id"])}},
            )
            return {
                "action": "route_to_claude",
                "message_text": f"Starting on: {tickets[0]['title']}",
                "ticket_id": str(tickets[0]["_id"]),
            }
        list_payload = build_ticket_list(machine_id, tickets)
        return {
            "action": "send_list",
            "body": list_payload["body"],
            "button_label": list_payload["button_label"],
            "sections": list_payload["sections"],
        }

    # ── Unknown / fallback — let Claude handle it ─────────────────────────────
    logger.warning("Unknown interactive reply_id=%s — routing to Claude", reply_id)
    return {
        "action": "route_to_claude",
        "message_text": reply_title,
        "ticket_id": None,
    }
