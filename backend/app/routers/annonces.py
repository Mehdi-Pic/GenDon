"""Annonces : publication, consultation, cycle de vie (renouvellement, don), favoris, signalements."""
from datetime import datetime, timedelta, timezone
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel as PydanticBase, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import clerk, models, schemas
from ..auth import get_current_user_id, get_user_id_optionnel
from ..database import get_db
from ..outils import echapper_like, ip_client, limite_atteinte, verifier_rate_limit
from ..photos import supprimer_images_cloudinary, valider_images

router = APIRouter()


def verifier_proprietaire(annonce: models.Annonce, user_id: str) -> None:
    if not annonce.clerk_user_id or annonce.clerk_user_id != user_id:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas le propriétaire de cette annonce")


@router.post("/annonces", response_model=schemas.AnnonceResponse)
def créer_annonce(
    annonce: schemas.AnnonceCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    valider_images(db, user_id, annonce.images)
    db_annonce = models.Annonce(
        **annonce.model_dump(),
        pseudo=clerk.pseudo_clerk(user_id),
        statut="publiee",
        clerk_user_id=user_id,
    )
    db.add(db_annonce)
    db.commit()
    db.refresh(db_annonce)
    return db_annonce


@router.get("/stats")
def stats_publiques(db: Session = Depends(get_db)):
    """Chiffres affiches sur la page d'accueil : deux COUNT, pas de donnees personnelles."""
    return {
        "annonces": db.query(models.Annonce).filter(models.Annonce.donne_at == None).count(),
        "dons_realises": db.query(models.DonRealise).count(),
    }


LIMITE_PAR_PAGE = 18

@router.get("/annonces", response_model=schemas.AnnoncesPaginées)
def lister_annonces(
    categorie: str = None,
    recherche: str = None,
    quartier: str = None,
    tri: str = "recent",
    photos: bool = False,
    periode: str = None,
    page: int = 1,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id_optionnel),
):
    page = max(1, page)
    query = db.query(models.Annonce).filter(models.Annonce.donne_at == None)
    if categorie:
        query = query.filter(models.Annonce.categorie == categorie)
    if recherche:
        terme = f"%{echapper_like(recherche.strip()[:100])}%"
        query = query.filter(
            models.Annonce.titre.ilike(terme, escape="\\") | models.Annonce.description.ilike(terme, escape="\\")
        )
    if quartier:
        query = query.filter(models.Annonce.quartier == quartier)
    if photos:
        query = query.filter(func.cardinality(models.Annonce.images) > 0)
    if periode == "semaine":
        query = query.filter(models.Annonce.created_at >= datetime.now(timezone.utc) - timedelta(days=7))
    elif periode == "mois":
        query = query.filter(models.Annonce.created_at >= datetime.now(timezone.utc) - timedelta(days=30))
    # L'id departage les created_at identiques : sans lui, deux pages successives
    # pourraient repeter ou omettre une annonce
    if tri == "ancien":
        query = query.order_by(models.Annonce.created_at.asc(), models.Annonce.id.asc())
    else:
        query = query.order_by(models.Annonce.created_at.desc(), models.Annonce.id.desc())
    total = query.count()
    annonces = query.offset((page - 1) * LIMITE_PAR_PAGE).limit(LIMITE_PAR_PAGE).all()
    if user_id and annonces:
        ids = [a.id for a in annonces]
        favoris_ids = {
            aid for (aid,) in db.query(models.Favori.annonce_id)
            .filter(models.Favori.clerk_user_id == user_id, models.Favori.annonce_id.in_(ids))
            .all()
        }
        for a in annonces:
            a.est_favori = a.id in favoris_ids
            a.est_proprietaire = a.clerk_user_id == user_id
    return {"annonces": annonces, "total": total, "pages": ceil(total / LIMITE_PAR_PAGE) if total > 0 else 1, "page": page}


