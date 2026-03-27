from fastapi import APIRouter, Depends, HTTPException, status
from ..auth import verify_password, hash_password, create_access_token, get_current_admin
from ..database import get_db
from pydantic import BaseModel

router = APIRouter(tags=["tech-auth"])


class TechLoginRequest(BaseModel):
    phone_number: str
    pin: str


class SetPinRequest(BaseModel):
    pin: str


@router.post("/auth/technician/login")
async def technician_login(body: TechLoginRequest):
    """Technician logs in with phone number + PIN. Returns a JWT with actor_type=technician."""
    if len(body.pin) < 4:
        raise HTTPException(status_code=400, detail="PIN must be at least 4 digits")

    db = get_db()
    user = await db.users.find_one({"phone_number": body.phone_number, "active": True})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phone number not recognized or inactive",
        )
    pin_hash = user.get("pin_hash")
    if not pin_hash or not verify_password(body.pin, pin_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid PIN",
        )
    token = create_access_token({
        "sub": body.phone_number,
        "actor_type": "technician",
        "name": user.get("name", ""),
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "name": user.get("name", ""),
        "phone_number": body.phone_number,
    }


@router.post("/users/{phone_number}/set-pin")
async def set_technician_pin(
    phone_number: str,
    body: SetPinRequest,
    current_admin: dict = Depends(get_current_admin),
):
    """Admin sets a PIN for a technician to enable portal login."""
    if len(body.pin) < 4:
        raise HTTPException(status_code=400, detail="PIN must be at least 4 digits")

    db = get_db()
    result = await db.users.update_one(
        {"phone_number": phone_number},
        {"$set": {"pin_hash": hash_password(body.pin)}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"updated": True}
