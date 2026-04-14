from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict
from datetime import datetime
from .user import PyObjectId


class PhotoMetadata(BaseModel):
    datetime_taken: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

TicketCategory = Literal["repair", "installation", "maintenance", "emergency", "inspection"]


class TicketStep(BaseModel):
    step_index: int
    label: str
    completion_type: Literal["confirmation", "note", "photo", "manual", "attachment"]
    completed: bool = False
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None  # phone number or "admin"
    note_text: Optional[str] = None
    photo_path: Optional[str] = None
    manual_id: Optional[str] = None           # links to manuals collection
    manual_title: Optional[str] = None        # stored for display without extra lookup
    send_manual_via_whatsapp: bool = False     # Code Path B: proactively push doc via WA
    manual_doc_sent: bool = False              # prevents duplicate WA doc sends
    photo_metadata: Optional[PhotoMetadata] = None


class TicketBase(BaseModel):
    machine_id: Optional[str] = None          # None for non-machine ticket types
    ticket_type_id: Optional[str] = None      # links to ticket_types collection
    title: str
    description: Optional[str] = None
    steps: List[TicketStep] = []
    assigned_to: Optional[str] = None  # primary technician phone number
    secondary_assigned_to: Optional[str] = None  # secondary technician phone number
    priority: int = Field(default=0, description="Higher = more urgent")
    due_date: Optional[datetime] = None
    category: Optional[TicketCategory] = None
    reference_photos: List[str] = []  # filenames of admin-attached reference images
    reference_photo_metadata: Dict[str, PhotoMetadata] = {}  # keyed by filename
    location: Optional[str] = None            # for non-machine ticket types
    contact_name: Optional[str] = None
    contact_number: Optional[str] = None
    contact_address: Optional[str] = None


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
    location: Optional[str] = None
    contact_name: Optional[str] = None
    contact_number: Optional[str] = None
    contact_address: Optional[str] = None


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
