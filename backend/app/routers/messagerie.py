"""Messagerie entre donneur et demandeur."""
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel as PydanticBase, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import clerk, emails, models
from ..auth import get_current_user_id
from ..database import get_db
from ..outils import verifier_rate_limit

router = APIRouter()


def _est_participant(conv, user_id: str) -> bool:
    return user_id in (conv.donneur_id, conv.demandeur_id)


class ConversationCreate(PydanticBase):
    annonce_id: int


class MessageCreate(PydanticBase):
    contenu: str = Field(min_length=1, max_length=2000)


@router.post("/conversations")
def demarrer_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    annonce = db.query(models.Annonce).filter(models.Annonce.id == data.annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    if not annonce.clerk_user_id:
        raise HTTPException(status_code=400, detail="Impossible de contacter ce donneur")
    if annonce.clerk_user_id == user_id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas contacter votre propre annonce")
    if annonce.donne_at:
        raise HTTPException(status_code=400, detail="Cet objet a deja ete donne")

    existante = (
        db.query(models.Conversation)
        .filter(models.Conversation.annonce_id == data.annonce_id, models.Conversation.demandeur_id == user_id)
        .first()
    )
    if existante:
        return {"id": existante.id}

    demandeur_pseudo = clerk.pseudo_clerk(user_id)
    conv = models.Conversation(
        annonce_id=data.annonce_id,
        donneur_id=annonce.clerk_user_id,
        demandeur_id=user_id,
        donneur_pseudo=(annonce.pseudo or "Un habitant")[:50],
        demandeur_pseudo=demandeur_pseudo[:50],
    )
    db.add(conv)
    try:
        db.commit()
    except IntegrityError:
        # Double clic : la conversation vient d'être créée par l'autre requête
        db.rollback()
        existante = (
            db.query(models.Conversation)
            .filter(models.Conversation.annonce_id == data.annonce_id, models.Conversation.demandeur_id == user_id)
            .first()
        )
        if not existante:
            raise HTTPException(status_code=409, detail="Réessayez")
        return {"id": existante.id}
    db.refresh(conv)
    return {"id": conv.id}


@router.get("/conversations")
def mes_conversations(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    convs = (
        db.query(models.Conversation)
        .filter(
            ((models.Conversation.donneur_id == user_id) & (models.Conversation.donneur_actif == True))
            | ((models.Conversation.demandeur_id == user_id) & (models.Conversation.demandeur_actif == True))
        )
        .order_by(models.Conversation.dernier_message_at.desc())
        .all()
    )
    if not convs:
        return []
    ids = [c.id for c in convs]
    annonces = {
        a.id: a for a in db.query(models.Annonce).filter(models.Annonce.id.in_({c.annonce_id for c in convs})).all()
    }
    non_lus = dict(
        db.query(models.Message.conversation_id, func.count(models.Message.id))
        .filter(
            models.Message.conversation_id.in_(ids),
            models.Message.auteur_id != user_id,
            models.Message.lu == False,
            models.Message.systeme == False,
        )
        .group_by(models.Message.conversation_id)
        .all()
    )
    # Dernier message de chaque conversation en une seule requête (DISTINCT ON Postgres)
    derniers = {
        m.conversation_id: m
        for m in db.query(models.Message)
        .filter(models.Message.conversation_id.in_(ids))
        .distinct(models.Message.conversation_id)
        .order_by(models.Message.conversation_id, models.Message.created_at.desc(), models.Message.id.desc())
        .all()
    }
    resultat = []
    for c in convs:
        dernier = derniers.get(c.id)
        annonce = annonces.get(c.annonce_id)
        resultat.append({
            "id": c.id,
            "annonce_id": c.annonce_id,
            "annonce_titre": annonce.titre if annonce else "Annonce supprimée",
            "annonce_image": (annonce.images[0] if annonce and annonce.images else None),
            "interlocuteur": c.demandeur_pseudo if c.donneur_id == user_id else c.donneur_pseudo,
            "dernier_message": dernier.contenu if dernier else None,
            "dernier_message_at": c.dernier_message_at,
            "created_at": c.created_at,
            "non_lus": non_lus.get(c.id, 0),
        })
    return resultat


@router.get("/conversations/{conversation_id}/messages")
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    conv = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    if not _est_participant(conv, user_id):
        raise HTTPException(status_code=403, detail="Accès refusé")
    # Si j'ai quitté cette conversation, elle n'est plus accessible pour moi
    moi_actif = conv.donneur_actif if conv.donneur_id == user_id else conv.demandeur_actif
    if not moi_actif:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    autre_actif = conv.demandeur_actif if conv.donneur_id == user_id else conv.donneur_actif
    annonce = db.query(models.Annonce).filter(models.Annonce.id == conv.annonce_id).first()
    messages = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.created_at.asc())
        .all()
    )
    return {
        "id": conv.id,
        "annonce_id": conv.annonce_id,
        "annonce_titre": annonce.titre if annonce else "Annonce supprimée",
        "annonce_image": (annonce.images[0] if annonce and annonce.images else None),
        "interlocuteur": conv.demandeur_pseudo if conv.donneur_id == user_id else conv.donneur_pseudo,
        "autre_present": autre_actif,
        "messages": [
            {"id": m.id, "contenu": m.contenu, "created_at": m.created_at, "a_moi": m.auteur_id == user_id, "systeme": m.systeme}
            for m in messages
        ],
    }


