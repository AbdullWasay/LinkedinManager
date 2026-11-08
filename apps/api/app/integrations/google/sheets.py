from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    Application,
    BlocklistEntry,
    Company,
    Contact,
    EmailDraft,
    Job,
    OAuthCredential,
    SyncState,
    UserSettings,
)
from app.integrations.google.oauth import get_credential_row, get_valid_credentials
from app.services.activity import log_activity

logger = logging.getLogger(__name__)

WORKSHEETS = [
    "Job Opportunities",
    "Contacts",
    "Email Outreach",
    "Blocklist",
    "Application Tracker",
    "Settings",
    "Activity Logs",
]

HEADERS: dict[str, list[str]] = {
    "Job Opportunities": [
        "id",
        "title",
        "company_name",
        "source",
        "source_url",
        "location",
        "employment_type",
        "is_remote",
        "opportunity_type",
        "application_mode",
        "manual_apply_required",
        "manual_apply_status",
        "apply_url",
        "apply_email",
        "status",
        "match_score",
        "updated_at",
    ],
    "Contacts": [
        "id",
        "company_id",
        "full_name",
        "role_title",
        "email",
        "email_status",
        "linkedin_url",
        "updated_at",
    ],
    "Email Outreach": [
        "id",
        "application_id",
        "subject",
        "outreach_type",
        "approval_status",
        "match_score_snapshot",
        "updated_at",
    ],
    "Blocklist": [
        "id",
        "entry_type",
        "value",
        "reason",
        "is_permanent",
        "expires_at",
        "is_deleted",
        "updated_at",
    ],
    "Application Tracker": [
        "id",
        "job_id",
        "company_id",
        "contact_id",
        "stage",
        "thread_id",
        "follow_up_at",
        "interview_at",
        "notes",
        "updated_at",
    ],
    "Settings": [
        "id",
        "automation_paused",
        "emergency_stop",
        "auto_send_enabled",
        "discovery_interval_hours",
        "sheets_sync_interval_minutes",
        "daily_send_limit",
        "follow_up_days",
        "version",
        "updated_at",
    ],
    "Activity Logs": [
        "id",
        "category",
        "action",
        "status",
        "message",
        "created_at",
    ],
}


def _sheets_service(db: Session, user_id: UUID):
    creds = get_valid_credentials(db, user_id)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _row_hash(values: list[Any]) -> str:
    payload = json.dumps(values, default=str, sort_keys=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def ensure_spreadsheet(db: Session, user_id: UUID) -> str:
    settings = get_settings()
    row = get_credential_row(db, user_id)
    if row is None:
        raise RuntimeError("Google not connected")
    if row.spreadsheet_id:
        return row.spreadsheet_id

    service = _sheets_service(db, user_id)
    body = {
        "properties": {"title": settings.google_sheets_title},
        "sheets": [{"properties": {"title": name}} for name in WORKSHEETS],
    }
    created = service.spreadsheets().create(body=body).execute()
    spreadsheet_id = created["spreadsheetId"]

    # Remove default Sheet1 if Google added an extra sheet somehow — create() with
    # sheets list should already define only our worksheets.

    for worksheet, headers in HEADERS.items():
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{worksheet}'!A1",
            valueInputOption="RAW",
            body={"values": [headers]},
        ).execute()

    row.spreadsheet_id = spreadsheet_id
    log_activity(
        db,
        user_id=user_id,
        category="sync",
        action="spreadsheet_created",
        message=f"Created spreadsheet {settings.google_sheets_title}",
        details={"spreadsheet_id": spreadsheet_id},
        commit=False,
    )
    db.commit()
    return spreadsheet_id


def _upsert_sync_state(
    db: Session,
    user_id: UUID,
    resource: str,
    *,
    pushed: bool = False,
    pulled: bool = False,
    error: Optional[str] = None,
) -> None:
    state = (
        db.query(SyncState)
        .filter(SyncState.user_id == user_id, SyncState.resource == resource)
        .one_or_none()
    )
    if state is None:
        state = SyncState(user_id=user_id, resource=resource)
        db.add(state)
    now = datetime.now(timezone.utc)
    if pushed:
        state.last_pushed_at = now
    if pulled:
        state.last_pulled_at = now
    state.last_error = error


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return str(value)


def _delete_worksheet_if_exists(service, spreadsheet_id: str, title: str) -> bool:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in meta.get("sheets", []):
        props = sheet.get("properties", {})
        if props.get("title") == title:
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": [{"deleteSheet": {"sheetId": props["sheetId"]}}]},
            ).execute()
            return True
    return False


