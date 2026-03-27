from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from .user import PyObjectId

TicketCategory = Literal["repair", "installation", "maintenance", "emergency", "inspection"]


class TicketStep(BaseModel):
    step_index: int
    label: str
    completion_type: Literal["confirmation", "note", "photo", "manual"]
    completed: bool = False
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None  # phone number or "admin"
    note_text: Optional[str] = None
    photo_path: Optional[str] = None


class TicketBase(BaseModel):
    machine_id: str
    title: str
    description: Optional[str] = None
    steps: List[TicketStep] = []
    assigned_to: Optional[str] = None  # primary technician phone number
    secondary_assigned_to: Optional[str] = None  # secondary technician phone number
    priority: int = Field(default=0, description="Higher = more urgent")
    due_date: Optional[datetime] = None
    category: Optional[TicketCategory] = None


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[TicketStep]] = None
    assigned_to: Optional[str] = None
    secondary_assigned_to: Optional[str] = None
    priority: Optional[int] = None
    due_date: Optional[datetime] = None
    category: Optional[TicketCategory] = None
    status: Optional[Literal["open", "in_progress", "closed"]] = None


class TicketInDB(TicketBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    status: Literal["open", "in_progress", "closed"] = "open"
    created_by: Optional[str] = None  # admin username
    created_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    closed_by: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
