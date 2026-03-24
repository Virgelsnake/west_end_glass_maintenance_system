from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
import os
from ..auth import get_current_admin
from ..config import settings

router = APIRouter(prefix="/tickets", tags=["photos"])


@router.get("/{ticket_id}/photos/{filename}")
async def get_photo(
    ticket_id: str,
    filename: str,
    current_admin: str = Depends(get_current_admin),
):
    """Serve a stored photo file for a ticket step."""
    # Prevent path traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(settings.photo_storage_path, ticket_id, safe_filename)

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Photo not found")

    return FileResponse(file_path)
