from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from ..auth import hash_password, require_role, get_current_admin
from ..database import get_db
from ..models.admin import AdminCreate, AdminUpdate

router = APIRouter(prefix="/admins", tags=["admins"])

_super_only = require_role("super_admin")


def _serialize(doc) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    doc.pop("password_hash", None)
    return doc


@router.get("")
async def list_admins(current_admin: dict = Depends(get_current_admin)):
    db = get_db()
    admins = await db.admins.find().to_list(length=None)
    return [_serialize(a) for a in admins]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_admin(
    body: AdminCreate,
    current_admin: dict = Depends(_super_only),
):
    db = get_db()
    existing = await db.admins.find_one({"username": body.username})
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    doc = {
        "username": body.username,
        "full_name": body.full_name,
        "role": body.role,
        "active": body.active,
        "password_hash": hash_password(body.password),
        "created_at": datetime.utcnow(),
        "last_login": None,
    }
    result = await db.admins.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    doc.pop("password_hash", None)
    return doc


@router.patch("/{username}")
async def update_admin(
    username: str,
    update: AdminUpdate,
    current_admin: dict = Depends(_super_only),
):
    db = get_db()
    changes = {k: v for k, v in update.model_dump().items() if v is not None}
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.admins.update_one({"username": username}, {"$set": changes})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Admin not found")
    return {"updated": True}


@router.post("/{username}/set-password")
async def set_admin_password(
    username: str,
    body: dict,
    current_admin: dict = Depends(_super_only),
):
    new_password = body.get("password", "").strip()
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    db = get_db()
    result = await db.admins.update_one(
        {"username": username},
        {"$set": {"password_hash": hash_password(new_password)}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Admin not found")
    return {"updated": True}


@router.delete("/{username}")
async def deactivate_admin(
    username: str,
    current_admin: dict = Depends(_super_only),
):
    if username == current_admin["username"]:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    db = get_db()
    result = await db.admins.update_one({"username": username}, {"$set": {"active": False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Admin not found")
    return {"deactivated": True}
