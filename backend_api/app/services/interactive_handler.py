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
  ticket_start_{ticket_id}             — tap "Begin Steps" on detail card
  ticket_close_{ticket_id}             — close ticket after all steps done
  ticket_review_{ticket_id}            — review all steps (routes to Claude)
  ticket_restart_{ticket_id}           — re-present step 1 buttons
  ticket_switch_{machine_id}           — switch ticket on current machine
  step_done_{ticket_id}_{step_index}   — confirm step complete
  step_issue_{ticket_id}_{step_index}  — flag an issue on a step
  tech_my_tickets                      — show all tickets assigned to this tech
  menu_open_{ticket_id}                — open the in-step navigation menu

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

def _priority_badge(priority: int) -> str:
    return PRIORITY_BADGE.get(priority, f"P{priority}")


# ── ID parsing ────────────────────────────────────────────────────────────────

def parse_reply_id(reply_id: str) -> dict:
    """
    Parse a button/list reply ID into a structured dict.

    Examples:
      "step_done_abc123_0"          → {"action": "step_done", "ticket_id": "abc123", "step_index": 0}
      "ticket_select_abc123"        → {"action": "ticket_select", "ticket_id": "abc123"}
      "ticket_close_abc123"         → {"action": "ticket_close", "ticket_id": "abc123"}
      "ticket_switch_WEG-ARRISOR-01" → {"action": "ticket_switch", "machine_id": "WEG-ARRISOR-01"}
      "tech_my_tickets"             → {"action": "tech_my_tickets"}
      "menu_open_abc123"            → {"action": "menu_open", "ticket_id": "abc123"}
      "ticket_restart_abc123"       → {"action": "ticket_restart", "ticket_id": "abc123"}
    """
    # Exact matches first
    if reply_id == "tech_my_tickets":
        return {"action": "tech_my_tickets"}

    parts = reply_id.split("_", 3)  # at most 4 parts

    if len(parts) < 2:
        return {"action": "unknown"}

    prefix = parts[0]   # "ticket", "step", "menu", or "tech"
    action = parts[1]   # "select", "done", "issue", "close", "review", "switch", "open", etc.

    # ── ticket_* actions ─────────────────────────────────────────────────────
    if prefix == "ticket":
        if action == "select" and len(parts) >= 3:
            return {"action": "ticket_select", "ticket_id": parts[2]}

        if action == "start" and len(parts) >= 3:
            return {"action": "ticket_start", "ticket_id": parts[2]}

        if action == "close" and len(parts) >= 3:
            return {"action": "ticket_close", "ticket_id": parts[2]}

        if action == "review" and len(parts) >= 3:
            return {"action": "ticket_review", "ticket_id": parts[2]}

        if action == "restart" and len(parts) >= 3:
            return {"action": "ticket_restart", "ticket_id": parts[2]}

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

    # ── menu_* actions ────────────────────────────────────────────────────────
    elif prefix == "menu":
        if action == "open" and len(parts) >= 3:
            return {"action": "menu_open", "ticket_id": parts[2]}

    return {"action": "unknown"}


# ── Payload builders ─────────────────────────────────────────────────────────

def build_ticket_detail_card(ticket: dict) -> dict:
    """
    Build a ticket detail card with Begin Steps + My Tickets buttons.
    Shows the full description — no truncation.
    """
    ticket_id = str(ticket["_id"])
    title = ticket.get("title", "Untitled")
    machine_id = ticket.get("machine_id", "Unknown")
    description = ticket.get("description") or ""
    steps = ticket.get("steps", [])
    completed = sum(1 for s in steps if s.get("completed"))
    total = len(steps)
    priority = ticket.get("priority", 0)
    badge = _priority_badge(priority)

    body_parts = [f"*{title}*", f"Machine: {machine_id}  {badge}"]
    if description:
        body_parts.append(f"\n{description}")
    body_parts.append(f"\nProgress: {completed} of {total} steps complete")
    body = "\n".join(body_parts)[:1024]  # Meta body limit

    return {
        "type": "buttons",
        "body": body,
        "buttons": [
            {"id": f"ticket_start_{ticket_id}", "title": "Begin Steps"},
            {"id": "tech_my_tickets",           "title": "My Tickets"},
        ],
    }


