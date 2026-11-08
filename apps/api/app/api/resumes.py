from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.models import Resume
from app.db.session import get_db
from app.integrations.google import drive as drive_integration
from app.services.resume_matching import extract_drive_file_id

router = APIRouter(prefix="/resumes", tags=["resumes"])

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"


class ResumeIn(BaseModel):
    name: str
    variant: str = "custom"
    role_labels: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    drive_url: Optional[str] = None
    is_master: bool = False


class ResumeUpdate(BaseModel):
    name: Optional[str] = None
    variant: Optional[str] = None
    role_labels: Optional[list[str]] = None
    keywords: Optional[list[str]] = None
    drive_url: Optional[str] = None
    is_master: Optional[bool] = None


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "custom"


def _to_dict(resume: Resume) -> dict:
    content = resume.content_json or {}
    return {
        "id": str(resume.id),
        "name": resume.name,
        "variant": resume.variant,
        "role_labels": resume.role_labels or [],
        "keywords": content.get("keywords") or [],
        "drive_url": resume.drive_url,
        "drive_file_id": resume.drive_file_id,
        "local_path": resume.local_path,
        "has_file": bool(resume.local_path or resume.drive_file_id or resume.drive_url),
        "is_master": resume.is_master,
        "updated_at": resume.updated_at.isoformat() if resume.updated_at else None,
    }


def _apply_drive_link(resume: Resume, drive_url: str | None) -> None:
    if not drive_url:
        return
    file_id = extract_drive_file_id(drive_url)
    resume.drive_url = drive_url.strip()
    resume.drive_file_id = file_id


def _set_master(db: Session, user_id: UUID, resume: Resume, is_master: bool) -> None:
    if not is_master:
        resume.is_master = False
        return
    db.query(Resume).filter(Resume.user_id == user_id, Resume.id != resume.id).update(
        {Resume.is_master: False}
    )
    resume.is_master = True


@router.get("")
def list_resumes(db: Session = Depends(get_db), user_id: UUID = Depends(get_current_user_id)) -> dict:
    rows = db.query(Resume).filter(Resume.user_id == user_id).order_by(Resume.is_master.desc(), Resume.name).all()
    return {"total": len(rows), "items": [_to_dict(r) for r in rows]}


@router.post("")
def create_resume(
    payload: ResumeIn,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    variant = payload.variant.strip() or _slug(payload.name)
    existing = (
        db.query(Resume)
        .filter(Resume.user_id == user_id, Resume.variant == variant)
        .one_or_none()
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Resume variant '{variant}' already exists")

    resume = Resume(
        user_id=user_id,
        name=payload.name.strip(),
        variant=variant,
        role_labels=[r.strip() for r in payload.role_labels if r.strip()],
        content_json={"keywords": [k.strip().lower() for k in payload.keywords if k.strip()]},
        is_master=False,
    )
    _apply_drive_link(resume, payload.drive_url)
    db.add(resume)
    db.flush()
    _set_master(db, user_id, resume, payload.is_master)
    db.commit()
    db.refresh(resume)
    return _to_dict(resume)


@router.patch("/{resume_id}")
def update_resume(
    resume_id: UUID,
    payload: ResumeUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).one_or_none()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    if payload.name is not None:
        resume.name = payload.name.strip()
    if payload.variant is not None:
        resume.variant = payload.variant.strip() or resume.variant
    if payload.role_labels is not None:
        resume.role_labels = [r.strip() for r in payload.role_labels if r.strip()]
    if payload.keywords is not None:
        content = dict(resume.content_json or {})
        content["keywords"] = [k.strip().lower() for k in payload.keywords if k.strip()]
        resume.content_json = content
    if payload.drive_url is not None:
        if payload.drive_url.strip():
            _apply_drive_link(resume, payload.drive_url)
        else:
            resume.drive_url = None
            resume.drive_file_id = None
    if payload.is_master is not None:
        _set_master(db, user_id, resume, payload.is_master)
    db.commit()
    db.refresh(resume)
    return _to_dict(resume)


@router.post("/{resume_id}/upload")
async def upload_resume_file(
    resume_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).one_or_none()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "cv.pdf").suffix or ".pdf"
    dest = UPLOAD_DIR / f"{user_id}_{resume.variant}{suffix}"
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    resume.local_path = str(dest)

    # Best-effort mirror into the app Drive folder
    try:
        uploaded = drive_integration.upload_file(db, user_id, local_path=str(dest), name=dest.name)
        resume.drive_file_id = uploaded.get("file_id")
        resume.drive_url = uploaded.get("web_view_link") or resume.drive_url
    except Exception:
        # Local file is enough for Gmail attachment
        pass

    db.commit()
    db.refresh(resume)
    return _to_dict(resume)


@router.post("/from-drive")
def create_from_drive(
    name: str = Form(...),
    drive_url: str = Form(...),
    role_labels: str = Form(""),
    keywords: str = Form(""),
    variant: str = Form(""),
    is_master: bool = Form(False),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    file_id = extract_drive_file_id(drive_url)
    if not file_id:
        raise HTTPException(status_code=400, detail="Could not parse Google Drive file id from URL")
    labels = [x.strip() for x in role_labels.split(",") if x.strip()]
    kws = [x.strip().lower() for x in keywords.split(",") if x.strip()]
    payload = ResumeIn(
        name=name,
        variant=variant or _slug(name),
        role_labels=labels,
        keywords=kws,
        drive_url=drive_url,
        is_master=is_master,
    )
    return create_resume(payload, db=db, user_id=user_id)


@router.delete("/{resume_id}")
def delete_resume(
    resume_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).one_or_none()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    db.delete(resume)
    db.commit()
    return {"ok": True}
