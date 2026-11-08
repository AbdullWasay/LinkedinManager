from __future__ import annotations

import base64
import logging
import mimetypes
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.integrations.google.oauth import get_valid_credentials
from app.services.activity import log_activity

logger = logging.getLogger(__name__)


def _gmail_service(db: Session, user_id: UUID):
    creds = get_valid_credentials(db, user_id)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def send_email(
    db: Session,
    user_id: UUID,
    *,
    to_email: str,
    subject: str,
    body: str,
    attachment_path: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> dict[str, Any]:
    """Send email via Gmail API. Does NOT bypass approval — callers must enforce it."""
    service = _gmail_service(db, user_id)
    message = EmailMessage()
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    if attachment_path:
        path = Path(attachment_path)
        if not path.exists():
            raise FileNotFoundError(f"Attachment not found: {attachment_path}")
        ctype, _ = mimetypes.guess_type(str(path))
        maintype, subtype = (ctype or "application/pdf").split("/", 1)
        message.add_attachment(
            path.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            filename=path.name,
        )

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body_payload: dict[str, Any] = {"raw": raw}
    if thread_id:
        body_payload["threadId"] = thread_id

    sent = service.users().messages().send(userId="me", body=body_payload).execute()
    log_activity(
        db,
        user_id=user_id,
        category="email",
        action="gmail_send",
        message=f"Sent email to {to_email}",
        details={
            "gmail_message_id": sent.get("id"),
            "thread_id": sent.get("threadId"),
            "subject": subject,
        },
    )
    return {
        "gmail_message_id": sent.get("id"),
        "thread_id": sent.get("threadId"),
        "label_ids": sent.get("labelIds", []),
    }


def list_recent_messages(db: Session, user_id: UUID, *, max_results: int = 20) -> list[dict[str, Any]]:
    service = _gmail_service(db, user_id)
    response = (
        service.users()
        .messages()
        .list(userId="me", maxResults=max_results, q="in:inbox")
        .execute()
    )
    messages = []
    for item in response.get("messages", []):
        full = (
            service.users()
            .messages()
            .get(userId="me", id=item["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"])
            .execute()
        )
        headers = {h["name"]: h["value"] for h in full.get("payload", {}).get("headers", [])}
        messages.append(
            {
                "gmail_message_id": full.get("id"),
                "thread_id": full.get("threadId"),
                "snippet": full.get("snippet"),
                "from": headers.get("From"),
                "subject": headers.get("Subject"),
                "date": headers.get("Date"),
                "label_ids": full.get("labelIds", []),
            }
        )
    return messages
