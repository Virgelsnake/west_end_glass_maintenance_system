from pydantic import BaseModel, Field
from typing import Optional, Any, Literal
from datetime import datetime
from .user import PyObjectId


AuditEventType = Literal[
    "ticket_created",
    "ticket_updated",
    "ticket_closed",
    "ticket_reopened",
    "message_received",
    "message_sent",
    "note_added",
    "photo_attached",
    "step_completed",
    "user_added",
    "user_deactivated",
    "auth_failure",
    "daily_template_created",
    "daily_template_updated",
    "daily_template_deleted",
    "daily_ticket_created",
]

ActorType = Literal["technician", "admin", "system"]


class AuditLogEntry(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    event: AuditEventType
    ticket_id: Optional[str] = None
    machine_id: Optional[str] = None
    actor: Optional[str] = None          # phone number or admin username
    actor_type: ActorType = "system"
    payload: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
