"""Comptes suspendus : leurs annonces sont masquées du site.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "comptes_suspendus",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("clerk_user_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comptes_suspendus_clerk_user_id", "comptes_suspendus", ["clerk_user_id"], unique=True)
    op.create_index("ix_comptes_suspendus_id", "comptes_suspendus", ["id"])


def downgrade():
    op.drop_index("ix_comptes_suspendus_id", table_name="comptes_suspendus")
    op.drop_index("ix_comptes_suspendus_clerk_user_id", table_name="comptes_suspendus")
    op.drop_table("comptes_suspendus")
