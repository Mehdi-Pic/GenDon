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