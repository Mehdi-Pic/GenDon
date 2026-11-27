"""Panel d'administration : statistiques, annonces, utilisateurs, signalements, journal, emails."""
import hashlib
from datetime import datetime, timedelta, timezone
from math import ceil

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel as PydanticBase, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import clerk, emails, models, roles, schemas
from ..database import get_db
from ..outils import auteur_non_suspendu, enregistrer_suspension, filtre_recherche
from ..photos import supprimer_images_cloudinary
from ..roles import exiger_admin, exiger_moderateur, journaliser
from . import contact
from .annonces import LIMITE_PAR_PAGE

router = APIRouter()


@router.get("/admin/moi")
def admin_moi(acteur: dict = Depends(exiger_moderateur)):
    return {"role": acteur["role"]}


@router.get("/admin/stats")
def admin_stats(db: Session = Depends(get_db), acteur: dict = Depends(exiger_moderateur)):
    il_y_a_7_jours = datetime.now(timezone.utc) - timedelta(days=7)
    donnees = db.query(models.Annonce).filter(models.Annonce.donne_at != None)  # noqa: E711
    return {
        # Même définition que /stats (page d'accueil) : non donnée et auteur non suspendu
        "annonces": db.query(models.Annonce).filter(models.Annonce.donne_at == None, auteur_non_suspendu()).count(),  # noqa: E711
        # Encore en base mais masquées du public : données (purgées après quelques jours) ou auteur suspendu
        "annonces_donnees": donnees.count(),
        "annonces_suspendues": db.query(models.Annonce).filter(
            models.Annonce.donne_at == None, ~auteur_non_suspendu()  # noqa: E711
        ).count(),
        "annonces_semaine": db.query(models.Annonce).filter(models.Annonce.created_at >= il_y_a_7_jours).count(),
        "vues_totales": db.query(func.coalesce(func.sum(models.Annonce.vues), 0)).scalar(),
        "favoris": db.query(models.Favori).count(),
        "dons_realises": db.query(models.DonRealise).count(),
        "signalements_en_attente": db.query(models.Signalement).filter(models.Signalement.traite == False).count(),
    }


@router.get("/admin/annonces", response_model=schemas.AnnoncesPaginées)
def admin_lister_annonces(
    recherche: str = None,
    page: int = 1,
    db: Session = Depends(get_db),
    acteur: dict = Depends(exiger_moderateur),
):
    page = max(1, page)
    query = db.query(models.Annonce)
    if recherche:
        query = query.filter(
            filtre_recherche(recherche, models.Annonce.titre, models.Annonce.description, models.Annonce.pseudo)
        )
    query = query.order_by(models.Annonce.created_at.desc(), models.Annonce.id.desc())
    total = query.count()
    annonces = query.offset((page - 1) * LIMITE_PAR_PAGE).limit(LIMITE_PAR_PAGE).all()
    auteurs = {a.clerk_user_id for a in annonces if a.clerk_user_id}
    suspendus = {
        uid for (uid,) in db.query(models.CompteSuspendu.clerk_user_id)
        .filter(models.CompteSuspendu.clerk_user_id.in_(auteurs)).all()
    } if auteurs else set()
    for a in annonces:
        a.auteur_suspendu = a.clerk_user_id in suspendus
    return {"annonces": annonces, "total": total, "pages": ceil(total / LIMITE_PAR_PAGE) if total > 0 else 1, "page": page}


