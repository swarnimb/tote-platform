"""supplier_followup_weeks_is_active

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("suppliers", sa.Column("followup_weeks", sa.Integer(), server_default="4", nullable=False))
    op.add_column("suppliers", sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False))


def downgrade() -> None:
    op.drop_column("suppliers", "followup_weeks")
    op.drop_column("suppliers", "is_active")
