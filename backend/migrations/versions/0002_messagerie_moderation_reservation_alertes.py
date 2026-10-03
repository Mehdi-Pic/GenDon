"""Conversations indépendantes des annonces, signalements de conversation, réservation,
alertes de recherche, préférence des emails de messages.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _cle_etrangere(table, colonne):
    """Nom réel de la clé étrangère (une base ancienne peut l'avoir nommée autrement)."""
    for fk in sa.inspect(op.get_bind()).get_foreign_keys(table):
        if fk["constrained_columns"] == [colonne]:
            return fk["name"]
    return None


def upgrade():
    op.create_table(
        "alertes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("clerk_user_id", sa.String(length=100), nullable=False),
        sa.Column("recherche", sa.String(length=100), nullable=True),
        sa.Column("categorie", sa.String(length=50), nullable=True),
        sa.Column("quartier", sa.String(length=100), nullable=True),
        sa.Column("verifie_jusqu_a", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alertes_clerk_user_id", "alertes", ["clerk_user_id"])
    op.create_index("ix_alertes_id", "alertes", ["id"])
    op.create_table(
        "desabonnements_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("clerk_user_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_desabonnements_messages_clerk_user_id", "desabonnements_messages", ["clerk_user_id"], unique=True)
    op.create_index("ix_desabonnements_messages_id", "desabonnements_messages", ["id"])

    op.add_column("annonces", sa.Column("reserve_pour", sa.String(length=100), nullable=True))

    # Conversations : survivent au retrait de l'annonce, avec une copie de son titre
    op.add_column("conversations", sa.Column("annonce_titre", sa.String(length=100), server_default="", nullable=False))
    op.execute(
        "UPDATE conversations c SET annonce_titre = a.titre FROM annonces a WHERE a.id = c.annonce_id"
    )
    op.alter_column("conversations", "annonce_id", existing_type=sa.Integer(), nullable=True)
    ancienne = _cle_etrangere("conversations", "annonce_id")
    if ancienne:
        op.drop_constraint(ancienne, "conversations", type_="foreignkey")
    op.create_foreign_key(
        "conversations_annonce_id_fkey", "conversations", "annonces", ["annonce_id"], ["id"], ondelete="SET NULL"
    )

    # Signalements : une conversation signalée est désormais rattachée à la conversation elle-même
    op.add_column("signalements", sa.Column("conversation_id", sa.Integer(), nullable=True))
    op.alter_column("signalements", "annonce_id", existing_type=sa.Integer(), nullable=True)
    op.create_index("ix_signalements_conversation_id", "signalements", ["conversation_id"])
    op.create_foreign_key(
        "signalements_conversation_id_fkey", "signalements", "conversations",
        ["conversation_id"], ["id"], ondelete="SET NULL",
    )
    # Reprise des anciens signalements « [Conversation #12] motif » (un seul par utilisateur et conversation)
    op.execute(
        r"""
        UPDATE signalements s SET conversation_id = sub.cid
        FROM (
            SELECT DISTINCT ON (s2.clerk_user_id, c.id) s2.id AS sid, c.id AS cid
            FROM signalements s2
            JOIN conversations c ON c.id = substring(s2.raison from '^\[Conversation #(\d+)\]')::int
            ORDER BY s2.clerk_user_id, c.id, s2.id
        ) sub
        WHERE s.id = sub.sid
        """
    )
    op.create_unique_constraint(
        "uq_signalement_user_conversation", "signalements", ["clerk_user_id", "conversation_id"]
    )


def downgrade():
    op.drop_constraint("uq_signalement_user_conversation", "signalements", type_="unique")
    op.drop_constraint("signalements_conversation_id_fkey", "signalements", type_="foreignkey")
    op.drop_index("ix_signalements_conversation_id", table_name="signalements")
    op.execute("DELETE FROM signalements WHERE annonce_id IS NULL")
    op.alter_column("signalements", "annonce_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("signalements", "conversation_id")
    op.drop_constraint("conversations_annonce_id_fkey", "conversations", type_="foreignkey")
    op.execute("DELETE FROM conversations WHERE annonce_id IS NULL")
    op.create_foreign_key(
        "conversations_annonce_id_fkey", "conversations", "annonces", ["annonce_id"], ["id"], ondelete="CASCADE"
    )
    op.alter_column("conversations", "annonce_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("conversations", "annonce_titre")
    op.drop_column("annonces", "reserve_pour")
    op.drop_index("ix_desabonnements_messages_id", table_name="desabonnements_messages")
    op.drop_index("ix_desabonnements_messages_clerk_user_id", table_name="desabonnements_messages")
    op.drop_table("desabonnements_messages")
    op.drop_index("ix_alertes_id", table_name="alertes")
    op.drop_index("ix_alertes_clerk_user_id", table_name="alertes")
    op.drop_table("alertes")
