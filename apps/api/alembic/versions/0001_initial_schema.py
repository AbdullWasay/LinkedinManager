"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("linkedin_url", sa.String(512), server_default=""),
        sa.Column("portfolio_url", sa.String(512), server_default=""),
        sa.Column("education", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("professional_background", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("projects", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("target_positions", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("target_markets", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("salary_expectations", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("employment_types", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("match_weights", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "oauth_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False, server_default="google"),
        sa.Column("scopes", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("access_token_enc", sa.Text(), server_default=""),
        sa.Column("refresh_token_enc", sa.Text(), server_default=""),
        sa.Column("token_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("spreadsheet_id", sa.String(255), nullable=True),
        sa.Column("drive_folder_id", sa.String(255), nullable=True),
        sa.Column("gmail_history_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_oauth_credentials_user_id", "oauth_credentials", ["user_id"])

    op.create_table(
        "settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("automation_paused", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("emergency_stop", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("auto_send_enabled", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("discovery_interval_hours", sa.Integer(), server_default="6"),
        sa.Column("sheets_sync_interval_minutes", sa.Integer(), server_default="10"),
        sa.Column("daily_send_limit", sa.Integer(), server_default="20"),
        sa.Column("follow_up_days", postgresql.JSONB(), server_default=sa.text("'[3,7,14]'::jsonb")),
        sa.Column("extra", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("sheet_row_hash", sa.String(64), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(255), nullable=True),
        sa.Column("website", sa.String(512), nullable=True),
        sa.Column("linkedin_url", sa.String(512), nullable=True),
        sa.Column("careers_url", sa.String(512), nullable=True),
        sa.Column("industry", sa.String(255), nullable=True),
        sa.Column("size", sa.String(64), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("research_notes", sa.Text(), nullable=True),
        sa.Column("research_status", sa.String(64), server_default="pending"),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("sheet_row_hash", sa.String(64), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_companies_user_id", "companies", ["user_id"])
    op.create_index("ix_companies_domain", "companies", ["domain"])

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("employment_type", sa.String(64), nullable=True),
        sa.Column("is_remote", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("salary_range", sa.String(255), nullable=True),
        sa.Column("opportunity_type", sa.String(32), server_default="vacancy"),
        sa.Column("status", sa.String(64), server_default="discovered"),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("match_details", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("raw_payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("sheet_row_hash", sa.String(64), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "source", "source_url", name="uq_jobs_source_url"),
    )
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])

    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role_title", sa.String(255), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("email_status", sa.String(32), server_default="unverified"),
        sa.Column("linkedin_url", sa.String(512), nullable=True),
        sa.Column("source", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("last_contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("sheet_row_hash", sa.String(64), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_contacts_user_id", "contacts", ["user_id"])
    op.create_index("ix_contacts_email", "contacts", ["email"])

    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("variant", sa.String(64), nullable=False),
        sa.Column("content_json", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("drive_file_id", sa.String(255), nullable=True),
        sa.Column("local_path", sa.String(1024), nullable=True),
        sa.Column("is_master", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stage", sa.String(64), server_default="discovered"),
        sa.Column("thread_id", sa.String(255), nullable=True),
        sa.Column("follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interview_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("sheet_row_hash", sa.String(64), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_applications_user_id", "applications", ["user_id"])
    op.create_index("ix_applications_stage", "applications", ["stage"])
    op.create_index("ix_applications_thread_id", "applications", ["thread_id"])

    op.create_table(
        "application_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_application_events_application_id", "application_events", ["application_id"])

    op.create_table(
        "email_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("subject", sa.String(998), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("outreach_type", sa.String(64), server_default="application"),
        sa.Column("approval_status", sa.String(32), server_default="pending"),
        sa.Column("blocklist_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duplicate_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("match_score_snapshot", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_email_drafts_user_id", "email_drafts", ["user_id"])
    op.create_index("ix_email_drafts_approval_status", "email_drafts", ["approval_status"])

    op.create_table(
        "email_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("email_drafts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("gmail_message_id", sa.String(255), nullable=True),
        sa.Column("thread_id", sa.String(255), nullable=True),
        sa.Column("from_email", sa.String(320), nullable=True),
        sa.Column("to_email", sa.String(320), nullable=True),
        sa.Column("subject", sa.String(998), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("classification", sa.String(64), nullable=True),
        sa.Column("labels", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("gmail_message_id"),
    )
    op.create_index("ix_email_messages_user_id", "email_messages", ["user_id"])
    op.create_index("ix_email_messages_thread_id", "email_messages", ["thread_id"])

    op.create_table(
        "blocklist_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entry_type", sa.String(64), nullable=False),
        sa.Column("value", sa.String(512), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("is_permanent", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("sheet_row_hash", sa.String(64), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_blocklist_entries_user_id", "blocklist_entries", ["user_id"])

    op.create_table(
        "sync_state",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource", sa.String(64), nullable=False),
        sa.Column("last_pulled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_pushed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_sync_state_user_id", "sync_state", ["user_id"])

    op.create_table(
        "activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), server_default="success"),
        sa.Column("message", sa.Text(), server_default=""),
        sa.Column("details", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_activity_logs_user_id", "activity_logs", ["user_id"])
    op.create_index("ix_activity_logs_category", "activity_logs", ["category"])
    op.create_index("ix_activity_logs_created_at", "activity_logs", ["created_at"])


def downgrade() -> None:
    for table in [
        "activity_logs",
        "sync_state",
        "blocklist_entries",
        "email_messages",
        "email_drafts",
        "application_events",
        "applications",
        "resumes",
        "contacts",
        "jobs",
        "companies",
        "settings",
        "oauth_credentials",
        "user_profiles",
        "users",
    ]:
        op.drop_table(table)