def build_step_buttons(ticket: dict) -> dict | None:
    """
    Build an interactive button payload for the next incomplete step.
    Returns None if all steps are complete (caller should offer close-ticket buttons).

    Confirmation/manual steps: Done / Report Issue / Menu  (3 buttons)
    Note steps: plain text prompt only — tech types in the chat box
    Photo steps: plain text prompt only — tech sends a photo
    """
    ticket_id = str(ticket["_id"])
    total = len(ticket.get("steps", []))

    for step in ticket.get("steps", []):
        if step.get("completed", False):
            continue

        idx = step["step_index"]
        label = step["label"]
        ctype = step.get("completion_type", "confirmation")

        if ctype == "photo":
            return {
                "type": "text",
                "text": f"📷 Step {idx + 1} of {total}: {label}\n\nJust send a photo — no need to type anything.",
            }

        if ctype == "note":
            return {
                "type": "text",
                "text": f"Step {idx + 1} of {total}: {label}\n\nType your note below ↓",
            }

        if ctype in ("confirmation", "manual"):
            return {
                "type": "buttons",
                "body": f"Step {idx + 1} of {total}: {label}",
                "buttons": [
                    {"id": f"step_done_{ticket_id}_{idx}",  "title": "Done"},
                    {"id": f"step_issue_{ticket_id}_{idx}", "title": "Report Issue"},
                    {"id": f"menu_open_{ticket_id}",        "title": "Menu"},
                ],
            }

        # Unknown type — fallback to done/issue/menu
        return {
            "type": "buttons",
            "body": f"Step {idx + 1} of {total}: {label}",
            "buttons": [
                {"id": f"step_done_{ticket_id}_{idx}",  "title": "Done"},
                {"id": f"step_issue_{ticket_id}_{idx}", "title": "Report Issue"},
                {"id": f"menu_open_{ticket_id}",        "title": "Menu"},
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
            {"id": "tech_my_tickets",             "title": "My Tickets"},
        ],
    }


def build_menu_list(ticket_id: str) -> dict:
    """Build the in-step navigation menu list picker."""
    return {
        "type": "list",
        "body": "What would you like to do?",
        "button_label": "Options",
        "sections": [
            {
                "title": "NAVIGATION",
                "rows": [
                    {
                        "id": "tech_my_tickets",
                        "title": "My Other Tickets",
                        "description": "See all your assigned tickets",
                    },
                    {
                        "id": f"ticket_review_{ticket_id}",
                        "title": "View Progress",
                        "description": "See what's been completed so far",
                    },
                    {
                        "id": f"ticket_restart_{ticket_id}",
                        "title": "Back to Start",
                        "description": "Go back to the first step of this ticket",
                    },
                ],
            }
        ],
    }


def build_ticket_list(machine_id: str, tickets: list) -> dict:
    """
    Build an interactive list picker for a machine's open tickets.
    Title = priority badge (≤24 chars), description = full ticket title + status (≤72 chars).
    """
    rows = []
    for t in tickets[:10]:  # Meta max 10 rows per section
        tid = str(t["_id"])
        priority = t.get("priority", 0)
        badge = _priority_badge(priority)
        title_text = t.get("title", "Untitled")
        status = t.get("status", "open")
        rows.append({
            "id": f"ticket_select_{tid}",
            "title": badge[:24],
            "description": f"{title_text[:60]} · {status}",
        })

    return {
        "type": "list",
        "body": f"Open tickets for {machine_id} — tap to select one:",
        "button_label": "View Tickets",
        "sections": [{"title": machine_id[:24], "rows": rows}],
    }


