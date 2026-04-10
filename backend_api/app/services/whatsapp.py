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
        if resp.status_code >= 400:
            print(f"[WHATSAPP] ERROR: HTTP {resp.status_code}")
            print(f"[WHATSAPP] Response: {resp.text}")
            raise Exception(f"Meta API error: HTTP {resp.status_code} - {resp.text}")
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


async def upload_media(file_bytes: bytes, mime_type: str, filename: str = "photo.jpg") -> str:
    """Upload a media file to WhatsApp and return its media_id."""
    url = f"{WHATSAPP_API_BASE}/{settings.meta_phone_number_id}/media"
    headers = {"Authorization": f"Bearer {settings.meta_whatsapp_token}"}
    files = {
        "file": (filename, file_bytes, mime_type),
        "type": (None, mime_type),
        "messaging_product": (None, "whatsapp"),
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, files=files)
        resp.raise_for_status()
        return resp.json()["id"]


async def send_image_message(to: str, media_id: str, caption: str = "") -> dict:
    """Send a WhatsApp image message using an already-uploaded media_id."""
    url = f"{WHATSAPP_API_BASE}/{settings.meta_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.meta_whatsapp_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {"id": media_id, "caption": caption},
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def send_ticket_photo(to: str, file_path: str, caption: str = "") -> None:
    """Read a local image file, upload it to WhatsApp, and send it to a recipient."""
    import mimetypes
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "image/jpeg"
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    filename = os.path.basename(file_path)
    media_id = await upload_media(file_bytes, mime_type, filename)
    await send_image_message(to=to, media_id=media_id, caption=caption)


async def send_ticket_assignment_notification(
    to: str,
    tech_name: str,
    machine_id: str,
    ticket_title: str = "",  # kept for backward compat, not used in template
) -> dict:
    """
    Notify a technician that a ticket has been assigned to them.
    Uses the westend_glass__machine_servicing_system template (3 params: user_name, service_date, machine_name).
    """
    from datetime import datetime
    url = f"{WHATSAPP_API_BASE}/{settings.meta_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.meta_whatsapp_token}",
        "Content-Type": "application/json",
    }
    now = datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC")
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": "westend_glass__machine_servicing_system",
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": tech_name},
                        {"type": "text", "text": now},
                        {"type": "text", "text": machine_id},
                    ],
                }
            ],
        },
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            raise Exception(
                f"Meta template API error: HTTP {resp.status_code} — {resp.text}"
            )
        return resp.json()
