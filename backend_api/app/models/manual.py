from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .user import PyObjectId


class ManualInDB(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    title: str
    original_filename: str
    stored_filename: str
    file_type: str  # e.g. "pdf", "docx", "jpg", "png", "webp"
    file_size: int  # bytes
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    uploaded_by: str  # admin username

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
