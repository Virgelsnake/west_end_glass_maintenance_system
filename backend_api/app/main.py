from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import connect_db, close_db
from .auth import hash_password
from .routers import (
    admin_auth,
    webhook,
    tickets,
    users,
    machines,
    messages,
    audit,
    photos,
)

app = FastAPI(
    title="West End Glass Maintenance System API",
    version="1.0.0",
    description="WhatsApp-based field-service ticketing backend",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await connect_db()
    await _seed_admin()


@app.on_event("shutdown")
async def shutdown():
    await close_db()


async def _seed_admin():
    """Create default admin account if none exists."""
    from .database import get_db
    db = get_db()
    existing = await db.admins.find_one({"username": settings.admin_username})
    if not existing:
        await db.admins.insert_one({
            "username": settings.admin_username,
            "password_hash": hash_password(settings.admin_password),
        })


app.include_router(admin_auth.router)
app.include_router(webhook.router)
app.include_router(tickets.router)
app.include_router(users.router)
app.include_router(machines.router)
app.include_router(messages.router)
app.include_router(audit.router)
app.include_router(photos.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
