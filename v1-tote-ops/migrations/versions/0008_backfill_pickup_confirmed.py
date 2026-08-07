"""backfill_pickup_confirmed

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-19
"""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    suppliers = conn.execute(
        sa.text(
            "SELECT id FROM suppliers "
            "WHERE last_action_stage = 'pickup_confirmed' AND is_deleted = FALSE"
        )
    ).fetchall()

    for row in suppliers:
        existing = conn.execute(
            sa.text("SELECT id FROM pickups WHERE supplier_id = :sid LIMIT 1"),
            {"sid": row.id},
        ).fetchone()
        if existing:
            continue
        conn.execute(
            sa.text(
                "INSERT INTO pickups (id, supplier_id, status) "
                "VALUES (:id, :sid, 'confirmed')"
            ),
            {"id": str(uuid.uuid4()), "sid": row.id},
        )


def downgrade() -> None:
    pass