@router.delete("/admin/annonces/{annonce_id}")
def admin_supprimer_annonce(
    annonce_id: int,
    db: Session = Depends(get_db),
    acteur: dict = Depends(exiger_moderateur),
):
    annonce = db.query(models.Annonce).filter(models.Annonce.id == annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    journaliser(db, acteur["user_id"], "suppression_annonce", f"#{annonce_id} « {annonce.titre} » de {annonce.pseudo}")
    images = list(annonce.images or [])
    db.delete(annonce)
    db.commit()
    supprimer_images_cloudinary(images)
    return {"message": "Annonce supprimée"}


@router.get("/admin/utilisateurs")
def admin_lister_utilisateurs(
    db: Session = Depends(get_db),
    acteur: dict = Depends(exiger_moderateur),
):
    # Tous les comptes (pagination Clerk), et plus seulement les 100 derniers
    comptes_clerk = clerk.tous_les_utilisateurs()
    if not comptes_clerk:
        raise HTTPException(status_code=502, detail="Impossible de récupérer les utilisateurs")
    comptes = dict(
        db.query(models.Annonce.clerk_user_id, func.count(models.Annonce.id))
        .group_by(models.Annonce.clerk_user_id)
        .all()
    )
    roles_en_base = {r.clerk_user_id: r.role for r in db.query(models.Role).all()}
    admins = roles.admins_principaux()
    # Les modérateurs n'ont pas besoin des adresses email pour modérer : réservées aux admins
    voit_emails = acteur["role"] == "admin"
    utilisateurs = []
    for u in comptes_clerk:
        uid = u["id"]
        utilisateurs.append({
            "id": uid,
            "pseudo": u.get("username") or u.get("first_name") or "(sans pseudo)",
            "email": clerk.email_principal(u) if voit_emails else None,
            "image": u.get("image_url"),
            "created_at": u.get("created_at"),
            "nb_annonces": comptes.get(uid, 0),
            "role": "admin" if uid in admins else roles_en_base.get(uid),
            "est_admin_principal": uid in admins,
            "suspendu": bool(u.get("banned")),
        })
    return utilisateurs


class RoleUpdate(PydanticBase):
    role: str = Field(pattern="^(moderateur|aucun)$")


@router.post("/admin/utilisateurs/{uid}/role")
def admin_changer_role(
    uid: str,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    acteur: dict = Depends(exiger_admin),
):
    if uid in roles.admins_principaux():
        raise HTTPException(status_code=400, detail="Le rôle d'un administrateur principal ne peut pas être modifié")
    ligne = db.query(models.Role).filter(models.Role.clerk_user_id == uid).first()
    if data.role == "aucun":
        if ligne:
            db.delete(ligne)
            db.commit()
    else:
        if ligne:
            ligne.role = data.role
        else:
            db.add(models.Role(clerk_user_id=uid, role=data.role))
        db.commit()
    journaliser(db, acteur["user_id"], "changement_role", f"{uid} → {data.role}")
    contact._cache_emails_equipe["expire"] = 0.0  # l'équipe a changé : destinataires du contact à relire
    return {"role": None if data.role == "aucun" else data.role}


@router.get("/admin/signalements")
def admin_lister_signalements(
    db: Session = Depends(get_db),
    acteur: dict = Depends(exiger_moderateur),
):
    lignes = (
        db.query(models.Signalement, models.Annonce.titre, models.Conversation)
        .outerjoin(models.Annonce, models.Annonce.id == models.Signalement.annonce_id)
        .outerjoin(models.Conversation, models.Conversation.id == models.Signalement.conversation_id)
        .order_by(models.Signalement.traite.asc(), models.Signalement.created_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": s.id,
            # "annonce" ou "conversation" : ce qui a été signalé
            "type": "conversation" if s.conversation_id or not s.annonce_id else "annonce",
            "annonce_id": s.annonce_id,
            "annonce_titre": titre,
            "conversation_id": s.conversation_id,
            "conversation_titre": conv.annonce_titre if conv else None,
            "raison": s.raison,
            "traite": s.traite,
            "created_at": s.created_at,
        }
        for s, titre, conv in lignes
    ]


@router.get("/admin/conversations/{conversation_id}")
def admin_lire_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    acteur: dict = Depends(exiger_moderateur),
):
    """Lecture d'une conversation par l'équipe : uniquement si elle a été signalée par l'un
    des participants (jamais de consultation libre des messages), et chaque lecture est journalisée."""
    conv = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    signalee = (
        db.query(models.Signalement.id).filter(models.Signalement.conversation_id == conversation_id).first()
    )
    if not conv or not signalee:
        raise HTTPException(status_code=404, detail="Conversation introuvable ou non signalée")
    messages = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.created_at.asc(), models.Message.id.asc())
        .all()
    )
    journaliser(db, acteur["user_id"], "conversation_consultee", f"conversation #{conversation_id}")
    suspendus = {
        uid for (uid,) in db.query(models.CompteSuspendu.clerk_user_id)
        .filter(models.CompteSuspendu.clerk_user_id.in_([conv.donneur_id, conv.demandeur_id])).all()
    }

    def auteur(m):
        if m.systeme:
            return "systeme"
        return "donneur" if m.auteur_id == conv.donneur_id else "demandeur"

    return {
        "id": conv.id,
        "annonce_id": conv.annonce_id,
        "annonce_titre": conv.annonce_titre,
        "donneur": {"id": conv.donneur_id, "pseudo": conv.donneur_pseudo, "suspendu": conv.donneur_id in suspendus},
        "demandeur": {
            "id": conv.demandeur_id, "pseudo": conv.demandeur_pseudo, "suspendu": conv.demandeur_id in suspendus,
        },
        "messages": [
            {"id": m.id, "auteur": auteur(m), "contenu": m.contenu, "created_at": m.created_at} for m in messages
        ],
    }


