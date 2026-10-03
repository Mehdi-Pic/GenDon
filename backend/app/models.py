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
    # Rempli quand le proprietaire declare l'objet donne : l'annonce est alors retiree du site sous 3 jours
    donne_at = Column(DateTime(timezone=True), nullable=True)
    # statut "reservee" : le donneur a promis l'objet à ce demandeur (identifiant Clerk)
    reserve_pour = Column(String(100), nullable=True)


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
    """Signalement d'une annonce (annonce_id) ou d'une conversation (conversation_id)."""
    __tablename__ = "signalements"

    id = Column(Integer, primary_key=True, index=True)
    annonce_id = Column(Integer, ForeignKey("annonces.id", ondelete="CASCADE"), nullable=True)
    # SET NULL : le motif reste lisible par l'équipe même si la conversation est supprimée
    conversation_id = Column(
        Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    clerk_user_id = Column(String(100), nullable=False)
    raison = Column(Text, nullable=False)
    traite = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("clerk_user_id", "annonce_id", name="uq_signalement_user_annonce"),
        UniqueConstraint("clerk_user_id", "conversation_id", name="uq_signalement_user_conversation"),
    )


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
    # SET NULL : la conversation survit au retrait de l'annonce (purge, suppression, don),
    # le temps de finaliser la remise. Elle est purgée ensuite après inactivité.
    annonce_id = Column(Integer, ForeignKey("annonces.id", ondelete="SET NULL"), nullable=True)
    # Titre copié à la création (et tenu à jour) : reste affiché une fois l'annonce retirée
    annonce_titre = Column(String(100), nullable=False, default="", server_default="")
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

class DesabonnementNewsletter(Base):
    __tablename__ = "desabonnements_newsletter"

    id = Column(Integer, primary_key=True, index=True)
    clerk_user_id = Column(String(100), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DonRealise(Base):
    """Trace durable d'un don abouti : survit à la suppression de l'annonce (compteur global)."""
    __tablename__ = "dons_realises"

    id = Column(Integer, primary_key=True, index=True)
    clerk_user_id = Column(String(100), nullable=True)
    titre = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ImageUploadee(Base):
    """Registre des images envoyees via /upload : une annonce ne peut referencer que les images
    de son auteur, et les images jamais publiees sont nettoyees automatiquement."""
    __tablename__ = "images_uploadees"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), nullable=False, unique=True, index=True)
    public_id = Column(String(300), nullable=False)
    clerk_user_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DesabonnementMessages(Base):
    """Utilisateurs qui ne veulent plus d'email « nouveau message »."""
    __tablename__ = "desabonnements_messages"

    id = Column(Integer, primary_key=True, index=True)
    clerk_user_id = Column(String(100), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Alerte(Base):
    """Recherche enregistrée : un email signale les nouvelles annonces qui y correspondent."""
    __tablename__ = "alertes"

    id = Column(Integer, primary_key=True, index=True)
    clerk_user_id = Column(String(100), nullable=False, index=True)
    recherche = Column(String(100), nullable=True)
    categorie = Column(String(50), nullable=True)
    quartier = Column(String(100), nullable=True)
    # Les annonces publiées avant cette date ont déjà été signalées (ou précèdent l'alerte)
    verifie_jusqu_a = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Dernier email d'alerte envoyé à cet utilisateur (même valeur sur toutes ses alertes) : plafond horaire
    dernier_envoi_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CompteSuspendu(Base):
    """Comptes suspendus (bannis chez Clerk) : leurs annonces sont masquées du site."""
    __tablename__ = "comptes_suspendus"

    id = Column(Integer, primary_key=True, index=True)
    clerk_user_id = Column(String(100), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
