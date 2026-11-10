"""Index sur les colonnes les plus filtrées : annonces par auteur et par date, conversations par annonce.

Revision ID: 0005
Revises: 0004
"""
from alembic import op


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_annonces_clerk_user_id", "annonces", ["clerk_user_id"])
    op.create_index("ix_annonces_created_at", "annonces", ["created_at"])
    op.create_index("ix_conversations_annonce_id", "conversations", ["annonce_id"])


def downgrade():
    op.drop_index("ix_conversations_annonce_id", table_name="conversations")
    op.drop_index("ix_annonces_created_at", table_name="annonces")
    op.drop_index("ix_annonces_clerk_user_id", table_name="annonces")