def build_all_tickets_list(tickets: list) -> dict:
    """
    Build an interactive list picker for ALL tickets assigned to a tech,
    grouped by machine (one section per machine, max 10 rows total).
    """
    # Group by machine, preserving priority sort order
    from collections import defaultdict
    by_machine: dict[str, list] = defaultdict(list)
    for t in tickets:
        by_machine[t.get("machine_id", "Unassigned")].append(t)

    sections = []
    row_count = 0
    for machine_id, machine_tickets in by_machine.items():
        rows = []
        for t in machine_tickets:
            if row_count >= 10:
                break
            tid = str(t["_id"])
            priority = t.get("priority", 0)
            badge = _priority_badge(priority)
            title_text = t.get("title", "Untitled")
            status = t.get("status", "open")
            rows.append({
                "id": f"ticket_select_{tid}",
                "title": badge[:24],
                "description": f"{title_text[:50]} · {machine_id}",
            })
            row_count += 1
        if rows:
            sections.append({"title": machine_id[:24], "rows": rows})

    return {
        "type": "list",
        "body": "Your open tickets — tap one to open it:",
        "button_label": "My Tickets",
        "sections": sections,
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

    # ── tech_my_tickets: show all assigned tickets across machines ────────────
    if action == "tech_my_tickets":
        tickets = await ticket_service.get_open_tickets_for_phone(db, phone_number)
        # Clear active ticket so next selection starts fresh
        await db.users.update_one(
            {"phone_number": phone_number},
            {"$set": {"active_ticket_id": None}},
        )
        if not tickets:
            return {"action": "send_text", "text": "You have no open tickets right now. Great work! 🎉"}
        if len(tickets) == 1:
            # Only one ticket — show its detail card directly
            ticket = tickets[0]
            await db.users.update_one(
                {"phone_number": phone_number},
                {"$set": {"active_ticket_id": str(ticket["_id"]), "active_machine_id": ticket.get("machine_id")}},
            )
            payload = build_ticket_detail_card(ticket)
            return {"action": "send_buttons", "body": payload["body"], "buttons": payload["buttons"]}
        payload = build_all_tickets_list(tickets)
        return {
            "action": "send_list",
            "body": payload["body"],
            "button_label": payload["button_label"],
            "sections": payload["sections"],
        }

    # ── ticket_select: tech picked a ticket from any list ────────────────────
    if action == "ticket_select":
        ticket_id = parsed["ticket_id"]
        ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
        if ticket is None:
            return {"action": "send_text", "text": "Ticket not found. Please contact your supervisor."}
        await db.users.update_one(
            {"phone_number": phone_number},
            {"$set": {
                "active_ticket_id": ticket_id,
                "active_machine_id": ticket.get("machine_id"),
            }},
        )
        # Show detail card before starting
        payload = build_ticket_detail_card(ticket)
        return {"action": "send_buttons", "body": payload["body"], "buttons": payload["buttons"]}

    # ── ticket_start: tech tapped "Begin Steps" on detail card ───────────────
    if action == "ticket_start":
        ticket_id = parsed["ticket_id"]
        ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
        if ticket is None:
            return {"action": "send_text", "text": "Ticket not found. Please contact your supervisor."}
        machine_id = ticket.get("machine_id", "")
        await db.tickets.update_one(
            {"_id": ObjectId(ticket_id)},
            {"$set": {"status": "in_progress"}},
        )
        await db.users.update_one(
            {"phone_number": phone_number},
            {"$set": {"active_ticket_id": ticket_id, "active_machine_id": machine_id}},
        )
        # Reload and send first step directly — no Claude needed
        ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
        step_payload = build_step_buttons(ticket)
        if step_payload is None:
            payload = build_close_ticket_buttons(ticket)
        else:
            payload = step_payload
        if payload["type"] == "text":
            return {"action": "send_text", "text": payload["text"]}
        return {"action": "send_buttons", "body": payload["body"], "buttons": payload["buttons"]}

    # ── ticket_restart: re-present the first step buttons ────────────────────
    elif action == "ticket_restart":
        ticket_id = parsed["ticket_id"]
        ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
        if ticket is None:
            return {"action": "send_text", "text": "Ticket not found."}
        # Reset to first step in display only — find step 0 regardless of completed state
        steps = ticket.get("steps", [])
        if not steps:
            return {"action": "send_text", "text": "This ticket has no steps."}
        first = steps[0]
        idx = first["step_index"]
        label = first["label"]
        ctype = first.get("completion_type", "confirmation")
        total = len(steps)
        completed = sum(1 for s in steps if s.get("completed"))
        ticket_id_str = str(ticket["_id"])
        header = f"Back to step 1 ({completed}/{total} steps already done).\n\n"
        if ctype == "photo":
            return {"action": "send_text", "text": f"{header}📷 Step 1 of {total}: {label}\n\nJust send a photo."}
        if ctype == "note":
            return {"action": "send_text", "text": f"{header}Step 1 of {total}: {label}\n\nType your note below ↓"}
        return {
            "action": "send_buttons",
            "body": f"{header}Step 1 of {total}: {label}",
            "buttons": [
                {"id": f"step_done_{ticket_id_str}_{idx}",  "title": "Done"},
                {"id": f"step_issue_{ticket_id_str}_{idx}", "title": "Report Issue"},
                {"id": f"menu_open_{ticket_id_str}",        "title": "Menu"},
            ],
        }

    # ── menu_open: show navigation menu list ─────────────────────────────────
    elif action == "menu_open":
        ticket_id = parsed["ticket_id"]
        payload = build_menu_list(ticket_id)
        return {
            "action": "send_list",
            "body": payload["body"],
            "button_label": payload["button_label"],
            "sections": payload["sections"],
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
            payload = build_close_ticket_buttons(ticket)
        else:
            payload = next_payload

        step_count = sum(1 for s in ticket.get("steps", []) if s.get("completed"))
        total = len(ticket.get("steps", []))

        if payload["type"] == "text":
            return {"action": "send_text", "text": f"✅ Step {step_index + 1} done ({step_count}/{total}).\n\n{payload['text']}"}

        return {
            "action": "send_buttons",
            "body": f"✅ Step {step_index + 1} done ({step_count}/{total} complete).\n\n{payload['body']}",
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
                    ticket = remaining[0]
                    await db.users.update_one(
                        {"phone_number": phone_number},
                        {"$set": {"active_ticket_id": str(ticket["_id"])}},
                    )
                    payload = build_ticket_detail_card(ticket)
                    return {
                        "action": "send_buttons",
                        "body": f"Ticket closed. 1 ticket still open on {machine_id}:\n\n{payload['body']}",
                        "buttons": payload["buttons"],
                    }
                else:
                    list_payload = build_ticket_list(machine_id, remaining)
                    return {
                        "action": "send_list",
                        "body": f"Ticket closed. {len(remaining)} tickets still open on {machine_id}:",
                        "button_label": list_payload["button_label"],
                        "sections": list_payload["sections"],
                    }

        # No remaining tickets for this machine — check all assigned tickets
        all_remaining = await ticket_service.get_open_tickets_for_phone(db, phone_number)
        if all_remaining:
            payload = build_all_tickets_list(all_remaining)
            return {
                "action": "send_list",
                "body": f"Ticket closed. You still have {len(all_remaining)} open ticket(s):",
                "button_label": payload["button_label"],
                "sections": payload["sections"],
            }

        return {"action": "send_text", "text": "Ticket closed. No more open tickets. Great work! 🎉"}

    # ── ticket_review: show all steps — route to Claude ──────────────────────
    elif action == "ticket_review":
        ticket_id = parsed["ticket_id"]
        return {
            "action": "route_to_claude",
            "message_text": "Show me a summary of all steps on this ticket.",
            "ticket_id": ticket_id,
        }

    # ── ticket_switch: tech wants to change ticket (legacy) ──────────────────
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
            ticket = tickets[0]
            await db.users.update_one(
                {"phone_number": phone_number},
                {"$set": {"active_ticket_id": str(ticket["_id"])}},
            )
            payload = build_ticket_detail_card(ticket)
            return {"action": "send_buttons", "body": payload["body"], "buttons": payload["buttons"]}
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