@router.get("/annonces/me", response_model=list[schemas.AnnonceResponse])
def get_mes_annonces(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    return (
        db.query(models.Annonce)
        .filter(models.Annonce.clerk_user_id == user_id)
        .order_by(models.Annonce.created_at.desc())
        .all()
    )


@router.get("/annonces/{annonce_id}", response_model=schemas.AnnonceResponse)
def get_annonce(
    annonce_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id_optionnel),
):
    annonce = db.query(models.Annonce).filter(models.Annonce.id == annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    annonce.est_proprietaire = bool(user_id and annonce.clerk_user_id == user_id)
    if user_id:
        annonce.est_favori = (
            db.query(models.Favori)
            .filter(models.Favori.clerk_user_id == user_id, models.Favori.annonce_id == annonce_id)
            .first()
            is not None
        )
    return annonce


@router.patch("/annonces/{annonce_id}", response_model=schemas.AnnonceResponse)
def modifier_annonce(
    annonce_id: int,
    data: schemas.AnnonceCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    annonce = db.query(models.Annonce).filter(models.Annonce.id == annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    verifier_proprietaire(annonce, user_id)
    if annonce.donne_at:
        raise HTTPException(status_code=400, detail="Cette annonce est cloturee")
    valider_images(db, user_id, data.images, deja_presentes=annonce.images or [])
    images_supprimees = set(annonce.images or []) - set(data.images or [])
    for key, value in data.model_dump().items():
        setattr(annonce, key, value)
    db.commit()
    db.refresh(annonce)
    # Après le commit : si l'enregistrement échoue, les photos ne sont pas perdues
    supprimer_images_cloudinary(list(images_supprimees))
    return annonce


# Une annonce vit 30 jours ; elle est renouvelable une fois passe ce delai d'anciennete
DUREE_VIE_JOURS = 30
RENOUVELABLE_APRES_JOURS = 7


@router.post("/annonces/{annonce_id}/renouveler", response_model=schemas.AnnonceResponse)
def renouveler_annonce(
    annonce_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Relance les 30 jours de visibilite d'une annonce (le proprietaire est toujours actif)."""
    annonce = db.query(models.Annonce).filter(models.Annonce.id == annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    verifier_proprietaire(annonce, user_id)
    if annonce.donne_at:
        raise HTTPException(status_code=400, detail="Cette annonce est cloturee")

    age_jours = (datetime.now(timezone.utc) - annonce.created_at).days
    if age_jours < RENOUVELABLE_APRES_JOURS:
        raise HTTPException(
            status_code=400,
            detail=f"Renouvelable dans {RENOUVELABLE_APRES_JOURS - age_jours} jour(s)",
        )

    annonce.created_at = datetime.now(timezone.utc)
    annonce.rappel_envoye = False  # le rappel J-3 pourra repartir sur le nouveau cycle
    db.commit()
    db.refresh(annonce)
    return annonce


@router.post("/annonces/{annonce_id}/donne", response_model=schemas.AnnonceResponse)
def declarer_don(
    annonce_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Le proprietaire declare l'objet donne : l'annonce quitte le site et le don est comptabilise."""
    annonce = db.query(models.Annonce).filter(models.Annonce.id == annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    verifier_proprietaire(annonce, user_id)
    # UPDATE conditionnel atomique : deux clics simultanés ne comptent qu'un seul don
    modifiees = (
        db.query(models.Annonce)
        .filter(models.Annonce.id == annonce_id, models.Annonce.donne_at == None)
        .update({models.Annonce.donne_at: datetime.now(timezone.utc)}, synchronize_session=False)
    )
    if not modifiees:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ce don est deja enregistre")
    # Trace independante de l'annonce : le compteur survit a la purge des 3 jours
    db.add(models.DonRealise(clerk_user_id=user_id, titre=annonce.titre[:100]))
    db.commit()
    db.refresh(annonce)
    return annonce


@router.post("/annonces/{annonce_id}/vue")
def compter_vue(
    annonce_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id_optionnel),
):
    """Appelé par le navigateur à l'affichage réel de la page (pas par les bots/prefetch/metadata)."""
    annonce = db.query(models.Annonce).filter(models.Annonce.id == annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    if user_id and annonce.clerk_user_id == user_id:
        return {"comptee": False}
    # Une vue par visiteur (compte, sinon IP) et par annonce toutes les 6 h : empêche de gonfler le compteur
    visiteur = user_id or ip_client(request)
    if limite_atteinte(visiteur, f"vue:{annonce_id}", maximum=1, fenetre_secondes=6 * 3600):
        return {"comptee": False}
    db.query(models.Annonce).filter(models.Annonce.id == annonce_id).update(
        {models.Annonce.vues: models.Annonce.vues + 1}
    )
    db.commit()
    return {"comptee": True}


@router.post("/annonces/{annonce_id}/favori")
def ajouter_favori(
    annonce_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    annonce = db.query(models.Annonce).filter(models.Annonce.id == annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    if annonce.clerk_user_id == user_id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas mettre votre propre annonce en favori")
    existe = (
        db.query(models.Favori)
        .filter(models.Favori.clerk_user_id == user_id, models.Favori.annonce_id == annonce_id)
        .first()
    )
    if not existe:
        db.add(models.Favori(clerk_user_id=user_id, annonce_id=annonce_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # double clic : le favori existe déjà
    return {"est_favori": True}


@router.delete("/annonces/{annonce_id}/favori")
def retirer_favori(
    annonce_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    db.query(models.Favori).filter(
        models.Favori.clerk_user_id == user_id, models.Favori.annonce_id == annonce_id
    ).delete()
    db.commit()
    return {"est_favori": False}


@router.get("/favoris", response_model=list[schemas.AnnonceResponse])
def mes_favoris(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    annonces = (
        db.query(models.Annonce)
        .join(models.Favori, models.Favori.annonce_id == models.Annonce.id)
        .filter(models.Favori.clerk_user_id == user_id)
        .order_by(models.Favori.created_at.desc())
        .all()
    )
    for a in annonces:
        a.est_favori = True
    return annonces


# ---------- Signalements (public, authentifié) ----------

class SignalementCreate(PydanticBase):
    raison: str = Field(min_length=3, max_length=500)


@router.post("/annonces/{annonce_id}/signaler")
def signaler_annonce(
    annonce_id: int,
    data: SignalementCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    verifier_rate_limit(user_id, "signalement", maximum=5, fenetre_secondes=3600)
    annonce = db.query(models.Annonce).filter(models.Annonce.id == annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    existe = (
        db.query(models.Signalement)
        .filter(models.Signalement.clerk_user_id == user_id, models.Signalement.annonce_id == annonce_id)
        .first()
    )
    if not existe:
        db.add(models.Signalement(annonce_id=annonce_id, clerk_user_id=user_id, raison=data.raison.strip()))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # double envoi : déjà enregistré
    return {"message": "Signalement enregistré"}

@router.delete("/annonces/{annonce_id}")
def supprimer_annonce(
    annonce_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    annonce = db.query(models.Annonce).filter(models.Annonce.id == annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    verifier_proprietaire(annonce, user_id)
    images = list(annonce.images or [])
    db.delete(annonce)
    db.commit()
    supprimer_images_cloudinary(images)
    return {"message": "Annonce supprimée"}

