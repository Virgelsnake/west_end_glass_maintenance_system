"""
daily_scheduler.py — APScheduler-backed service for auto-creating daily checklist tickets.

Lifecycle:
  init_scheduler(db) — called once at FastAPI startup
  schedule_daily(template_doc) — add/replace cron job for a template
  unschedule_daily(template_id: str) — remove job
  shutdown() — called at FastAPI shutdown
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler = None
_db = None  # reference to motor DB kept for job callbacks


def _get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


async def init_scheduler(db) -> None:
    """Start the scheduler and register cron jobs for all active templates."""
    global _db
    _db = db

    scheduler = _get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started")

    templates = await db.daily_checklist_templates.find({"active": True}).to_list(length=None)
    for t in templates:
        await schedule_daily(t)
    logger.info("Scheduled %d daily checklist job(s)", len(templates))


async def schedule_daily(template: dict) -> None:
    """Add or replace the cron job for a template."""
    scheduler = _get_scheduler()
    template_id = str(template["_id"])
    schedule_time = template.get("schedule_time", "00:00")

    try:
        hour_str, minute_str = schedule_time.split(":")
        hour = int(hour_str)
        minute = int(minute_str)
    except (ValueError, AttributeError):
        logger.warning("Invalid schedule_time '%s' for template %s — defaulting to 00:00", schedule_time, template_id)
        hour, minute = 0, 0

    trigger = CronTrigger(hour=hour, minute=minute, timezone="UTC")

    scheduler.add_job(
        _fire_daily_job,
        trigger=trigger,
        id=template_id,
        args=[template_id],
        replace_existing=True,
        misfire_grace_time=3600,  # allow up to 1h late if server was down
    )
    logger.info("Scheduled daily job for template %s at %02d:%02d UTC", template_id, hour, minute)


async def unschedule_daily(template_id: str) -> None:
    """Remove the cron job for a template if it exists."""
    scheduler = _get_scheduler()
    try:
        scheduler.remove_job(template_id)
        logger.info("Unscheduled daily job for template %s", template_id)
    except Exception:
        pass  # job may not have existed


def shutdown() -> None:
    """Gracefully stop the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")


async def _fire_daily_job(template_id: str) -> None:
    """Cron job callback — fetch template from DB and create today's ticket."""
    from bson import ObjectId

    if _db is None:
        logger.error("DB reference not set — cannot fire daily job for template %s", template_id)
        return

    try:
        if not ObjectId.is_valid(template_id):
            return
        template = await _db.daily_checklist_templates.find_one({"_id": ObjectId(template_id)})
        if not template:
            logger.warning("Template %s not found — skipping daily fire", template_id)
            return
        if not template.get("active", True):
            logger.info("Template %s is inactive — skipping daily fire", template_id)
            return

        from ..routers.dailys import _create_daily_ticket
        ticket_id = await _create_daily_ticket(_db, template)
        logger.info("Auto-created daily ticket %s from template %s", ticket_id, template_id)

    except Exception as exc:
        logger.error("Error firing daily job for template %s: %s", template_id, exc, exc_info=True)
