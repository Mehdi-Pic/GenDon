from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List

CATEGORIES = [
    "Immobilier", "Vêtements", "Maison & Jardin",
    "Électronique", "Loisirs", "Sport", "Autres",
]

QUARTIERS = [
    "Les Grésillons", "Les Chevrins", "Les Agnettes", "Le Village",
    "Le Luth", "Le Fossé de l'Aumône", "Chandon - Brénu - Sévines",
    "République", "Cité Jardin",
]


class AnnonceCreate(BaseModel):
    titre: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)
    categorie: str
    quartier: str
    pseudo: str = Field(min_length=1, max_length=50)
    images: Optional[List[str]] = []
    statut: Optional[str] = "publiee"

    @field_validator("titre", "description", "pseudo")
    @classmethod
    def non_vide(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Ce champ ne peut pas être vide")
        return v

    @field_validator("categorie")
    @classmethod
    def categorie_valide(cls, v):
        if v not in CATEGORIES:
            raise ValueError("Catégorie invalide")
        return v

    @field_validator("quartier")
    @classmethod
    def quartier_valide(cls, v):
        if v not in QUARTIERS:
            raise ValueError("Quartier invalide")
        return v

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
    est_proprietaire: bool = False
    est_favori: bool = False
    vues: int = 0

    class Config:
        from_attributes = True


class AnnoncesPaginées(BaseModel):
    annonces: List[AnnonceResponse]
    total: int
    pages: int
    page: int
