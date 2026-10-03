"""Alertes de recherche : l'utilisateur enregistre des critères, un email lui signale les nouveaux dons."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel as PydanticBase, Field, field_validator
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user_id
from ..database import get_db

router = APIRouter()

MAX_ALERTES_PAR_UTILISATEUR = 10


class AlerteCreate(PydanticBase):
    recherche: Optional[str] = Field(default=None, max_length=100)
    categorie: Optional[str] = None
    quartier: Optional[str] = None

    @field_validator("recherche")
    @classmethod
    def nettoyer(cls, v):
        v = " ".join((v or "").split())
        return v or None

    @field_validator("categorie")
    @classmethod
    def categorie_valide(cls, v):
        if v and v not in schemas.CATEGORIES:
            raise ValueError("Catégorie invalide")
        return v or None

    @field_validator("quartier")
    @classmethod
    def quartier_valide(cls, v):
        if v and v not in schemas.QUARTIERS:
            raise ValueError("Quartier invalide")
        return v or None


def _vers_json(a: models.Alerte) -> dict:
    return {
        "id": a.id, "recherche": a.recherche, "categorie": a.categorie,
        "quartier": a.quartier, "created_at": a.created_at,
    }


@router.get("/alertes")
def mes_alertes(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    alertes = (
        db.query(models.Alerte)
        .filter(models.Alerte.clerk_user_id == user_id)
        .order_by(models.Alerte.created_at.desc())
        .all()
    )
    return [_vers_json(a) for a in alertes]


@router.post("/alertes")
def creer_alerte(data: AlerteCreate, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    if not (data.recherche or data.categorie or data.quartier):
        raise HTTPException(status_code=400, detail="Indiquez au moins un mot-clé, une catégorie ou un quartier")
    alertes = db.query(models.Alerte).filter(models.Alerte.clerk_user_id == user_id).all()
    for a in alertes:
        if (a.recherche or "").lower() == (data.recherche or "").lower() and a.categorie == data.categorie \
                and a.quartier == data.quartier:
            return _vers_json(a)  # déjà enregistrée
    if len(alertes) >= MAX_ALERTES_PAR_UTILISATEUR:
        raise HTTPException(
            status_code=400, detail=f"Maximum {MAX_ALERTES_PAR_UTILISATEUR} alertes : supprimez-en une d'abord"
        )
    alerte = models.Alerte(
        clerk_user_id=user_id, recherche=data.recherche, categorie=data.categorie, quartier=data.quartier
    )
    db.add(alerte)
    db.commit()
    db.refresh(alerte)
    return _vers_json(alerte)


@router.delete("/alertes/{alerte_id}")
def supprimer_alerte(alerte_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    db.query(models.Alerte).filter(models.Alerte.id == alerte_id, models.Alerte.clerk_user_id == user_id).delete()
    db.commit()
    return {"ok": True}
