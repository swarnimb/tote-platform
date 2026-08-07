"""gradeouts_single_junk

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-15
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("gradeouts", "totes_275_junk")
    op.drop_column("gradeouts", "totes_330_junk")
    op.add_column("gradeouts", sa.Column("junk", sa.Integer(), server_default="0"))


def downgrade() -> None:
    op.drop_column("gradeouts", "junk")
    op.add_column("gradeouts", sa.Column("totes_330_junk", sa.Integer(), server_default="0"))
    op.add_column("gradeouts", sa.Column("totes_275_junk", sa.Integer(), server_default="0"))