def push_all(db: Session, user_id: UUID) -> dict[str, Any]:
    spreadsheet_id = ensure_spreadsheet(db, user_id)
    service = _sheets_service(db, user_id)
    results: dict[str, Any] = {}

    # Companies worksheet removed from product surface — delete if leftover.
    if _delete_worksheet_if_exists(service, spreadsheet_id, "Companies"):
        results["Companies"] = "deleted"

    jobs = db.query(Job).filter(Job.user_id == user_id, Job.is_deleted.is_(False)).all()
    company_ids = [j.company_id for j in jobs if j.company_id]
    company_names = {}
    if company_ids:
        company_names = {
            c.id: c.name
            for c in db.query(Company).filter(Company.id.in_(company_ids)).all()
        }
    job_rows = [
        [
            _fmt(j.id),
            j.title,
            company_names.get(j.company_id, "") if j.company_id else "",
            j.source,
            j.source_url or "",
            j.location or "",
            j.employment_type or "",
            _fmt(j.is_remote),
            j.opportunity_type,
            j.application_mode,
            _fmt(j.manual_apply_required),
            j.manual_apply_status,
            j.apply_url or "",
            j.apply_email or "",
            j.status,
            _fmt(j.match_score),
            _fmt(j.updated_at),
        ]
        for j in jobs
    ]
    _replace_sheet(service, spreadsheet_id, "Job Opportunities", job_rows)
    results["Job Opportunities"] = len(job_rows)
    _upsert_sync_state(db, user_id, "jobs", pushed=True)

    contacts = db.query(Contact).filter(Contact.user_id == user_id, Contact.is_deleted.is_(False)).all()
    contact_rows = [
        [
            _fmt(c.id),
            _fmt(c.company_id),
            c.full_name,
            c.role_title or "",
            c.email or "",
            c.email_status,
            c.linkedin_url or "",
            _fmt(c.updated_at),
        ]
        for c in contacts
    ]
    _replace_sheet(service, spreadsheet_id, "Contacts", contact_rows)
    results["Contacts"] = len(contact_rows)
    _upsert_sync_state(db, user_id, "contacts", pushed=True)

    drafts = db.query(EmailDraft).filter(EmailDraft.user_id == user_id).all()
    draft_rows = [
        [
            _fmt(d.id),
            _fmt(d.application_id),
            d.subject,
            d.outreach_type,
            d.approval_status,
            _fmt(d.match_score_snapshot),
            _fmt(d.updated_at),
        ]
        for d in drafts
    ]
    _replace_sheet(service, spreadsheet_id, "Email Outreach", draft_rows)
    results["Email Outreach"] = len(draft_rows)
    _upsert_sync_state(db, user_id, "email_outreach", pushed=True)

    blocks = db.query(BlocklistEntry).filter(BlocklistEntry.user_id == user_id).all()
    block_rows = [
        [
            _fmt(b.id),
            b.entry_type,
            b.value,
            b.reason or "",
            _fmt(b.is_permanent),
            _fmt(b.expires_at),
            _fmt(b.is_deleted),
            _fmt(b.updated_at),
        ]
        for b in blocks
    ]
    _replace_sheet(service, spreadsheet_id, "Blocklist", block_rows)
    results["Blocklist"] = len(block_rows)
    _upsert_sync_state(db, user_id, "blocklist", pushed=True)

    apps = db.query(Application).filter(Application.user_id == user_id, Application.is_deleted.is_(False)).all()
    app_rows = [
        [
            _fmt(a.id),
            _fmt(a.job_id),
            _fmt(a.company_id),
            _fmt(a.contact_id),
            a.stage,
            a.thread_id or "",
            _fmt(a.follow_up_at),
            _fmt(a.interview_at),
            a.notes or "",
            _fmt(a.updated_at),
        ]
        for a in apps
    ]
    _replace_sheet(service, spreadsheet_id, "Application Tracker", app_rows)
    results["Application Tracker"] = len(app_rows)
    _upsert_sync_state(db, user_id, "applications", pushed=True)

    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).one_or_none()
    settings_rows = []
    if settings:
        settings_rows = [
            [
                _fmt(settings.id),
                _fmt(settings.automation_paused),
                _fmt(settings.emergency_stop),
                _fmt(settings.auto_send_enabled),
                _fmt(settings.discovery_interval_hours),
                _fmt(settings.sheets_sync_interval_minutes),
                _fmt(settings.daily_send_limit),
                _fmt(settings.follow_up_days),
                _fmt(settings.version),
                _fmt(settings.updated_at),
            ]
        ]
    _replace_sheet(service, spreadsheet_id, "Settings", settings_rows)
    results["Settings"] = len(settings_rows)
    _upsert_sync_state(db, user_id, "settings", pushed=True)

    log_activity(
        db,
        user_id=user_id,
        category="sync",
        action="sheets_push",
        message="Pushed database records to Google Sheets",
        details=results,
        commit=False,
    )
    db.commit()
    return {"spreadsheet_id": spreadsheet_id, "counts": results}


