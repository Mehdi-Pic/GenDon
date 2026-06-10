from sqlalchemy import Column, Integer, String, Text, DateTime, ARRAY
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