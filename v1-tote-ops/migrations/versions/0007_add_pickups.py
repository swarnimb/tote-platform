"""add_pickups

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pickups",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("supplier_id", sa.String(36), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="confirmed"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.add_column(
        "gradeouts",
        sa.Column("pickup_id", sa.String(36), sa.ForeignKey("pickups.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("gradeouts", "pickup_id")
    op.drop_table("pickups")
