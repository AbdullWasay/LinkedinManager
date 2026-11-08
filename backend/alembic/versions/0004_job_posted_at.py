"""add posted_at to jobs for freshness filtering

Revision ID: 0004_job_posted_at
Revises: 0003_resume_roles
Create Date: 2026-11-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_job_posted_at"
down_revision: Union[str, None] = "0003_resume_roles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_jobs_posted_at", "jobs", ["posted_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_posted_at", table_name="jobs")
    op.drop_column("jobs", "posted_at")
