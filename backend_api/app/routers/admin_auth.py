from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime
from ..auth import verify_password, create_access_token, hash_password, get_current_admin
from ..config import settings
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Admin login — returns JWT access token with role claim."""
    db = get_db()
    admin = await db.admins.find_one({"username": form_data.username, "active": True})

    if not admin or not verify_password(form_data.password, admin["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last_login
    await db.admins.update_one(
        {"username": form_data.username},
        {"$set": {"last_login": datetime.utcnow()}}
    )

    role = admin.get("role", "viewer")
    token = create_access_token({
        "sub": form_data.username,
        "role": role,
        "actor_type": "admin",
    })
    return {"access_token": token, "token_type": "bearer", "role": role, "full_name": admin.get("full_name", form_data.username)}


@router.get("/me")
async def get_me(current_admin: dict = Depends(get_current_admin)):
    return {"username": current_admin["username"], "role": current_admin["role"]}
