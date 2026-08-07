"""fix_backfill_pickup_dates

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE pickups
            SET created_at = s.last_action_date
            FROM suppliers s
            WHERE pickups.supplier_id = s.id
              AND s.last_action_stage = 'pickup_confirmed'
              AND s.last_action_date IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    pass
