"""gradeouts_remove_pickup_pdf

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-15
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_gradeouts_pickup_id", "gradeouts", type_="unique")
    op.drop_constraint("gradeouts_pickup_id_fkey", "gradeouts", type_="foreignkey")
    op.drop_column("gradeouts", "pickup_id")
    op.drop_column("gradeouts", "pdf_storage_path")


def downgrade() -> None:
    op.add_column("gradeouts", sa.Column("pdf_storage_path", sa.Text()))
    op.add_column(
        "gradeouts",
        sa.Column("pickup_id", sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        "gradeouts_pickup_id_fkey", "gradeouts", "pickups", ["pickup_id"], ["id"]
    )
    op.create_unique_constraint("uq_gradeouts_pickup_id", "gradeouts", ["pickup_id"])
