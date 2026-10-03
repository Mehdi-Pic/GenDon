"""Formulaire de contact : écrit à l'équipe (admins + modérateurs)."""
import os
import re
import time
from html import escape

import httpx
import resend
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel as PydanticBase, Field
from sqlalchemy.orm import Session

from .. import clerk, models, roles
from ..auth import get_user_id_optionnel
from ..database import get_db
from ..outils import ip_client, limite_atteinte, verifier_rate_limit

router = APIRouter()


class MessageContactSite(PydanticBase):
    nom: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=5, max_length=120)
    sujet: str = Field(min_length=3, max_length=120)
    message: str = Field(min_length=10, max_length=2000)
    # Champ piege : invisible pour un humain, souvent rempli par les robots
    site_web: str = Field(default="", max_length=200)


# Plafonds GLOBAUX du formulaire, tous expéditeurs confondus. La limite par IP ne suffit pas :
# un robot qui change d'IP à chaque envoi pourrait sinon épuiser le quota Resend et bloquer
# tous les emails du site (notifications, rappels, newsletter).
CONTACT_MAX_PAR_HEURE = 20
CONTACT_MAX_PAR_JOUR = 50
REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
DUREE_CACHE_EQUIPE = 600  # secondes

_cache_emails_equipe = {"emails": [], "expire": 0.0}


def _une_ligne(texte: str) -> str:
    """Retire retours à la ligne et caractères de contrôle (sujet, nom : pas d'en-tête injectable)."""
    return " ".join("".join(c if c.isprintable() else " " for c in texte).split())


def _emails_equipe(db: Session) -> list:
    """Emails des administrateurs (variable Railway) et des modérateurs (table roles).
    Mis en cache 10 minutes : sans cela, chaque envoi interrogeait Clerk une fois par membre."""
    if time.monotonic() < _cache_emails_equipe["expire"] and _cache_emails_equipe["emails"]:
        return list(_cache_emails_equipe["emails"])
    # CONTACT_EMAIL (ex. contact@gendon.fr) remplace l'adresse personnelle des admins principaux :
    # leurs réponses partent alors de l'adresse du site, pas de leur boîte perso
    adresse_site = os.getenv("CONTACT_EMAIL", "").strip()
    identifiants = {r.clerk_user_id for r in db.query(models.Role).all()}
    if adresse_site:
        identifiants -= set(roles.admins_principaux())
    else:
        identifiants |= set(roles.admins_principaux())
    headers = {"Authorization": f"Bearer {os.getenv('CLERK_SECRET_KEY')}"}
    emails = []
    for uid in identifiants:
        try:
            r = httpx.get(f"https://api.clerk.com/v1/users/{uid}", headers=headers, timeout=10)
            if r.is_success:
                adresse = clerk.email_principal(r.json())
                if adresse:
                    emails.append(adresse)
        except Exception:
            continue
    if adresse_site:
        emails.insert(0, adresse_site)
    if emails:
        _cache_emails_equipe["emails"] = emails
        _cache_emails_equipe["expire"] = time.monotonic() + DUREE_CACHE_EQUIPE
    return emails


@router.post("/contact")
def contacter_equipe(
    data: MessageContactSite,
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id_optionnel),
):
    # Robot detecte : on fait comme si tout s'etait bien passe, sans rien envoyer
    if data.site_web.strip():
        return {"ok": True}

    expediteur = data.email.strip()
    if not REGEX_EMAIL.match(expediteur):
        raise HTTPException(status_code=400, detail="Adresse email invalide")
    nom = _une_ligne(data.nom)
    sujet = _une_ligne(data.sujet)
    if not nom or len(sujet) < 3:
        raise HTTPException(status_code=400, detail="Nom ou sujet invalide")

    # Anti-spam : par compte si connecté, sinon par adresse IP
    cle = user_id or ip_client(request)
    verifier_rate_limit(cle, "contact_site", maximum=3, fenetre_secondes=3600)
    # Puis plafonds globaux (comptés seulement si l'expéditeur a passé sa propre limite)
    if limite_atteinte("tous", "contact_site_heure", CONTACT_MAX_PAR_HEURE, 3600) or limite_atteinte(
        "tous", "contact_site_jour", CONTACT_MAX_PAR_JOUR, 24 * 3600
    ):
        raise HTTPException(
            status_code=429, detail="Le formulaire reçoit trop de messages en ce moment, réessayez plus tard"
        )

    destinataires = _emails_equipe(db)
    if not destinataires:
        raise HTTPException(status_code=503, detail="Aucun contact disponible pour le moment")

    resend.api_key = os.getenv("RESEND_API_KEY")
    try:
        resend.Emails.send({
            "from": f"GenDon <{os.getenv('RESEND_FROM_EMAIL', 'onboarding@resend.dev')}>",
            "to": destinataires,
            "reply_to": expediteur,
            "subject": f"[Contact GenDon] {sujet}",
            "html": f"""
            <div style="font-family:sans-serif;max-width:560px;margin:auto;color:#111">
              <p style="font-size:18px;font-weight:700;margin-bottom:4px">Nouveau message via le formulaire de contact</p>
              <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0"/>
              <p><strong>De :</strong> {escape(nom)} ({escape(expediteur)})</p>
              <p><strong>Sujet :</strong> {escape(sujet)}</p>
              <p><strong>Message :</strong></p>
              <blockquote style="background:#f9fafb;border-left:3px solid #d1d5db;padding:12px 16px;margin:0;border-radius:4px;color:#374151;white-space:pre-wrap">{escape(data.message.strip())}</blockquote>
              <p style="margin-top:20px;color:#6b7280;font-size:13px">Répondez directement à cet email pour joindre l'expéditeur.</p>
            </div>
            """,
        })
    except Exception:
        raise HTTPException(status_code=500, detail="L'envoi du message a échoué")
    return {"ok": True}
