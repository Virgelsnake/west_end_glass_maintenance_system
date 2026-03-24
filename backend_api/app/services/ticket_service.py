from datetime import datetime
from typing import Optional
from bson import ObjectId
from .audit_service import log_event


async def get_open_tickets_for_machine(db, machine_id: str) -> list:
    """Return open/in_progress tickets for a machine, sorted by priority desc then created_at asc."""
    cursor = db.tickets.find(
        {"machine_id": machine_id, "status": {"$in": ["open", "in_progress"]}}
    ).sort([("priority", -1), ("created_at", 1)])
    return await cursor.to_list(length=None)


async def get_open_tickets_for_phone(db, phone_number: str) -> list:
    """Return all open tickets assigned to a technician's phone number."""
    cursor = db.tickets.find(
        {"assigned_to": phone_number, "status": {"$in": ["open", "in_progress"]}}
    ).sort([("priority", -1), ("created_at", 1)])
    return await cursor.to_list(length=None)


async def get_current_step(ticket: dict) -> Optional[dict]:
    """Return the first incomplete step, or None if all done."""
    for step in ticket.get("steps", []):
        if not step.get("completed", False):
            return step
    return None


async def check_off_step(db, ticket_id: str, step_index: int, actor: str) -> dict:
    """Mark a step as complete and return updated ticket."""
    now = datetime.utcnow()
    await db.tickets.update_one(
        {"_id": ObjectId(ticket_id), "steps.step_index": step_index},
        {
            "$set": {
                "steps.$.completed": True,
                "steps.$.completed_at": now,
                "steps.$.completed_by": actor,
                "status": "in_progress",
            }
        },
    )
    await log_event(
        db,
        event="step_completed",
        actor=actor,
        actor_type="technician",
        ticket_id=ticket_id,
        payload={"step_index": step_index},
    )
    return await db.tickets.find_one({"_id": ObjectId(ticket_id)})


async def attach_note_to_step(db, ticket_id: str, step_index: int, note_text: str, actor: str) -> dict:
    """Save a note to a step and check it off."""
    now = datetime.utcnow()
    await db.tickets.update_one(
        {"_id": ObjectId(ticket_id), "steps.step_index": step_index},
        {
            "$set": {
                "steps.$.completed": True,
                "steps.$.completed_at": now,
                "steps.$.completed_by": actor,
                "steps.$.note_text": note_text,
                "status": "in_progress",
            }
        },
    )
    await log_event(
        db,
        event="note_added",
        actor=actor,
        actor_type="technician",
        ticket_id=ticket_id,
        payload={"step_index": step_index, "note": note_text},
    )
    return await db.tickets.find_one({"_id": ObjectId(ticket_id)})


async def attach_photo_to_step(db, ticket_id: str, step_index: int, photo_path: str, actor: str) -> dict:
    """Attach a downloaded photo path to a step and check it off."""
    now = datetime.utcnow()
    await db.tickets.update_one(
        {"_id": ObjectId(ticket_id), "steps.step_index": step_index},
        {
            "$set": {
                "steps.$.completed": True,
                "steps.$.completed_at": now,
                "steps.$.completed_by": actor,
                "steps.$.photo_path": photo_path,
                "status": "in_progress",
            }
        },
    )
    await log_event(
        db,
        event="photo_attached",
        actor=actor,
        actor_type="technician",
        ticket_id=ticket_id,
        payload={"step_index": step_index, "photo_path": photo_path},
    )
    return await db.tickets.find_one({"_id": ObjectId(ticket_id)})


async def all_steps_complete(ticket: dict) -> bool:
    return all(step.get("completed", False) for step in ticket.get("steps", []))


async def close_ticket(db, ticket_id: str, closed_by: str) -> dict:
    """Mark ticket as closed."""
    now = datetime.utcnow()
    await db.tickets.update_one(
        {"_id": ObjectId(ticket_id)},
        {"$set": {"status": "closed", "closed_at": now, "closed_by": closed_by}},
    )
    ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    await log_event(
        db,
        event="ticket_closed",
        actor=closed_by,
        actor_type="technician",
        ticket_id=ticket_id,
        machine_id=ticket.get("machine_id"),
        payload={"closed_by": closed_by},
    )
    return ticket
