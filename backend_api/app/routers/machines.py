from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from ..auth import get_current_admin
from ..database import get_db
from ..models.machine import MachineCreate, MachineUpdate
from datetime import datetime

router = APIRouter(prefix="/machines", tags=["machines"])


def _serialize(doc) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@router.get("")
async def list_machines(current_admin: str = Depends(get_current_admin)):
    db = get_db()
    machines = await db.machines.find().to_list(length=None)
    return [_serialize(m) for m in machines]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_machine(machine: MachineCreate, current_admin: str = Depends(get_current_admin)):
    db = get_db()
    existing = await db.machines.find_one({"machine_id": machine.machine_id})
    if existing:
        raise HTTPException(status_code=409, detail="Machine ID already registered")
    doc = machine.model_dump()
    doc["created_at"] = datetime.utcnow()
    result = await db.machines.insert_one(doc)
    return {**doc, "_id": str(result.inserted_id)}


@router.get("/{machine_id}")
async def get_machine(machine_id: str, current_admin: str = Depends(get_current_admin)):
    db = get_db()
    machine = await db.machines.find_one({"machine_id": machine_id})
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    return _serialize(machine)


@router.patch("/{machine_id}")
async def update_machine(
    machine_id: str,
    update: MachineUpdate,
    current_admin: str = Depends(get_current_admin)
):
    db = get_db()
    changes = {k: v for k, v in update.model_dump().items() if v is not None}
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.machines.update_one({"machine_id": machine_id}, {"$set": changes})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Machine not found")
    return {"updated": True}
