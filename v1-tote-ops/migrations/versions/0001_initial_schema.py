"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-03-15
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column("email", sa.String(255)),
        sa.Column("bol_email", sa.String(255)),
        sa.Column("bol_same_as_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("industry", sa.String(255)),
        sa.Column("tote_types", sa.String(20)),
        sa.Column("average_quantity_275", sa.String(50)),
        sa.Column("average_quantity_330", sa.String(50)),
        sa.Column("last_contacted_date", sa.Date()),
        sa.Column("working_hours", sa.String(255)),
        sa.Column("is_hazmat", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("warnings", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_suppliers_is_deleted", "suppliers", ["is_deleted"])

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

    op.create_table(
        "gradeouts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("pickup_id", sa.String(36), sa.ForeignKey("pickups.id"), nullable=False, unique=True),
        sa.Column("supplier_id", sa.String(36), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("date_received", sa.Date(), nullable=False),
        sa.Column("totes_275_good_washable", sa.Integer(), server_default="0"),
        sa.Column("totes_275_good_cage", sa.Integer(), server_default="0"),
        sa.Column("totes_275_total_usable", sa.Integer(), server_default="0"),
        sa.Column("totes_275_junk", sa.Integer(), server_default="0"),
        sa.Column("totes_330_good_washable", sa.Integer(), server_default="0"),
        sa.Column("totes_330_good_cage", sa.Integer(), server_default="0"),
        sa.Column("totes_330_total_usable", sa.Integer(), server_default="0"),
        sa.Column("totes_330_junk", sa.Integer(), server_default="0"),
        sa.Column("pdf_storage_path", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("pickup_id", name="uq_gradeouts_pickup_id"),
    )
    op.create_index("idx_gradeouts_supplier_id", "gradeouts", ["supplier_id"])
    op.create_index("idx_gradeouts_date_received", "gradeouts", ["date_received"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("month", sa.Date(), nullable=False, unique=True),
        sa.Column("gradeout_count", sa.Integer(), nullable=False),
        sa.Column("total_usable_275", sa.Integer(), nullable=False),
        sa.Column("total_usable_330", sa.Integer(), nullable=False),
        sa.Column("total_revenue", sa.Numeric(10, 2), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("sent_at", sa.DateTime()),
        sa.UniqueConstraint("month", name="uq_invoices_month"),
    )
    op.create_index("idx_invoices_month", "invoices", ["month"])

    op.create_table(
        "leads",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255)),
        sa.Column("industry", sa.String(255)),
        sa.Column("contact_name", sa.String(255)),
        sa.Column("contact_phone", sa.String(50)),
        sa.Column("contact_email", sa.String(255)),
        sa.Column(
            "outreach_status",
            sa.Enum(
                "research", "contacted", "responded", "not_interested", "active_supplier",
                name="lead_status",
            ),
            nullable=False,
            server_default="research",
        ),
        sa.Column("last_contact_date", sa.Date()),
        sa.Column("potential_volume", sa.String(255)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_leads_outreach_status", "leads", ["outreach_status"])


def downgrade() -> None:
    op.drop_index("idx_leads_outreach_status", "leads")
    op.drop_table("leads")
    op.drop_index("idx_invoices_month", "invoices")
    op.drop_table("invoices")
    op.drop_index("idx_gradeouts_date_received", "gradeouts")
    op.drop_index("idx_gradeouts_supplier_id", "gradeouts")
    op.drop_table("gradeouts")
    op.drop_index("idx_pickups_status", "pickups")
    op.drop_index("idx_pickups_supplier_id", "pickups")
    op.drop_table("pickups")
    op.drop_index("idx_suppliers_is_deleted", "suppliers")
    op.drop_table("suppliers")
    sa.Enum(name="pickup_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="lead_status").drop(op.get_bind(), checkfirst=True)
