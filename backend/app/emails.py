"""Envoi d'emails (Resend) : gabarit commun, liens signés de désabonnement, notifications."""
import hashlib
import hmac
import os
from html import escape

import resend

from . import clerk

PIED_DE_PAGE = "GenDon · Dons gratuits entre habitants de Gennevilliers"


def frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "").split(",")[0].strip() or "https://www.gendon.fr"


def expediteur() -> str:
    return f"GenDon <{os.getenv('RESEND_FROM_EMAIL', 'onboarding@resend.dev')}>"


def bouton(lien: str, texte: str) -> str:
    return (
        f'<a href="{lien}" style="background:#16a34a;color:#fff;text-decoration:none;padding:11px 22px;'
        f'border-radius:9999px;font-weight:600;display:inline-block">{texte}</a>'
    )


def encadre(texte: str) -> str:
    """Titre d'annonce mis en avant (texte déjà échappé)."""
    return (
        '<p style="background:#f9fafb;border-left:3px solid #16a34a;padding:12px 16px;'
        f'border-radius:4px;font-weight:600">{texte}</p>'
    )


def gabarit(titre: str, corps: str, pied: str = "") -> str:
    """Mise en page commune des emails transactionnels. `corps` et `pied` sont du HTML déjà échappé."""
    return f"""
    <div style="font-family:sans-serif;max-width:560px;margin:auto;color:#111">
      <p style="font-size:18px;font-weight:700;margin-bottom:4px">{titre}</p>
      <p style="color:#6b7280;margin-top:0">via <strong>GenDon</strong> · Gennevilliers</p>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0"/>
      {corps}
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0"/>
      <p style="color:#9ca3af;font-size:12px">{PIED_DE_PAGE}{"<br/>" + pied if pied else ""}</p>
    </div>
    """


def envoyer(destinataire: str, sujet: str, html: str, **options) -> None:
    resend.api_key = os.getenv("RESEND_API_KEY")
    resend.Emails.send({"from": expediteur(), "to": [destinataire], "subject": sujet, "html": html, **options})


def vignette_email(url: str, largeur: int = 320) -> str:
    """Version réduite d'une image Cloudinary pour l'email."""
    return url.replace("/upload/", f"/upload/w_{largeur},q_auto,f_auto/") if "/upload/" in url else url


def cle_desabonnement():
    """Clé HMAC des liens de désabonnement. Pas de valeur par défaut : une clé connue
    permettrait de forger un lien pour n'importe quel compte."""
    cle = os.getenv("NEWSLETTER_SECRET") or os.getenv("CLERK_SECRET_KEY")
    return cle.encode() if cle else None


def token_desabonnement(user_id: str) -> str:
    signature = hmac.new(cle_desabonnement(), user_id.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{user_id}.{signature}"


def verifier_token_desabonnement(token: str):
    cle = cle_desabonnement()
    if not cle:
        return None
    try:
        user_id, signature = token.rsplit(".", 1)
    except ValueError:
        return None
    attendu = hmac.new(cle, user_id.encode(), hashlib.sha256).hexdigest()[:32]
    return user_id if hmac.compare_digest(signature, attendu) else None


def notifier_nouveau_message(destinataire_id: str, expediteur_pseudo: str, annonce_titre: str, conversation_id: int):
    """Email 'nouveau message' au destinataire (tâche de fond, best-effort)."""
    try:
        email = clerk.email_utilisateur(destinataire_id)
        if not email:
            return
        frontend = frontend_url()
        corps = f"""
          <p><strong>{escape(expediteur_pseudo)}</strong> vous a écrit à propos de :</p>
          {encadre(escape(annonce_titre))}
          <p style="margin-top:24px">{bouton(f"{frontend}/messages/{conversation_id}", "Voir la conversation")}</p>
        """
        pied = f'<a href="{frontend}/profil" style="color:#9ca3af">Gérer mes notifications par email</a>'
        envoyer(
            email,
            f"Nouveau message de {expediteur_pseudo} sur GenDon",
            gabarit("Vous avez un nouveau message", corps, pied),
        )
    except Exception:
        pass
