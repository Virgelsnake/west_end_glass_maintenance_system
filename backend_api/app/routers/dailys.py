from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from typing import Optional
from datetime import date
import logging

from ..auth import get_current_admin
from ..database import get_db
from ..models.daily import DailyChecklistCreate, DailyChecklistUpdate
from ..models.ticket import TicketStep
from ..services.audit_service import log_event
from ..services import whatsapp as wa_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dailys", tags=["dailys"])


def _serialize(doc) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@router.get("")
async def list_daily_templates(current_admin: dict = Depends(get_current_admin)):
    db = get_db()
    templates = await db.daily_checklist_templates.find({}).sort("created_at", -1).to_list(length=None)
    result = []
    for t in templates:
        t = _serialize(t)
        # Enrich with machine name
        machine = await db.machines.find_one({"machine_id": t["machine_id"]})
        t["machine_name"] = machine["name"] if machine else t["machine_id"]
        # Enrich with assignee name
        user = await db.users.find_one({"phone_number": t["assigned_to"]})
        t["assignee_name"] = user["name"] if user else t["assigned_to"]
        result.append(t)
    return result


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_daily_template(
    template: DailyChecklistCreate,
    current_admin: dict = Depends(get_current_admin),
):
    from datetime import datetime
    db = get_db()
    doc = template.model_dump()
    doc["created_at"] = datetime.utcnow()
    doc["created_by"] = current_admin["username"]
    result = await db.daily_checklist_templates.insert_one(doc)
    template_id = str(result.inserted_id)

    await log_event(db, "daily_template_created", actor=current_admin["username"],
                    actor_type="admin", machine_id=template.machine_id,
                    payload={"template_id": template_id, "title": template.title})

    # Schedule the daily job
    try:
        from ..services.daily_scheduler import schedule_daily
        created = await db.daily_checklist_templates.find_one({"_id": ObjectId(template_id)})
        await schedule_daily(created)
    except Exception as exc:
        logger.warning("Failed to schedule daily job after creation: %s", exc)

    return {**doc, "_id": template_id}


@router.get("/{template_id}")
async def get_daily_template(template_id: str, current_admin: dict = Depends(get_current_admin)):
    db = get_db()
    if not ObjectId.is_valid(template_id):
        raise HTTPException(status_code=400, detail="Invalid template ID")
    template = await db.daily_checklist_templates.find_one({"_id": ObjectId(template_id)})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    t = _serialize(template)
    machine = await db.machines.find_one({"machine_id": t["machine_id"]})
    t["machine_name"] = machine["name"] if machine else t["machine_id"]
    user = await db.users.find_one({"phone_number": t["assigned_to"]})
    t["assignee_name"] = user["name"] if user else t["assigned_to"]
    return t


@router.patch("/{template_id}")
async def update_daily_template(
    template_id: str,
    update: DailyChecklistUpdate,
    current_admin: dict = Depends(get_current_admin),
):
    db = get_db()
    if not ObjectId.is_valid(template_id):
        raise HTTPException(status_code=400, detail="Invalid template ID")
    existing = await db.daily_checklist_templates.find_one({"_id": ObjectId(template_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")

    changes = {k: v for k, v in update.model_dump().items() if v is not None}
    if not changes:
        return _serialize(existing)

    # items is a list so can't use "is not None" — handle separately
    if update.items is not None:
        changes["items"] = [item.model_dump() for item in update.items]

    await db.daily_checklist_templates.update_one(
        {"_id": ObjectId(template_id)},
        {"$set": changes},
    )

    await log_event(db, "daily_template_updated", actor=current_admin["username"],
                    actor_type="admin", machine_id=existing["machine_id"],
                    payload={"template_id": template_id, "changes": list(changes.keys())})

    updated = await db.daily_checklist_templates.find_one({"_id": ObjectId(template_id)})

    # Reschedule / unschedule based on active flag and schedule_time changes
    try:
        from ..services.daily_scheduler import schedule_daily, unschedule_daily
        if updated.get("active", True):
            await schedule_daily(updated)
        else:
            await unschedule_daily(template_id)
    except Exception as exc:
        logger.warning("Failed to reschedule after update: %s", exc)

    return _serialize(updated)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_daily_template(template_id: str, current_admin: dict = Depends(get_current_admin)):
    db = get_db()
    if not ObjectId.is_valid(template_id):
        raise HTTPException(status_code=400, detail="Invalid template ID")
    existing = await db.daily_checklist_templates.find_one({"_id": ObjectId(template_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.daily_checklist_templates.delete_one({"_id": ObjectId(template_id)})

    await log_event(db, "daily_template_deleted", actor=current_admin["username"],
                    actor_type="admin", machine_id=existing.get("machine_id"),
                    payload={"template_id": template_id, "title": existing.get("title")})

    try:
        from ..services.daily_scheduler import unschedule_daily
        await unschedule_daily(template_id)
    except Exception as exc:
        logger.warning("Failed to unschedule after deletion: %s", exc)


@router.post("/{template_id}/trigger", status_code=status.HTTP_201_CREATED)
async def trigger_daily_template(template_id: str, current_admin: dict = Depends(get_current_admin)):
    """Immediately fire a daily checklist — creates today's ticket right now."""
    db = get_db()
    if not ObjectId.is_valid(template_id):
        raise HTTPException(status_code=400, detail="Invalid template ID")
    template = await db.daily_checklist_templates.find_one({"_id": ObjectId(template_id)})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    ticket_id = await _create_daily_ticket(db, template)
    return {"ticket_id": ticket_id, "message": "Daily ticket created"}


async def _create_daily_ticket(db, template: dict) -> str:
    """Create a maintenance ticket from a daily checklist template."""
    from datetime import datetime

    machine = await db.machines.find_one({"machine_id": template["machine_id"]})
    machine_name = machine["name"] if machine else template["machine_id"]

    today_str = date.today().strftime("%d/%m/%Y")
    title = f"Daily Check — {machine_name} — {today_str}"

    steps = [
        TicketStep(
            step_index=item["item_index"],
            label=item["label"],
            completion_type=item.get("completion_type", "confirmation"),
        ).model_dump()
        for item in template.get("items", [])
    ]

    doc = {
        "machine_id": template["machine_id"],
        "title": title,
        "description": f"Automated daily checklist for {machine_name}.",
        "status": "open",
        "steps": steps,
        "assigned_to": template["assigned_to"],
        "secondary_assigned_to": None,
        "priority": 0,
        "due_date": None,
        "category": "inspection",
        "reference_photos": [],
        "created_by": "system",
        "created_at": datetime.utcnow(),
        "closed_at": None,
        "closed_by": None,
    }

    result = await db.tickets.insert_one(doc)
    ticket_id = str(result.inserted_id)

    await log_event(db, "daily_ticket_created", actor="system", actor_type="system",
                    ticket_id=ticket_id, machine_id=template["machine_id"],
                    payload={"template_id": str(template["_id"]), "title": title})

    # WhatsApp assignment notification
    try:
        tech = await db.users.find_one({"phone_number": template["assigned_to"]})
        tech_name = tech["name"] if tech else template["assigned_to"]
        await wa_service.send_ticket_assignment_notification(
            to=template["assigned_to"],
            tech_name=tech_name,
            ticket_title=title,
            machine_id=template["machine_id"],
        )
    except Exception as exc:
        logger.warning("WhatsApp notification failed for daily ticket: %s", exc)

    return ticket_id
