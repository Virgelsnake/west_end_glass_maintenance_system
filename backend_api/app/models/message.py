from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from .user import PyObjectId


class MessageInDB(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    ticket_id: str
    direction: Literal["inbound", "outbound"]
    phone_number: str
    content: str
    media_type: Optional[str] = None   # "image", "text", etc.
    media_path: Optional[str] = None   # local path if downloaded
    ai_generated: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
