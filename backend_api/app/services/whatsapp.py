import httpx
import os
from ..config import settings

WHATSAPP_API_BASE = "https://graph.facebook.com/v19.0"


async def send_text_message(to: str, text: str) -> dict:
    """Send a plain text WhatsApp message via Meta Cloud API."""
    url = f"{WHATSAPP_API_BASE}/{settings.meta_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.meta_whatsapp_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def download_media(media_id: str, ticket_id: str, step_index: int) -> str:
    """
    Download a WhatsApp media file by media_id.
    Saves to local disk and returns the saved file path.
    """
    headers = {"Authorization": f"Bearer {settings.meta_whatsapp_token}"}

    # Step 1: Get the download URL for the media_id
    async with httpx.AsyncClient() as client:
        meta_resp = await client.get(
            f"{WHATSAPP_API_BASE}/{media_id}",
            headers=headers,
        )
        meta_resp.raise_for_status()
        media_info = meta_resp.json()

    download_url = media_info["url"]
    mime_type = media_info.get("mime_type", "image/jpeg")
    ext = mime_type.split("/")[-1].split(";")[0]  # e.g. "jpeg"

    # Step 2: Download the actual binary
    async with httpx.AsyncClient() as client:
        file_resp = await client.get(download_url, headers=headers)
        file_resp.raise_for_status()
        content = file_resp.content

    # Step 3: Save to disk
    import time
    timestamp = int(time.time())
    dir_path = os.path.join(settings.photo_storage_path, str(ticket_id))
    os.makedirs(dir_path, exist_ok=True)
    filename = f"{step_index}_{timestamp}.{ext}"
    file_path = os.path.join(dir_path, filename)

    with open(file_path, "wb") as f:
        f.write(content)

    return file_path
