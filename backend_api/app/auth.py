from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings
from .database import get_db

pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")

# Two separate OAuth2 schemes — admin and technician
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_tech_scheme = OAuth2PasswordBearer(tokenUrl="/auth/technician/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _decode_token(token: str) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        sub: str = payload.get("sub")
        if sub is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


async def get_current_admin(token: str = Depends(oauth2_scheme)) -> dict:
    """Returns dict with {username, role} for any valid admin JWT."""
    payload = _decode_token(token)
    actor_type = payload.get("actor_type", "admin")
    if actor_type != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return {"username": payload["sub"], "role": payload.get("role", "viewer")}


def require_role(*roles: str):
    """Dependency factory that restricts access to specific admin roles."""
    async def _check(current_admin: dict = Depends(get_current_admin)) -> dict:
        if current_admin["role"] not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {', '.join(roles)}",
            )
        return current_admin
    return _check


async def get_current_technician(token: str = Depends(oauth2_tech_scheme)) -> dict:
    """Returns dict with {phone_number, name} for a valid technician JWT."""
    payload = _decode_token(token)
    actor_type = payload.get("actor_type", "")
    if actor_type != "technician":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Technician access required"
        )
    return {"phone_number": payload["sub"], "name": payload.get("name", "")}


async def is_phone_authorized(phone_number: str, db) -> bool:
    """Check if a phone number is in the active user whitelist."""
    user = await db.users.find_one({"phone_number": phone_number, "active": True})
    return user is not None


async def get_authorized_user(phone_number: str, db):
    """Return user document if authorized, or None."""
    return await db.users.find_one({"phone_number": phone_number, "active": True})
