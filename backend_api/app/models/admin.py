from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from .user import PyObjectId


class AdminBase(BaseModel):
    username: str
    full_name: str
    role: Literal["super_admin", "dispatcher", "viewer"] = "viewer"
    active: bool = True


class AdminCreate(AdminBase):
    password: str


class AdminUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[Literal["super_admin", "dispatcher", "viewer"]] = None
    active: Optional[bool] = None


class AdminInDB(AdminBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
