"""add role labels and drive url to resumes

Revision ID: 0003_resume_roles
Revises: 0002_app_mode
Create Date: 2026-11-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_resume_roles"
down_revision: Union[str, None] = "0002_app_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("drive_url", sa.String(length=1024), nullable=True))
    op.add_column(
        "resumes",
        sa.Column("role_labels", postgresql.ARRAY(sa.String()), server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("resumes", "role_labels")
    op.drop_column("resumes", "drive_url")
