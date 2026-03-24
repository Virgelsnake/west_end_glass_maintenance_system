import hmac
import hashlib
from fastapi import Request, HTTPException
from ..config import settings


async def verify_webhook_signature(request: Request) -> bytes:
    """Validate X-Hub-Signature-256 from Meta Cloud API webhook."""
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header.startswith("sha256="):
        raise HTTPException(status_code=403, detail="Missing or invalid signature header")

    body = await request.body()
    expected_sig = hmac.new(
        settings.meta_app_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    received_sig = signature_header.removeprefix("sha256=")

    if not hmac.compare_digest(expected_sig, received_sig):
        raise HTTPException(status_code=403, detail="Webhook signature verification failed")

    return body
