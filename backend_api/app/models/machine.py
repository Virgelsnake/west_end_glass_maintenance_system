from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .user import PyObjectId


class MachineBase(BaseModel):
    machine_id: str = Field(..., description="Unique machine identifier, e.g. WEG-MACHINE-0042")
    name: str
    location: Optional[str] = None
    notes: Optional[str] = None


class MachineCreate(MachineBase):
    pass


class MachineUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class MachineInDB(MachineBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