def _replace_sheet(service, spreadsheet_id: str, worksheet: str, rows: list[list[Any]]) -> None:
    headers = HEADERS[worksheet]
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=f"'{worksheet}'!A2:Z",
    ).execute()
    values = [headers] + rows
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{worksheet}'!A1",
        valueInputOption="RAW",
        body={"values": values},
    ).execute()


def pull_mutable_sheets(db: Session, user_id: UUID) -> dict[str, Any]:
    """Pull user-editable sheets: Blocklist, Settings, Application Tracker notes/stage."""
    row = get_credential_row(db, user_id)
    if not row or not row.spreadsheet_id:
        raise RuntimeError("Spreadsheet not provisioned")

    service = _sheets_service(db, user_id)
    spreadsheet_id = row.spreadsheet_id
    summary: dict[str, Any] = {"updated": {}, "conflicts": []}

    # Blocklist
    block_values = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range="'Blocklist'!A2:H")
        .execute()
        .get("values", [])
    )
    updated_blocks = 0
    for values in block_values:
        if not values or not values[0]:
            continue
        entry_id = values[0]
        entry = db.query(BlocklistEntry).filter(BlocklistEntry.id == entry_id).one_or_none()
        if entry is None:
            # Allow creating blocklist entries from Sheets when UUID is new-looking
            continue
        sheet_updated = values[7] if len(values) > 7 else ""
        if sheet_updated and entry.updated_at and sheet_updated < entry.updated_at.isoformat():
            summary["conflicts"].append({"resource": "blocklist", "id": entry_id})
            continue
        entry.entry_type = values[1] if len(values) > 1 else entry.entry_type
        entry.value = values[2] if len(values) > 2 else entry.value
        entry.reason = values[3] if len(values) > 3 else entry.reason
        if len(values) > 4:
            entry.is_permanent = str(values[4]).upper() == "TRUE"
        if len(values) > 6:
            entry.is_deleted = str(values[6]).upper() == "TRUE"
        entry.version += 1
        entry.sheet_row_hash = _row_hash(values)
        updated_blocks += 1
    summary["updated"]["blocklist"] = updated_blocks
    _upsert_sync_state(db, user_id, "blocklist", pulled=True)

    # Settings
    settings_values = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range="'Settings'!A2:J")
        .execute()
        .get("values", [])
    )
    if settings_values:
        values = settings_values[0]
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).one_or_none()
        if settings and values:
            sheet_version = int(values[8]) if len(values) > 8 and str(values[8]).isdigit() else 0
            if sheet_version >= settings.version:
                settings.automation_paused = str(values[1]).upper() == "TRUE" if len(values) > 1 else settings.automation_paused
                settings.emergency_stop = str(values[2]).upper() == "TRUE" if len(values) > 2 else settings.emergency_stop
                # Never enable auto_send from Sheets silently
                if len(values) > 4 and values[4]:
                    settings.discovery_interval_hours = int(values[4])
                if len(values) > 5 and values[5]:
                    settings.sheets_sync_interval_minutes = int(values[5])
                if len(values) > 6 and values[6]:
                    settings.daily_send_limit = int(values[6])
                settings.version = max(settings.version, sheet_version) + 1
                summary["updated"]["settings"] = 1
            else:
                summary["conflicts"].append({"resource": "settings", "id": str(settings.id)})
    _upsert_sync_state(db, user_id, "settings", pulled=True)

    # Application tracker stage/notes
    app_values = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range="'Application Tracker'!A2:J")
        .execute()
        .get("values", [])
    )
    updated_apps = 0
    for values in app_values:
        if not values or not values[0]:
            continue
        app = db.query(Application).filter(Application.id == values[0]).one_or_none()
        if app is None:
            continue
        if len(values) > 4 and values[4]:
            app.stage = values[4]
        if len(values) > 8:
            app.notes = values[8]
        app.version += 1
        updated_apps += 1
    summary["updated"]["applications"] = updated_apps
    _upsert_sync_state(db, user_id, "applications", pulled=True)

    log_activity(
        db,
        user_id=user_id,
        category="sync",
        action="sheets_pull",
        message="Pulled mutable Google Sheets changes into database",
        details=summary,
        commit=False,
    )
    db.commit()
    return summary


def sync_status(db: Session, user_id: UUID) -> dict[str, Any]:
    row = get_credential_row(db, user_id)
    states = db.query(SyncState).filter(SyncState.user_id == user_id).all()
    spreadsheet_id = row.spreadsheet_id if row else None
    return {
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_url": (
            f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}" if spreadsheet_id else None
        ),
        "resources": [
            {
                "resource": s.resource,
                "last_pulled_at": s.last_pulled_at.isoformat() if s.last_pulled_at else None,
                "last_pushed_at": s.last_pushed_at.isoformat() if s.last_pushed_at else None,
                "last_error": s.last_error,
            }
            for s in states
        ],
    }
