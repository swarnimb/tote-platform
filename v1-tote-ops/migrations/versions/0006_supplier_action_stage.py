"""supplier_action_stage

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("suppliers", "last_contacted_date", new_column_name="last_pickup_date")
    op.add_column("suppliers", sa.Column("last_action_stage", sa.String(32), nullable=True))
    op.add_column("suppliers", sa.Column("last_action_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("suppliers", "last_action_date")
    op.drop_column("suppliers", "last_action_stage")
    op.alter_column("suppliers", "last_pickup_date", new_column_name="last_contacted_date")
