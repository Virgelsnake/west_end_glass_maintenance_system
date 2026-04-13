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
    simulate,
)
from .routers import admins, tech_auth, tech_tickets, dashboard
from .routers import dailys
from .routers import manuals
from .routers import ticket_types
from .services import daily_scheduler

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
    import sys
    
    # Log loaded environment variables (truncated for security)
    anthropic_key = settings.anthropic_api_key
    meta_token = settings.meta_whatsapp_token
    
    anthropic_status = "❌ INVALID/PLACEHOLDER" if anthropic_key.startswith("your_") else f"✓ {anthropic_key[:15]}...{anthropic_key[-8:]}"
    meta_status = "❌ INVALID/PLACEHOLDER" if meta_token.startswith("YOUR_") else f"✓ {meta_token[:15]}...{meta_token[-8:]}"
    
    print("\n" + "═" * 70, file=sys.stderr)
    print("🔧 Environment Variables Loaded:", file=sys.stderr)
    print(f"  MongoDB:      {settings.mongodb_url.replace('mongodb://', '').split(':')[0]}", file=sys.stderr)
    print(f"  Meta Token:   {meta_status}", file=sys.stderr)
    print(f"  Meta Phone:   {settings.meta_phone_number_id}", file=sys.stderr)
    print(f"  Anthropic:    {anthropic_status}", file=sys.stderr)
    print(f"  JWT Secret:   {settings.jwt_secret_key[:10]}...{settings.jwt_secret_key[-5:]}", file=sys.stderr)
    print("═" * 70 + "\n", file=sys.stderr)
    sys.stderr.flush()
    
    await connect_db()
    await _seed_admin()

    from .database import get_db
    await daily_scheduler.init_scheduler(get_db())


@app.on_event("shutdown")
async def shutdown():
    daily_scheduler.shutdown()
    await close_db()


async def _seed_admin():
    """Create default super_admin account if no admins exist."""
    from .database import get_db
    db = get_db()
    existing = await db.admins.find_one({"username": settings.admin_username})
    if not existing:
        await db.admins.insert_one({
            "username": settings.admin_username,
            "full_name": "System Administrator",
            "role": "super_admin",
            "active": True,
            "password_hash": hash_password(settings.admin_password),
            "created_at": __import__("datetime").datetime.utcnow(),
            "last_login": None,
        })
    else:
        # Backfill role/full_name for existing seeded admin that lacks them
        updates = {}
        if "role" not in existing:
            updates["role"] = "super_admin"
        if "full_name" not in existing:
            updates["full_name"] = "System Administrator"
        if "active" not in existing:
            updates["active"] = True
        if updates:
            await db.admins.update_one({"username": settings.admin_username}, {"$set": updates})


app.include_router(admin_auth.router)
app.include_router(webhook.router)
app.include_router(tickets.router)
app.include_router(users.router)
app.include_router(machines.router)
app.include_router(messages.router)
app.include_router(audit.router)
app.include_router(photos.router)
app.include_router(simulate.router)
app.include_router(admins.router)
app.include_router(tech_auth.router)
app.include_router(tech_tickets.router)
app.include_router(dashboard.router)
app.include_router(dailys.router)
app.include_router(manuals.router)
app.include_router(ticket_types.router)


@app.get("/settings/public", tags=["settings"])
async def public_settings():
    """Non-sensitive public config values needed by the frontend (no auth required)."""
    return {
        "whatsapp_business_number": settings.whatsapp_business_number,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
