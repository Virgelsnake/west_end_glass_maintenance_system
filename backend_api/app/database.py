from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

client: AsyncIOMotorClient = None


def get_client() -> AsyncIOMotorClient:
    return client


def get_db():
    return client[settings.mongodb_db_name]


async def connect_db():
    global client
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = get_db()

    # Ensure unique indexes
    await db.users.create_index("phone_number", unique=True)
    await db.machines.create_index("machine_id", unique=True)
    await db.tickets.create_index([("machine_id", 1), ("status", 1)])
    await db.audit_logs.create_index([("ticket_id", 1), ("timestamp", -1)])
    await db.messages.create_index([("ticket_id", 1), ("timestamp", 1)])


async def close_db():
    global client
    if client:
        client.close()
