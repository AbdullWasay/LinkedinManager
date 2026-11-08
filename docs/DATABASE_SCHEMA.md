# AI Job Hunter — Database Schema

All primary keys are UUID (`gen_random_uuid()`). Timestamps are UTC.

## Entity Relationship (simplified)

```
users ──┬── user_profiles
        ├── oauth_credentials
        ├── resumes
        ├── companies ──┬── jobs
        │               └── contacts
        ├── applications ──┬── email_drafts
        │                  ├── email_messages
        │                  └── application_events
        ├── blocklist_entries
        ├── settings
        ├── sync_state
        └── activity_logs
```

## Tables

### users
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| email | VARCHAR UNIQUE | |
| name | VARCHAR | |
| is_active | BOOLEAN | default true |
| created_at / updated_at | TIMESTAMPTZ | |

### user_profiles
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK UNIQUE | |
| full_name | VARCHAR | |
| linkedin_url | VARCHAR | |
| portfolio_url | VARCHAR | |
| education | JSONB | |
| professional_background | JSONB | skills, roles, summary |
| projects | JSONB | |
| target_positions | JSONB | |
| target_markets | JSONB | |
| salary_expectations | JSONB | nullable |
| employment_types | JSONB | full-time, contract, etc. |
| match_weights | JSONB | configurable scoring |
| created_at / updated_at | TIMESTAMPTZ | |

### oauth_credentials
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | |
| provider | VARCHAR | `google` |
| scopes | TEXT[] | |
| access_token_enc | TEXT | encrypted |
| refresh_token_enc | TEXT | encrypted |
| token_expiry | TIMESTAMPTZ | |
| spreadsheet_id | VARCHAR | nullable |
| drive_folder_id | VARCHAR | nullable |
| gmail_history_id | VARCHAR | nullable |
| created_at / updated_at | TIMESTAMPTZ | |

### companies
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | |
| name | VARCHAR | |
| domain | VARCHAR | |
| website | VARCHAR | |
| linkedin_url | VARCHAR | |
| careers_url | VARCHAR | |
| industry | VARCHAR | |
| size | VARCHAR | |
| location | VARCHAR | |
| research_notes | TEXT | |
| research_status | VARCHAR | pending/researched/failed |
| version | INT | optimistic lock |
| sheet_row_hash | VARCHAR | |
| is_deleted | BOOLEAN | |
| created_at / updated_at | TIMESTAMPTZ | |

### jobs
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | |
| company_id | UUID FK nullable | |
| title | VARCHAR | |
| description | TEXT | |
| source | VARCHAR | greenhouse, lever, etc. |
| source_url | VARCHAR UNIQUE-ish | dedupe key with user |
| location | VARCHAR | |
| employment_type | VARCHAR | |
| is_remote | BOOLEAN | |
| salary_range | VARCHAR | |
| opportunity_type | VARCHAR | `vacancy` \| `hiring_signal` |
| status | VARCHAR | discovered → … |
| match_score | FLOAT | |
| match_details | JSONB | strengths, gaps, concerns |
| raw_payload | JSONB | |
| version | INT | |
| sheet_row_hash | VARCHAR | |
| is_deleted | BOOLEAN | |
| discovered_at / created_at / updated_at | TIMESTAMPTZ | |

Unique constraint: `(user_id, source, source_url)` where source_url not null.

### contacts
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | |
| company_id | UUID FK | |
| full_name | VARCHAR | |
| role_title | VARCHAR | |
| email | VARCHAR | |
| email_status | VARCHAR | verified / unverified / guessed |
| linkedin_url | VARCHAR | |
| source | VARCHAR | |
| notes | TEXT | |
| last_contacted_at | TIMESTAMPTZ | |
| version | INT | |
| sheet_row_hash | VARCHAR | |
| is_deleted | BOOLEAN | |
| created_at / updated_at | TIMESTAMPTZ | |

