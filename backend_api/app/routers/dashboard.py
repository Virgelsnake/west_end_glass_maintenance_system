from fastapi import APIRouter, Depends
from datetime import datetime
from ..auth import get_current_admin
from ..database import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _serialize(doc) -> dict:
    if not doc:
        return doc
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    # Convert datetime fields to ISO strings
    if "timestamp" in doc and isinstance(doc["timestamp"], datetime):
        doc["timestamp"] = doc["timestamp"].isoformat()
    return doc


@router.get("/stats")
async def get_dashboard_stats(current_admin: dict = Depends(get_current_admin)):
    """
    Returns all KPIs needed for the dashboard in a single request:
    - ticket counts by status
    - overdue count (due_date in the past and not closed)
    - technician workload (open + in_progress counts per tech)
    - last 10 audit events for the activity feed
    """
    db = get_db()
    now = datetime.utcnow()

    # Counts by status
    all_tickets = await db.tickets.find().to_list(length=None)
    by_status = {"open": 0, "in_progress": 0, "closed": 0}
    overdue = 0
    for t in all_tickets:
        s = t.get("status", "open")
        if s in by_status:
            by_status[s] += 1
        if s != "closed" and t.get("due_date") and t["due_date"] < now:
            overdue += 1

    # Technician workload
    tech_map: dict[str, dict] = {}
    for t in all_tickets:
        if t.get("status") == "closed":
            continue
        for phone_field in ("assigned_to", "secondary_assigned_to"):
            phone = t.get(phone_field)
            if not phone:
                continue
            if phone not in tech_map:
                tech_map[phone] = {"phone": phone, "name": phone, "open": 0, "in_progress": 0}
            if t["status"] == "open":
                tech_map[phone]["open"] += 1
            elif t["status"] == "in_progress":
                tech_map[phone]["in_progress"] += 1

    # Resolve names for techs
    if tech_map:
        phone_list = list(tech_map.keys())
        users = await db.users.find({"phone_number": {"$in": phone_list}}).to_list(length=None)
        for u in users:
            if u["phone_number"] in tech_map:
                tech_map[u["phone_number"]]["name"] = u.get("name", u["phone_number"])

    # Recent activity (last 10 audit events)
    recent_activity = await db.audit_logs.find().sort("timestamp", -1).limit(10).to_list(length=None)

    return {
        "by_status": by_status,
        "overdue_count": overdue,
        "tech_workload": list(tech_map.values()),
        "recent_activity": [_serialize(a) for a in recent_activity],
    }
