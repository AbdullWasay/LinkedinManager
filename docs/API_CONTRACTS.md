# AI Job Hunter — API Contracts

Base URL: `/api/v1`  
Auth: Bearer session / Google OAuth cookie (Phase 1–2: single-user token).  
All IDs are UUIDs. Errors: `{ "detail": string | object }`.

---

## Health

### `GET /health`
```json
{ "status": "ok", "db": true, "redis": true }
```

---

## Auth / Google

### `GET /auth/google/login`
Redirects to Google OAuth consent (Sheets, Gmail, Drive scopes).

### `GET /auth/google/callback?code=&state=`
Exchanges code, stores encrypted tokens, creates Sheets workbook if missing, returns redirect to dashboard.

### `GET /auth/status`
```json
{
  "authenticated": true,
  "email": "user@gmail.com",
  "google_connected": true,
  "scopes": ["..."],
  "spreadsheet_id": "...",
  "spreadsheet_url": "https://docs.google.com/spreadsheets/d/..."
}
```

### `POST /auth/google/disconnect`
Revokes tokens (best-effort), clears credentials.

---

## Profile

### `GET /profile`
Returns full user profile.

### `PUT /profile`
Body: editable profile fields (name, links, background, projects, targets, match_weights).  
Never invents employment history.

---

## Settings & Automation

### `GET /settings`
### `PATCH /settings`
```json
{
  "automation_paused": false,
  "emergency_stop": false,
  "auto_send_enabled": false,
  "discovery_interval_hours": 6,
  "sheets_sync_interval_minutes": 10,
  "daily_send_limit": 20,
  "follow_up_days": [3, 7, 14]
}
```

### `POST /automation/pause`
### `POST /automation/resume`
### `POST /automation/emergency-stop`
### `POST /automation/run/{task_name}`  
`task_name`: `job_discovery` | `sheets_sync` | `gmail_reconcile` | …

---

## Jobs

### `GET /jobs?status=&min_score=&opportunity_type=&page=&limit=`
### `GET /jobs/{id}`
### `PATCH /jobs/{id}` — status, notes
### `POST /jobs/discover` — enqueue discovery
### `POST /jobs/{id}/match` — re-run matching

---

## Companies & Contacts

### `GET /companies`
### `GET /companies/{id}`
### `POST /companies/{id}/research`
### `GET /contacts?company_id=`
### `POST /contacts/{id}/verify-email`

---

## Applications

### `GET /applications?stage=`
### `GET /applications/{id}`
### `PATCH /applications/{id}` — stage, notes, interview_at
### `GET /applications/{id}/events`

Stages: `discovered | qualified | researched | drafted | approved | sent | replied | interview | offer | rejected`

---

## Email Drafts & Approval

### `GET /email-drafts?approval_status=pending`
### `GET /email-drafts/{id}`
Response includes company, position, recipient, verification status, job URL, match score, subject, body, resume, duplicate_check, blocklist_check.

### `POST /email-drafts/{id}/approve`
### `POST /email-drafts/{id}/reject`
### `POST /email-drafts/{id}/skip`
### `PATCH /email-drafts/{id}` — edit subject/body/resume then re-approve

### `POST /email-drafts/{id}/send`  
Requires `approval_status=approved`. Runs compliance gate. Sends via Gmail API with attachment.

---

## Email Messages / Replies

### `GET /emails?thread_id=&direction=`
### `POST /emails/reconcile` — pull Gmail
### `POST /emails/{id}/classify` — AI classification

---

## Resumes

### `GET /resumes`
### `POST /resumes` — upload / create variant
### `POST /resumes/generate` — tailored CV (factual checks)
### `GET /resumes/{id}/download`

---

## Blocklist

### `GET /blocklist`
### `POST /blocklist`
### `PATCH /blocklist/{id}`
### `DELETE /blocklist/{id}` — soft delete

---

## Google Sheets Sync

### `POST /sync/sheets/push`
### `POST /sync/sheets/pull`
### `POST /sync/sheets/full`
### `GET /sync/status`

---

## Activity Logs & Analytics

### `GET /activity-logs?category=&limit=`
### `GET /analytics/overview`
```json
{
  "jobs_discovered": 0,
  "avg_match_score": 0,
  "pending_approvals": 0,
  "emails_sent": 0,
  "replies": 0,
  "interviews": 0,
  "applications_by_stage": {}
}
```

---

## Phase 1–2 Implemented Surface

| Endpoint group | Phase |
|----------------|-------|
| Health, Profile, Settings | 1 |
| Auth Google, Sheets create/sync foundations | 2 |
| Gmail send/reconcile foundations | 2 |
| Drive folder + resume upload foundations | 2 |
| Jobs/Agents/Approval | 3–6 |
