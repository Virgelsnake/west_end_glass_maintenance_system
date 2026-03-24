from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId


class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)


class UserBase(BaseModel):
    phone_number: str = Field(..., description="E.164 format, e.g. +15551234567")
    name: str
    language: str = Field(default="en", description="BCP-47 language code, e.g. 'en', 'es'")
    active: bool = True


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    language: Optional[str] = None
    active: Optional[bool] = None


class UserInDB(UserBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: Optional[datetime] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