### applications
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | |
| job_id | UUID FK | |
| company_id | UUID FK | |
| contact_id | UUID FK nullable | |
| stage | VARCHAR | discovered…offer/rejected |
| resume_id | UUID FK nullable | |
| thread_id | VARCHAR | Gmail thread |
| follow_up_at | TIMESTAMPTZ | |
| interview_at | TIMESTAMPTZ | |
| notes | TEXT | |
| version | INT | |
| sheet_row_hash | VARCHAR | |
| is_deleted | BOOLEAN | |
| created_at / updated_at | TIMESTAMPTZ | |

### application_events
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| application_id | UUID FK | |
| event_type | VARCHAR | |
| payload | JSONB | |
| created_at | TIMESTAMPTZ | |

### resumes
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | |
| name | VARCHAR | Master, Full-stack, etc. |
| variant | VARCHAR | master/fullstack/frontend/backend/ai |
| content_json | JSONB | structured facts only |
| drive_file_id | VARCHAR | |
| local_path | VARCHAR | |
| is_master | BOOLEAN | |
| created_at / updated_at | TIMESTAMPTZ | |

### email_drafts
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | |
| application_id | UUID FK | |
| contact_id | UUID FK | |
| subject | VARCHAR | |
| body | TEXT | |
| resume_id | UUID FK | |
| outreach_type | VARCHAR | application/cto/founder/… |
| approval_status | VARCHAR | pending/approved/rejected/skipped/edited |
| blocklist_checked_at | TIMESTAMPTZ | |
| duplicate_checked_at | TIMESTAMPTZ | |
| match_score_snapshot | FLOAT | |
| created_at / updated_at | TIMESTAMPTZ | |

### email_messages
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | |
| application_id | UUID FK nullable | |
| draft_id | UUID FK nullable | |
| direction | VARCHAR | outbound/inbound |
| gmail_message_id | VARCHAR | |
| thread_id | VARCHAR | |
| from_email | VARCHAR | |
| to_email | VARCHAR | |
| subject | VARCHAR | |
| body | TEXT | |
| classification | VARCHAR | interested/interview/… |
| labels | JSONB | |
| sent_at / received_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |

### blocklist_entries
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | |
| entry_type | VARCHAR | company/domain/email/person/job/keyword |
| value | VARCHAR | |
| reason | TEXT | |
| is_permanent | BOOLEAN | |
| expires_at | TIMESTAMPTZ nullable | |
| version | INT | |
| sheet_row_hash | VARCHAR | |
| is_deleted | BOOLEAN | |
| created_at / updated_at | TIMESTAMPTZ | |

### settings
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK UNIQUE | |
| automation_paused | BOOLEAN | |
| emergency_stop | BOOLEAN | |
| auto_send_enabled | BOOLEAN | default false |
| discovery_interval_hours | INT | default 6 |
| sheets_sync_interval_minutes | INT | default 10 |
| daily_send_limit | INT | |
| follow_up_days | JSONB | e.g. [3,7,14] |
| extra | JSONB | |
| version | INT | |
| sheet_row_hash | VARCHAR | |
| updated_at | TIMESTAMPTZ | |

### sync_state
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | |
| resource | VARCHAR | jobs/companies/… |
| last_pulled_at | TIMESTAMPTZ | |
| last_pushed_at | TIMESTAMPTZ | |
| last_error | TEXT | |
| metadata | JSONB | |

### activity_logs
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | |
| category | VARCHAR | agent/sync/email/security/system |
| action | VARCHAR | |
| status | VARCHAR | success/failure/warning |
| message | TEXT | |
| details | JSONB | |
| created_at | TIMESTAMPTZ | |

## Indexes (critical)

- `jobs(user_id, status)`, `jobs(user_id, match_score DESC)`
- `applications(user_id, stage)`, `applications(thread_id)`
- `email_messages(thread_id)`, `email_messages(gmail_message_id)` UNIQUE
- `blocklist_entries(user_id, entry_type, value)`
- `contacts(user_id, email)`, `companies(user_id, domain)`
