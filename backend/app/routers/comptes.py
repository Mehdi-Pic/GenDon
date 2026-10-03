"""Comptes : synchronisation avec Clerk (webhook), suppression des données, préférences email."""
import anyio.to_thread
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel as PydanticBase
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from svix.webhooks import Webhook, WebhookVerificationError

from .. import clerk, emails, models
from ..auth import get_current_user_id
from ..database import SessionLocal, get_db
from ..photos import supprimer_images_cloudinary

router = APIRouter()


def purger_donnees_utilisateur(db: Session, clerk_user_id: str):
    """Efface toutes les données GenDon liées à un utilisateur (RGPD / suppression de compte)."""
    conversations = (
        db.query(models.Conversation)
        .filter(
            (models.Conversation.donneur_id == clerk_user_id)
            | (models.Conversation.demandeur_id == clerk_user_id)
        )
        .all()
    )
    # Avant les annonces : leur suppression emporte déjà une partie des conversations en cascade
    for conv in conversations:
        db.delete(conv)  # messages liés partent en cascade
    db.flush()
    annonces = db.query(models.Annonce).filter(models.Annonce.clerk_user_id == clerk_user_id).all()
    images = []
    for annonce in annonces:
        images.extend(annonce.images or [])
        db.delete(annonce)  # favoris et signalements liés partent en cascade
    # Images envoyées mais jamais publiées
    images.extend(
        url for (url,) in db.query(models.ImageUploadee.url)
        .filter(models.ImageUploadee.clerk_user_id == clerk_user_id).all()
    )
    db.query(models.ImageUploadee).filter(models.ImageUploadee.clerk_user_id == clerk_user_id).delete()
    # Le compteur global de dons est conservé, mais anonymisé
    db.query(models.DonRealise).filter(models.DonRealise.clerk_user_id == clerk_user_id).update(
        {models.DonRealise.clerk_user_id: None, models.DonRealise.titre: None}
    )
    db.query(models.Favori).filter(models.Favori.clerk_user_id == clerk_user_id).delete()
    db.query(models.Signalement).filter(models.Signalement.clerk_user_id == clerk_user_id).delete()
    db.query(models.Role).filter(models.Role.clerk_user_id == clerk_user_id).delete()
    db.query(models.DesabonnementNewsletter).filter(
        models.DesabonnementNewsletter.clerk_user_id == clerk_user_id
    ).delete()
    db.commit()
    supprimer_images_cloudinary(list(set(images)))



def mettre_a_jour_pseudo(db: Session, clerk_user_id: str, pseudo: str):
    """Répercute un changement de nom d'utilisateur Clerk sur les annonces et conversations."""
    db.query(models.Annonce).filter(models.Annonce.clerk_user_id == clerk_user_id).update(
        {models.Annonce.pseudo: pseudo}
    )
    db.query(models.Conversation).filter(models.Conversation.donneur_id == clerk_user_id).update(
        {models.Conversation.donneur_pseudo: pseudo}
    )
    db.query(models.Conversation).filter(models.Conversation.demandeur_id == clerk_user_id).update(
        {models.Conversation.demandeur_pseudo: pseudo}
    )
    db.commit()


def _traiter_evenement_clerk(evenement: dict):
    """Exécuté dans un thread avec sa propre session : le webhook est async (lecture du corps brut)."""
    type_evenement = evenement.get("type")
    data = evenement.get("data") or {}
    uid = data.get("id")
    if not uid:
        return
    db = SessionLocal()
    try:
        if type_evenement == "user.deleted":
            purger_donnees_utilisateur(db, uid)
        elif type_evenement == "user.updated":
            mettre_a_jour_pseudo(db, uid, clerk.pseudo_depuis_clerk(data))
    finally:
        db.close()


@router.post("/webhooks/clerk")
async def webhook_clerk(request: Request):
    secret = os.getenv("CLERK_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="Webhook non configuré")

    payload = await request.body()
    headers = {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }
    try:
        evenement = Webhook(secret).verify(payload, headers)
    except WebhookVerificationError:
        raise HTTPException(status_code=401, detail="Signature invalide")

    # Accès base et Cloudinary synchrones : hors de l'event loop
    await anyio.to_thread.run_sync(_traiter_evenement_clerk, evenement)
    return {"recu": True}


# ---------- Préférence newsletter (depuis Mon profil) ----------

class PreferenceNewsletter(PydanticBase):
    abonne: bool


@router.get("/newsletter/moi")
def lire_preference_newsletter(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    desabonne = (
        db.query(models.DesabonnementNewsletter)
        .filter(models.DesabonnementNewsletter.clerk_user_id == user_id)
        .first()
    )
    return {"abonne": desabonne is None}


@router.put("/newsletter/moi")
def changer_preference_newsletter(
    data: PreferenceNewsletter,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    requete = db.query(models.DesabonnementNewsletter).filter(
        models.DesabonnementNewsletter.clerk_user_id == user_id
    )
    if data.abonne:
        requete.delete()
        db.commit()
    elif not requete.first():
        db.add(models.DesabonnementNewsletter(clerk_user_id=user_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # double clic : déjà désabonné
    return {"abonne": data.abonne}


# ---------- Désabonnement newsletter (public, via lien signé dans l'email) ----------

class DesabonnementRequete(PydanticBase):
    token: str


@router.post("/newsletter/desabonnement")
def desabonner_newsletter(data: DesabonnementRequete, db: Session = Depends(get_db)):
    if not emails.cle_desabonnement():
        raise HTTPException(status_code=503, detail="Désabonnement momentanément indisponible")
    uid = emails.verifier_token_desabonnement(data.token)
    if not uid:
        raise HTTPException(status_code=400, detail="Lien de désabonnement invalide ou expiré")
    existe = (
        db.query(models.DesabonnementNewsletter)
        .filter(models.DesabonnementNewsletter.clerk_user_id == uid)
        .first()
    )
    if not existe:
        db.add(models.DesabonnementNewsletter(clerk_user_id=uid))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # double clic : déjà désabonné
    return {"ok": True}

