from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from bson import ObjectId
from datetime import datetime
import os
import uuid
import logging

from ..auth import get_current_admin, get_current_technician
from ..database import get_db
from ..config import settings
from ..services.audit_service import log_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/manuals", tags=["manuals"])

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".jpg", ".jpeg", ".png", ".webp"}
_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg",
    "image/png",
    "image/webp",
}


def _serialize(doc) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@router.get("")
async def list_manuals(current_admin: dict = Depends(get_current_admin)):
    db = get_db()
    manuals = await db.manuals.find().sort("uploaded_at", -1).to_list(length=None)
    return [_serialize(m) for m in manuals]


@router.post("", status_code=201)
async def upload_manual(
    title: str = Form(...),
    file: UploadFile = File(...),
    current_admin: dict = Depends(get_current_admin),
):
    # Validate extension
    original_filename = file.filename or "upload"
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Accepted: {', '.join(_ALLOWED_EXTENSIONS)}",
        )

    # Validate MIME type
    if file.content_type and file.content_type not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"MIME type '{file.content_type}' not allowed.",
        )

    # Build a safe stored filename with uuid prefix
    safe_name = f"{uuid.uuid4().hex}_{os.path.basename(original_filename)}"
    os.makedirs(settings.manual_storage_path, exist_ok=True)
    file_path = os.path.join(settings.manual_storage_path, safe_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    file_type = ext.lstrip(".")
    doc = {
        "title": title.strip(),
        "original_filename": original_filename,
        "stored_filename": safe_name,
        "file_type": file_type,
        "file_size": len(content),
        "uploaded_at": datetime.utcnow(),
        "uploaded_by": current_admin["username"],
    }

    db = get_db()
    result = await db.manuals.insert_one(doc)
    manual_id = str(result.inserted_id)

    await log_event(
        db,
        event="manual_uploaded",
        actor=current_admin["username"],
        actor_type="admin",
        payload={"manual_id": manual_id, "title": title, "filename": original_filename},
    )

    return {**doc, "_id": manual_id}


@router.get("/{manual_id}/file")
async def get_manual_file(
    manual_id: str,
    current_admin: dict = Depends(get_current_admin),
):
    if not ObjectId.is_valid(manual_id):
        raise HTTPException(status_code=400, detail="Invalid manual ID")

    db = get_db()
    manual = await db.manuals.find_one({"_id": ObjectId(manual_id)})
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found")

    safe_name = os.path.basename(manual["stored_filename"])
    file_path = os.path.join(settings.manual_storage_path, safe_name)
    if not os.path.isfile(file_path):
        logger.error(
            "Manual file missing: manual_id=%s stored_name=%s expected_path=%s exists=%s storage_dir_exists=%s",
            manual_id,
            safe_name,
            file_path,
            os.path.exists(file_path),
            os.path.isdir(settings.manual_storage_path),
        )
        raise HTTPException(
            status_code=404,
            detail="Document file not found on disk. It may have been deleted. Please re-upload it.",
        )

    ext = os.path.splitext(manual["original_filename"])[1].lower()
    _INLINE_MIME = {
        ".pdf":  "application/pdf",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".webp": "image/webp",
    }
    mime = _INLINE_MIME.get(ext, "application/octet-stream")
    return FileResponse(
        file_path,
        filename=manual["original_filename"],
        media_type=mime,
    )


@router.delete("/{manual_id}", status_code=204)
async def delete_manual(
    manual_id: str,
    current_admin: dict = Depends(get_current_admin),
):
    if not ObjectId.is_valid(manual_id):
        raise HTTPException(status_code=400, detail="Invalid manual ID")

    db = get_db()
    manual = await db.manuals.find_one({"_id": ObjectId(manual_id)})
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found")

    # Remove from disk (non-fatal if already gone)
    safe_name = os.path.basename(manual["stored_filename"])
    file_path = os.path.join(settings.manual_storage_path, safe_name)
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
    except OSError as exc:
        logger.warning("Could not delete manual file %s: %s", file_path, exc)

    await db.manuals.delete_one({"_id": ObjectId(manual_id)})

    await log_event(
        db,
        event="manual_deleted",
        actor=current_admin["username"],
        actor_type="admin",
        payload={"manual_id": manual_id, "title": manual.get("title")},
    )


# ── Tech portal endpoint (JWT tech auth) ──────────────────────────────────────

@router.get("/tech/{manual_id}/file")
async def get_manual_file_tech(
    manual_id: str,
    tech: dict = Depends(get_current_technician),
):
    if not ObjectId.is_valid(manual_id):
        raise HTTPException(status_code=400, detail="Invalid manual ID")

    db = get_db()
    manual = await db.manuals.find_one({"_id": ObjectId(manual_id)})
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found")

    safe_name = os.path.basename(manual["stored_filename"])
    file_path = os.path.join(settings.manual_storage_path, safe_name)
    if not os.path.isfile(file_path):
        logger.error(
            "Manual file missing (tech): manual_id=%s stored_name=%s expected_path=%s exists=%s storage_dir_exists=%s",
            manual_id,
            safe_name,
            file_path,
            os.path.exists(file_path),
            os.path.isdir(settings.manual_storage_path),
        )
        raise HTTPException(
            status_code=404,
            detail="Document file not found on disk. It may have been deleted. Please contact your supervisor.",
        )

    ext = os.path.splitext(manual["original_filename"])[1].lower()
    _INLINE_MIME = {
        ".pdf":  "application/pdf",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".webp": "image/webp",
    }
    mime = _INLINE_MIME.get(ext, "application/octet-stream")
    return FileResponse(
        file_path,
        filename=manual["original_filename"],
        media_type=mime,
    )
