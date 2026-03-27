from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from typing import Optional
from ..auth import get_current_admin, hash_password
from ..database import get_db
from ..models.user import UserCreate, UserUpdate
from ..services.audit_service import log_event
from datetime import datetime

router = APIRouter(prefix="/users", tags=["users"])


def _serialize(doc) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@router.get("")
async def list_users(
    active: Optional[bool] = None,
    current_admin: dict = Depends(get_current_admin)
):
    db = get_db()
    query = {}
    if active is not None:
        query["active"] = active
    users = await db.users.find(query).to_list(length=None)
    return [_serialize(u) for u in users]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, current_admin: dict = Depends(get_current_admin)):
    db = get_db()
    existing = await db.users.find_one({"phone_number": user.phone_number})
    if existing:
        raise HTTPException(status_code=409, detail="Phone number already registered")
    doc = user.model_dump()
    doc["created_at"] = datetime.utcnow()
    result = await db.users.insert_one(doc)
    await log_event(db, "user_added", actor=current_admin["username"], actor_type="admin",
                    payload={"phone_number": user.phone_number, "name": user.name})
    return {**doc, "_id": str(result.inserted_id)}


@router.patch("/{phone_number}")
async def update_user(
    phone_number: str,
    update: UserUpdate,
    current_admin: dict = Depends(get_current_admin)
):
    db = get_db()
    changes = {k: v for k, v in update.model_dump().items() if v is not None}
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.users.update_one({"phone_number": phone_number}, {"$set": changes})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"updated": True}


@router.delete("/{phone_number}")
async def deactivate_user(phone_number: str, current_admin: dict = Depends(get_current_admin)):
    db = get_db()
    result = await db.users.update_one(
        {"phone_number": phone_number},
        {"$set": {"active": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    await log_event(db, "user_deactivated", actor=current_admin["username"], actor_type="admin",
                    payload={"phone_number": phone_number})
    return {"deactivated": True}