@router.patch("/admin/signalements/{signalement_id}/traiter")
def admin_traiter_signalement(
    signalement_id: int,
    db: Session = Depends(get_db),
    acteur: dict = Depends(exiger_moderateur),
):
    s = db.query(models.Signalement).filter(models.Signalement.id == signalement_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Signalement introuvable")
    s.traite = True
    db.commit()
    journaliser(db, acteur["user_id"], "signalement_traite", f"signalement #{signalement_id}")
    return {"traite": True}


@router.get("/admin/journal")
def admin_journal(
    db: Session = Depends(get_db),
    acteur: dict = Depends(exiger_admin),
):
    lignes = (
        db.query(models.ActionModeration)
        .order_by(models.ActionModeration.created_at.desc())
        .limit(200)
        .all()
    )
    # Pseudo de chaque membre de l'équipe (quelques personnes : un appel Clerk par membre)
    pseudos = {uid: clerk.pseudo_clerk(uid) for uid in {l.clerk_user_id for l in lignes}}
    return [
        {
            "id": l.id, "par": pseudos.get(l.clerk_user_id, l.clerk_user_id), "action": l.action,
            "details": l.details, "created_at": l.created_at,
        }
        for l in lignes
    ]


class Suspension(PydanticBase):
    suspendu: bool


@router.post("/admin/utilisateurs/{uid}/suspendre")
def admin_suspendre_utilisateur(
    uid: str,
    data: Suspension,
    db: Session = Depends(get_db),
    acteur: dict = Depends(exiger_moderateur),
):
    """Suspend (bannit chez Clerk) ou réactive un compte. Un modérateur ne peut suspendre
    qu'un utilisateur ordinaire ; personne ne peut suspendre un administrateur principal ni soi-même."""
    if uid == acteur["user_id"]:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas suspendre votre propre compte")
    role_cible = roles.role_utilisateur(db, uid)
    if role_cible == "admin" or (role_cible and acteur["role"] != "admin"):
        raise HTTPException(status_code=403, detail="Ce compte ne peut pas être suspendu par vous")
    if not clerk.suspendre(uid, data.suspendu):
        raise HTTPException(status_code=502, detail="Clerk n'a pas pu appliquer la suspension")
    enregistrer_suspension(db, uid, data.suspendu)
    db.commit()
    pseudo = clerk.pseudo_clerk(uid)
    journaliser(db, acteur["user_id"], "suspension" if data.suspendu else "reactivation", f"{pseudo} ({uid})")
    return {"suspendu": data.suspendu}


# ---------- Email d'information à tous les inscrits (admins uniquement) ----------

class EmailInformation(PydanticBase):
    sujet: str = Field(min_length=3, max_length=150)
    titre: str = Field(min_length=3, max_length=120)
    message: str = Field(min_length=10, max_length=5000)
    bouton_don: bool = True


def _destinataires_information(db: Session) -> list:
    """(user_id, email) des inscrits, sauf ceux qui ont refusé les emails d'information."""
    desabonnes = {d.clerk_user_id for d in db.query(models.DesabonnementNewsletter).all()}
    destinataires = []
    for u in clerk.tous_les_utilisateurs():
        uid, email = u.get("id"), clerk.email_principal(u)
        if uid and email and uid not in desabonnes and not u.get("banned"):
            destinataires.append((uid, email))
    return destinataires


def _email_information(data: EmailInformation, uid: str, email: str) -> dict:
    lien_desabo = f"{emails.frontend_url()}/desabonnement?token={emails.token_desabonnement(uid)}"
    return {
        "from": emails.expediteur(),
        "to": [email],
        "subject": data.sujet,
        "headers": {"List-Unsubscribe": f"<{lien_desabo}>"},
        "html": emails.email_information(data.titre, data.message, data.bouton_don, lien_desabo),
    }


def _exiger_cle_desabonnement():
    if not emails.cle_desabonnement():
        raise HTTPException(status_code=503, detail="NEWSLETTER_SECRET manquant : liens de désabonnement impossibles")


@router.post("/admin/emails/apercu")
def admin_apercu_email(
    data: EmailInformation,
    db: Session = Depends(get_db),
    acteur: dict = Depends(exiger_admin),
):
    _exiger_cle_desabonnement()
    lien = f"{emails.frontend_url()}/desabonnement?token={emails.token_desabonnement(acteur['user_id'])}"
    return {
        "html": emails.email_information(data.titre, data.message, data.bouton_don, lien),
        "destinataires": len(_destinataires_information(db)),
    }


@router.post("/admin/emails/test")
def admin_tester_email(data: EmailInformation, acteur: dict = Depends(exiger_admin)):
    """Envoie l'email à l'administrateur seul, pour le relire dans une vraie boîte mail."""
    _exiger_cle_desabonnement()
    email = clerk.email_utilisateur(acteur["user_id"])
    if not email:
        raise HTTPException(status_code=502, detail="Adresse email introuvable pour votre compte")
    contenu = _email_information(data, acteur["user_id"], email)
    try:
        emails.envoyer(email, f"[TEST] {data.sujet}", contenu["html"], headers=contenu["headers"])
    except Exception:
        raise HTTPException(status_code=502, detail="L'envoi a échoué (Resend)")
    return {"envoye_a": email}


@router.post("/admin/emails/envoi")
def admin_envoyer_email(
    data: EmailInformation,
    taches_fond: BackgroundTasks,
    db: Session = Depends(get_db),
    acteur: dict = Depends(exiger_admin),
):
    """Envoie l'email à tous les inscrits. Le même email (sujet + message) ne part qu'une fois
    par jour même en cas de double clic : clé d'idempotence Resend."""
    _exiger_cle_desabonnement()
    destinataires = _destinataires_information(db)
    if not destinataires:
        raise HTTPException(status_code=502, detail="Aucun destinataire (Clerk injoignable ?)")
    empreinte = hashlib.sha256(f"{data.sujet}\n{data.titre}\n{data.message}".encode()).hexdigest()[:16]
    jour = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    envois = [_email_information(data, uid, email) for uid, email in destinataires]
    taches_fond.add_task(emails.envoyer_en_masse, envois, f"information-{jour}-{empreinte}")
    journaliser(db, acteur["user_id"], "email_information", f"« {data.sujet} » → {len(envois)} destinataires")
    return {"destinataires": len(envois)}
