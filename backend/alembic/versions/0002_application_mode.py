"""add application mode fields for manual vs email apply

Revision ID: 0002_app_mode
Revises: 0001_initial
Create Date: 2026-11-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_app_mode"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("application_mode", sa.String(32), server_default="unknown"))
    op.add_column("jobs", sa.Column("apply_url", sa.String(1024), nullable=True))
    op.add_column("jobs", sa.Column("apply_email", sa.String(320), nullable=True))
    op.add_column(
        "jobs",
        sa.Column("manual_apply_required", sa.Boolean(), server_default=sa.text("true")),
    )
    op.add_column(
        "jobs",
        sa.Column("manual_apply_status", sa.String(32), server_default="pending"),
    )
    op.create_index("ix_jobs_application_mode", "jobs", ["application_mode"])
    op.create_index("ix_jobs_manual_apply_required", "jobs", ["manual_apply_required"])
    op.create_index("ix_jobs_manual_apply_status", "jobs", ["manual_apply_status"])


def downgrade() -> None:
    op.drop_index("ix_jobs_manual_apply_status", table_name="jobs")
    op.drop_index("ix_jobs_manual_apply_required", table_name="jobs")
    op.drop_index("ix_jobs_application_mode", table_name="jobs")
    op.drop_column("jobs", "manual_apply_status")
    op.drop_column("jobs", "manual_apply_required")
    op.drop_column("jobs", "apply_email")
    op.drop_column("jobs", "apply_url")
    op.drop_column("jobs", "application_mode")
