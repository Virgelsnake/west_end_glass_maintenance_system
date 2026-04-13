from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .user import PyObjectId


class TicketTypeBase(BaseModel):
    name: str
    description: Optional[str] = None


class TicketTypeCreate(TicketTypeBase):
    pass


class TicketTypeInDB(TicketTypeBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
