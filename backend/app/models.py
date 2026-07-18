from sqlalchemy import Column, Integer, String, Text, DateTime, ARRAY, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from .database import Base

class Annonce(Base):
    __tablename__ = "annonces"

    id = Column(Integer, primary_key=True, index=True)
    titre = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    categorie = Column(String(50), nullable=False)
    quartier = Column(String(100), nullable=False)
    pseudo = Column(String(50), nullable=False)
    images = Column(ARRAY(String), nullable=True, default=[])
    statut = Column(String(20), nullable=False, default="publiee")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    clerk_user_id = Column(String(100), nullable=True)
    vues = Column(Integer, nullable=False, default=0, server_default="0")
    rappel_envoye = Column(Boolean, nullable=False, default=False, server_default="false")


class Favori(Base):
    __tablename__ = "favoris"

    id = Column(Integer, primary_key=True, index=True)
    clerk_user_id = Column(String(100), nullable=False, index=True)
    annonce_id = Column(Integer, ForeignKey("annonces.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("clerk_user_id", "annonce_id", name="uq_favori_user_annonce"),)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    clerk_user_id = Column(String(100), nullable=False, unique=True, index=True)
    role = Column(String(20), nullable=False)  # "admin" ou "moderateur"
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Signalement(Base):
    __tablename__ = "signalements"

    id = Column(Integer, primary_key=True, index=True)
    annonce_id = Column(Integer, ForeignKey("annonces.id", ondelete="CASCADE"), nullable=False)
    clerk_user_id = Column(String(100), nullable=False)
    raison = Column(String(500), nullable=False)
    traite = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("clerk_user_id", "annonce_id", name="uq_signalement_user_annonce"),)


class ActionModeration(Base):
    __tablename__ = "actions_moderation"

    id = Column(Integer, primary_key=True, index=True)
    clerk_user_id = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    annonce_id = Column(Integer, ForeignKey("annonces.id", ondelete="CASCADE"), nullable=False)
    donneur_id = Column(String(100), nullable=False, index=True)
    demandeur_id = Column(String(100), nullable=False, index=True)
    donneur_pseudo = Column(String(50), nullable=False, default="")
    demandeur_pseudo = Column(String(50), nullable=False, default="")
    donneur_actif = Column(Boolean, nullable=False, default=True, server_default="true")
    demandeur_actif = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    dernier_message_at = Column(DateTime(timezone=True), server_default=func.now())
    # Email de notification déjà envoyé pour du non-lu : évite de spammer à chaque message
    notif_donneur_envoyee = Column(Boolean, nullable=False, default=False, server_default="false")
    notif_demandeur_envoyee = Column(Boolean, nullable=False, default=False, server_default="false")

    __table_args__ = (UniqueConstraint("annonce_id", "demandeur_id", name="uq_conversation_annonce_demandeur"),)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    auteur_id = Column(String(100), nullable=False)
    contenu = Column(String(2000), nullable=False)
    lu = Column(Boolean, nullable=False, default=False, server_default="false")
    systeme = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())