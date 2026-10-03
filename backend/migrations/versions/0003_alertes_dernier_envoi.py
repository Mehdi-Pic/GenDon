"""Alertes : date du dernier email envoyé (plafond d'un email par heure et par personne).

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("alertes", sa.Column("dernier_envoi_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("alertes", "dernier_envoi_at")