@router.post("/conversations/{conversation_id}/messages")
def envoyer_message(
    conversation_id: int,
    data: MessageCreate,
    taches: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    conv = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    if not _est_participant(conv, user_id):
        raise HTTPException(status_code=403, detail="Accès refusé")
    # Si j'ai quitté, ou si l'autre a quitté, on ne peut plus écrire
    moi_actif = conv.donneur_actif if conv.donneur_id == user_id else conv.demandeur_actif
    if not moi_actif:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    autre_actif = conv.demandeur_actif if conv.donneur_id == user_id else conv.donneur_actif
    if not autre_actif:
        raise HTTPException(status_code=400, detail="Cette personne a quitté la conversation")
    verifier_rate_limit(user_id, "message", maximum=60, fenetre_secondes=3600)

    msg = models.Message(conversation_id=conversation_id, auteur_id=user_id, contenu=data.contenu.strip())
    db.add(msg)
    conv.dernier_message_at = datetime.now(timezone.utc)

    # Notification email au destinataire, une seule fois tant qu'il n'a pas lu (anti-spam)
    if user_id == conv.donneur_id:
        destinataire_id, expediteur_pseudo = conv.demandeur_id, conv.donneur_pseudo
        doit_notifier = not conv.notif_demandeur_envoyee
        conv.notif_demandeur_envoyee = True
    else:
        destinataire_id, expediteur_pseudo = conv.donneur_id, conv.demandeur_pseudo
        doit_notifier = not conv.notif_donneur_envoyee
        conv.notif_donneur_envoyee = True

    annonce = db.query(models.Annonce).filter(models.Annonce.id == conv.annonce_id).first()
    annonce_titre = annonce.titre if annonce else "votre annonce"
    db.commit()
    db.refresh(msg)

    if doit_notifier:
        # Envoyé après la réponse : l'expéditeur n'attend pas Clerk + Resend
        taches.add_task(emails.notifier_nouveau_message, destinataire_id, expediteur_pseudo, annonce_titre, conversation_id)

    return {"id": msg.id, "contenu": msg.contenu, "created_at": msg.created_at, "a_moi": True, "systeme": False}


@router.post("/conversations/{conversation_id}/lu")
def marquer_lu(
    conversation_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    conv = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    if not _est_participant(conv, user_id):
        raise HTTPException(status_code=403, detail="Accès refusé")
    db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id,
        models.Message.auteur_id != user_id,
        models.Message.lu == False,
    ).update({models.Message.lu: True})
    if user_id == conv.donneur_id:
        conv.notif_donneur_envoyee = False
    else:
        conv.notif_demandeur_envoyee = False
    db.commit()
    return {"ok": True}


@router.get("/messages/non-lus")
def compteur_non_lus(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    total = (
        db.query(models.Message)
        .join(models.Conversation, models.Message.conversation_id == models.Conversation.id)
        .filter(
            ((models.Conversation.donneur_id == user_id) & (models.Conversation.donneur_actif == True))
            | ((models.Conversation.demandeur_id == user_id) & (models.Conversation.demandeur_actif == True)),
            models.Message.auteur_id != user_id,
            models.Message.lu == False,
            models.Message.systeme == False,
        )
        .count()
    )
    return {"non_lus": total}


@router.delete("/conversations/{conversation_id}")
def quitter_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Quitter une conversation : elle disparaît pour moi, et l'autre voit « X a quitté la conversation »."""
    conv = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    if not _est_participant(conv, user_id):
        raise HTTPException(status_code=403, detail="Accès refusé")

    moi_actif = conv.donneur_actif if user_id == conv.donneur_id else conv.demandeur_actif
    if not moi_actif:
        return {"ok": True}  # déjà quittée : pas de second message « a quitté »

    if user_id == conv.donneur_id:
        conv.donneur_actif = False
        mon_pseudo = conv.donneur_pseudo
        autre_actif = conv.demandeur_actif
    else:
        conv.demandeur_actif = False
        mon_pseudo = conv.demandeur_pseudo
        autre_actif = conv.donneur_actif

    if autre_actif:
        # L'autre est encore là : on le prévient par un message système
        db.add(models.Message(
            conversation_id=conv.id,
            auteur_id="__system__",
            contenu=f"{mon_pseudo} a quitté la conversation",
            systeme=True,
        ))
        conv.dernier_message_at = datetime.now(timezone.utc)
        db.commit()
    else:
        # Les deux ont quitté : plus personne, on supprime définitivement
        db.delete(conv)
        db.commit()
    return {"ok": True}


class ConversationSignalement(PydanticBase):
    raison: str = Field(min_length=3, max_length=500)


@router.post("/conversations/{conversation_id}/signaler")
def signaler_conversation(
    conversation_id: int,
    data: ConversationSignalement,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    conv = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    if not _est_participant(conv, user_id):
        raise HTTPException(status_code=403, detail="Accès refusé")
    verifier_rate_limit(user_id, "signalement", maximum=5, fenetre_secondes=3600)
    # Rattaché à l'annonce de la conversation pour apparaître dans le panel admin existant ;
    # le numéro permet de retrouver la conversation concernée
    raison = f"[Conversation #{conv.id}] {data.raison.strip()}"
    existant = (
        db.query(models.Signalement)
        .filter(models.Signalement.clerk_user_id == user_id, models.Signalement.annonce_id == conv.annonce_id)
        .first()
    )
    if existant:
        # On complète le signalement existant au lieu de l'écraser
        existant.raison = f"{existant.raison}\n{raison}"
        existant.traite = False
    else:
        db.add(models.Signalement(annonce_id=conv.annonce_id, clerk_user_id=user_id, raison=raison))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return {"ok": True}

