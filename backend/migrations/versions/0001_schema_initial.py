"""Schéma initial : la base telle qu'elle existait avant Alembic.

Une base de production déjà en place n'exécute pas cette migration : app/migrations.py
la met à niveau puis la marque directement comme appliquée (stamp).

Revision ID: 0001
Revises: 
Create Date: 2026-10-03 00:43:53.486191
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('actions_moderation',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('clerk_user_id', sa.String(length=100), nullable=False),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('details', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_actions_moderation_id'), 'actions_moderation', ['id'], unique=False)
    op.create_table('annonces',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('titre', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('categorie', sa.String(length=50), nullable=False),
    sa.Column('quartier', sa.String(length=100), nullable=False),
    sa.Column('pseudo', sa.String(length=50), nullable=False),
    sa.Column('images', sa.ARRAY(sa.String()), nullable=True),
    sa.Column('statut', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('clerk_user_id', sa.String(length=100), nullable=True),
    sa.Column('vues', sa.Integer(), server_default='0', nullable=False),
    sa.Column('rappel_envoye', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('donne_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_annonces_id'), 'annonces', ['id'], unique=False)
    op.create_table('desabonnements_newsletter',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('clerk_user_id', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_desabonnements_newsletter_clerk_user_id'), 'desabonnements_newsletter', ['clerk_user_id'], unique=True)
    op.create_index(op.f('ix_desabonnements_newsletter_id'), 'desabonnements_newsletter', ['id'], unique=False)
    op.create_table('dons_realises',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('clerk_user_id', sa.String(length=100), nullable=True),
    sa.Column('titre', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dons_realises_id'), 'dons_realises', ['id'], unique=False)
    op.create_table('images_uploadees',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('url', sa.String(length=500), nullable=False),
    sa.Column('public_id', sa.String(length=300), nullable=False),
    sa.Column('clerk_user_id', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_images_uploadees_clerk_user_id'), 'images_uploadees', ['clerk_user_id'], unique=False)
    op.create_index(op.f('ix_images_uploadees_id'), 'images_uploadees', ['id'], unique=False)
    op.create_index(op.f('ix_images_uploadees_url'), 'images_uploadees', ['url'], unique=True)
    op.create_table('roles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('clerk_user_id', sa.String(length=100), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roles_clerk_user_id'), 'roles', ['clerk_user_id'], unique=True)
    op.create_index(op.f('ix_roles_id'), 'roles', ['id'], unique=False)
    op.create_table('conversations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('annonce_id', sa.Integer(), nullable=False),
    sa.Column('donneur_id', sa.String(length=100), nullable=False),
    sa.Column('demandeur_id', sa.String(length=100), nullable=False),
    sa.Column('donneur_pseudo', sa.String(length=50), nullable=False),
    sa.Column('demandeur_pseudo', sa.String(length=50), nullable=False),
    sa.Column('donneur_actif', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('demandeur_actif', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('dernier_message_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('notif_donneur_envoyee', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('notif_demandeur_envoyee', sa.Boolean(), server_default='false', nullable=False),
    sa.ForeignKeyConstraint(['annonce_id'], ['annonces.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('annonce_id', 'demandeur_id', name='uq_conversation_annonce_demandeur')
    )
    op.create_index(op.f('ix_conversations_demandeur_id'), 'conversations', ['demandeur_id'], unique=False)
    op.create_index(op.f('ix_conversations_donneur_id'), 'conversations', ['donneur_id'], unique=False)
    op.create_index(op.f('ix_conversations_id'), 'conversations', ['id'], unique=False)
    op.create_table('favoris',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('clerk_user_id', sa.String(length=100), nullable=False),
    sa.Column('annonce_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['annonce_id'], ['annonces.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('clerk_user_id', 'annonce_id', name='uq_favori_user_annonce')
    )
    op.create_index(op.f('ix_favoris_clerk_user_id'), 'favoris', ['clerk_user_id'], unique=False)
    op.create_index(op.f('ix_favoris_id'), 'favoris', ['id'], unique=False)
    op.create_table('signalements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('annonce_id', sa.Integer(), nullable=False),
    sa.Column('clerk_user_id', sa.String(length=100), nullable=False),
    sa.Column('raison', sa.Text(), nullable=False),
    sa.Column('traite', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['annonce_id'], ['annonces.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('clerk_user_id', 'annonce_id', name='uq_signalement_user_annonce')
    )
    op.create_index(op.f('ix_signalements_id'), 'signalements', ['id'], unique=False)
    op.create_table('messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('conversation_id', sa.Integer(), nullable=False),
    sa.Column('auteur_id', sa.String(length=100), nullable=False),
    sa.Column('contenu', sa.String(length=2000), nullable=False),
    sa.Column('lu', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('systeme', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_messages_id'), 'messages', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_messages_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_conversation_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_index(op.f('ix_signalements_id'), table_name='signalements')
    op.drop_table('signalements')
    op.drop_index(op.f('ix_favoris_id'), table_name='favoris')
    op.drop_index(op.f('ix_favoris_clerk_user_id'), table_name='favoris')
    op.drop_table('favoris')
    op.drop_index(op.f('ix_conversations_id'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_donneur_id'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_demandeur_id'), table_name='conversations')
    op.drop_table('conversations')
    op.drop_index(op.f('ix_roles_id'), table_name='roles')
    op.drop_index(op.f('ix_roles_clerk_user_id'), table_name='roles')
    op.drop_table('roles')
    op.drop_index(op.f('ix_images_uploadees_url'), table_name='images_uploadees')
    op.drop_index(op.f('ix_images_uploadees_id'), table_name='images_uploadees')
    op.drop_index(op.f('ix_images_uploadees_clerk_user_id'), table_name='images_uploadees')
    op.drop_table('images_uploadees')
    op.drop_index(op.f('ix_dons_realises_id'), table_name='dons_realises')
    op.drop_table('dons_realises')
    op.drop_index(op.f('ix_desabonnements_newsletter_id'), table_name='desabonnements_newsletter')
    op.drop_index(op.f('ix_desabonnements_newsletter_clerk_user_id'), table_name='desabonnements_newsletter')
    op.drop_table('desabonnements_newsletter')
    op.drop_index(op.f('ix_annonces_id'), table_name='annonces')
    op.drop_table('annonces')
    op.drop_index(op.f('ix_actions_moderation_id'), table_name='actions_moderation')
    op.drop_table('actions_moderation')
