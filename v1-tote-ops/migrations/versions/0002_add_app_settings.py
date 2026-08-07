"""add_app_settings

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-18
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.String(512), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
