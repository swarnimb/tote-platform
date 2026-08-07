"""drop_pickups_table

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-15
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("idx_pickups_status", "pickups")
    op.drop_index("idx_pickups_supplier_id", "pickups")
    op.drop_table("pickups")
    sa.Enum(name="pickup_status").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    op.create_table(
        "pickups",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("supplier_id", sa.String(36), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("request_date", sa.Date(), nullable=False),
        sa.Column("pickup_date", sa.Date()),
        sa.Column("tote_275_count", sa.Integer(), server_default="0"),
        sa.Column("tote_330_count", sa.Integer(), server_default="0"),
        sa.Column("is_hazmat", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "status",
            sa.Enum("contacted", "confirmed", "completed", "cancelled", name="pickup_status"),
            nullable=False,
            server_default="contacted",
        ),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_pickups_supplier_id", "pickups", ["supplier_id"])
    op.create_index("idx_pickups_status", "pickups", ["status"])
