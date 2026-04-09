from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from .user import PyObjectId


class DailyCheckItem(BaseModel):
    item_index: int
    label: str
    section_name: str
    completion_type: Literal["confirmation", "note", "photo", "manual"] = "confirmation"


class DailyChecklistTemplate(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    machine_id: str
    title: str
    items: List[DailyCheckItem] = []
    assigned_to: str                  # primary technician phone number
    schedule_time: str = "00:00"      # "HH:MM" in 24-hour format
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None  # admin username

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class DailyChecklistCreate(BaseModel):
    machine_id: str
    title: str
    items: List[DailyCheckItem] = []
    assigned_to: str
    schedule_time: str = "00:00"
    active: bool = True


class DailyChecklistUpdate(BaseModel):
    title: Optional[str] = None
    items: Optional[List[DailyCheckItem]] = None
    assigned_to: Optional[str] = None
    schedule_time: Optional[str] = None
    active: Optional[bool] = None
