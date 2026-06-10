from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List

class AnnonceCreate(BaseModel):
    titre: str
    description: str
    categorie: str
    quartier: str
    pseudo: str
    images: Optional[List[str]] = []
    statut: Optional[str] = "publiee"

    @field_validator("images")
    @classmethod
    def max_cinq_images(cls, v):
        if v and len(v) > 5:
            raise ValueError("Maximum 5 photos par annonce")
        return v

class AnnonceResponse(BaseModel):
    id: int
    titre: str
    description: str
    categorie: str
    quartier: str
    pseudo: str
    images: Optional[List[str]]
    statut: str
    created_at: datetime

    class Config:
        from_attributes = True


class AnnoncesPaginées(BaseModel):
    annonces: List[AnnonceResponse]
    total: int
    pages: int
    page: int