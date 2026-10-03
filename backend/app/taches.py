"""Tâches planifiées : purges, rappels d'expiration, newsletter, alertes de recherche."""
import os
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from html import escape

import httpx
import resend
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from sqlalchemy import func

from . import clerk, emails, models
from .database import SessionLocal
from .outils import auteur_non_suspendu, filtre_recherche, nettoyer_rate_limit
from .photos import supprimer_images_cloudinary


# Une annonce declaree donnee reste visible pour son proprietaire quelques jours, puis disparait
DELAI_RETRAIT_DON_JOURS = 3


def purger_annonces_expirees():
    db = SessionLocal()
    try:
        limite = datetime.now(timezone.utc) - timedelta(days=30)
        limite_donnees = datetime.now(timezone.utc) - timedelta(days=DELAI_RETRAIT_DON_JOURS)
        expirees = (
            db.query(models.Annonce)
            .filter(
                (models.Annonce.created_at < limite)
                | ((models.Annonce.donne_at != None) & (models.Annonce.donne_at < limite_donnees))
            )
            .all()
        )
        # Une annonce en erreur ne doit pas bloquer la purge des autres
        for annonce in expirees:
            try:
                images = list(annonce.images or [])
                db.delete(annonce)
                db.commit()
                supprimer_images_cloudinary(images)
            except Exception:
                db.rollback()
    except Exception:
        db.rollback()
    finally:
        db.close()


DELAI_IMAGE_ORPHELINE_JOURS = 2


def purger_images_orphelines():
    """Supprime les images envoyées mais jamais publiées (formulaire abandonné, photo retirée)
    ou dont l'annonce a disparu."""
    db = SessionLocal()
    try:
        limite = datetime.now(timezone.utc) - timedelta(days=DELAI_IMAGE_ORPHELINE_JOURS)
        candidates = db.query(models.ImageUploadee).filter(models.ImageUploadee.created_at < limite).all()
        for image in candidates:
            try:
                utilisee = (
                    db.query(models.Annonce.id).filter(models.Annonce.images.any(image.url)).first() is not None
                )
                if utilisee:
                    continue
                db.delete(image)
                db.commit()
                supprimer_images_cloudinary([image.url])
            except Exception:
                db.rollback()
    finally:
        db.close()


DUREE_JOURNAL_MODERATION_JOURS = 365


def purger_journal_moderation():
    """Le journal cite pseudos et titres d'annonces : il n'est conservé qu'un an."""
    db = SessionLocal()
    try:
        limite = datetime.now(timezone.utc) - timedelta(days=DUREE_JOURNAL_MODERATION_JOURS)
        db.query(models.ActionModeration).filter(models.ActionModeration.created_at < limite).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()



def envoyer_rappels_expiration():
    """Tâche quotidienne : prévient les donneurs 3 jours avant la suppression auto (30 j)."""
    db = SessionLocal()
    try:
        limite = datetime.now(timezone.utc) - timedelta(days=27)
        a_rappeler = (
            db.query(models.Annonce)
            .filter(
                models.Annonce.created_at < limite,
                models.Annonce.rappel_envoye == False,
                models.Annonce.donne_at == None,
            )
            .all()
        )
        if not a_rappeler:
            return
        clerk_secret = os.getenv("CLERK_SECRET_KEY")
        resend.api_key = os.getenv("RESEND_API_KEY")
        frontend = os.getenv("FRONTEND_URL", "").split(",")[0].strip() or "https://www.gendon.fr"
        for annonce in a_rappeler:
            try:
                email = None
                if annonce.clerk_user_id:
                    res = httpx.get(
                        f"https://api.clerk.com/v1/users/{annonce.clerk_user_id}",
                        headers={"Authorization": f"Bearer {clerk_secret}"},
                        timeout=10,
                    )
                    if res.is_success:
                        email = clerk.email_principal(res.json())
                if email:
                    resend.Emails.send({
                        "from": f"GenDon <{os.getenv('RESEND_FROM_EMAIL', 'onboarding@resend.dev')}>",
                        "to": [email],
                        "subject": f"Votre annonce « {annonce.titre} » expire dans 3 jours",
                        "html": f"""
                        <div style="font-family:sans-serif;max-width:560px;margin:auto;color:#111">
                          <p style="font-size:18px;font-weight:700;margin-bottom:4px">Votre annonce expire bientôt</p>
                          <p style="color:#6b7280;margin-top:0">via <strong>GenDon</strong> · Gennevilliers</p>
                          <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0"/>
                          <p>Votre annonce :</p>
                          <p style="background:#f9fafb;border-left:3px solid #16a34a;padding:12px 16px;border-radius:4px;font-weight:600">{escape(annonce.titre)}</p>
                          <p>sera <strong>supprimée automatiquement dans 3 jours</strong> (les annonces GenDon restent en ligne 30 jours).</p>
                          <p style="margin-top:16px"><strong>Toujours disponible ?</strong> Vous pouvez la relancer pour 30 jours
                            depuis <strong>Mon profil</strong>, onglet Mes annonces, avec le bouton « Renouveler ».</p>
                          <p style="margin-top:20px">
                            <a href="{frontend}/profil" style="background:#16a34a;color:#fff;text-decoration:none;padding:11px 22px;border-radius:9999px;font-weight:600;display:inline-block">Renouveler mon annonce</a>
                          </p>
                          <p style="margin-top:16px">Objet déjà donné ? Rien à faire, elle disparaîtra toute seule.</p>
                          <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0"/>
                          <p style="color:#9ca3af;font-size:12px">GenDon · Dons gratuits entre habitants de Gennevilliers</p>
                        </div>
                        """,
                    })
                # Marqué même sans email trouvé : inutile de réessayer chaque jour
                annonce.rappel_envoye = True
                db.commit()
            except Exception:
                db.rollback()
    finally:
        db.close()



def envoyer_newsletter_hebdo():
    """Chaque jeudi 18h30 : rappel du principe du don + les 5 dernières annonces."""
    db = SessionLocal()
    try:
        annonces = (
            db.query(models.Annonce)
            .filter(models.Annonce.donne_at == None, auteur_non_suspendu())
            .order_by(models.Annonce.created_at.desc())
            .limit(5)
            .all()
        )
        if not annonces:
            return  # rien à annoncer, on n'envoie pas d'email vide

        if not emails.cle_desabonnement():
            return  # impossible de générer des liens de désabonnement valides

        desabonnes = {d.clerk_user_id for d in db.query(models.DesabonnementNewsletter).all()}
        utilisateurs = clerk.tous_les_utilisateurs()
        if not utilisateurs:
            return

        frontend = os.getenv("FRONTEND_URL", "").split(",")[0].strip() or "https://www.gendon.fr"
        resend.api_key = os.getenv("RESEND_API_KEY")

        cartes = ""
        for a in annonces:
            image = emails.vignette_email(a.images[0]) if a.images else None
            visuel = (
                f'<img src="{image}" alt="" width="90" height="90" '
                f'style="width:90px;height:90px;object-fit:cover;border-radius:10px;display:block">'
                if image
                else '<div style="width:90px;height:90px;background:#f3f4f6;border-radius:10px"></div>'
            )
            cartes += f"""
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                   style="border:1px solid #e5e7eb;border-radius:12px;margin-bottom:12px">
              <tr>
                <td width="106" style="padding:10px 0 10px 10px;vertical-align:top">{visuel}</td>
                <td style="padding:12px 14px;vertical-align:top">
                  <a href="{frontend}/annonces/{a.id}"
                     style="color:#111;font-weight:700;font-size:15px;text-decoration:none">{escape(a.titre)}</a>
                  <p style="margin:4px 0 0;color:#6b7280;font-size:13px">{escape(a.quartier)} · {escape(a.categorie)}</p>
                </td>
              </tr>
            </table>
            """

        envois = []
        for u in utilisateurs:
            uid = u.get("id")
            if not uid or uid in desabonnes:
                continue
            email = clerk.email_principal(u)
            if not email:
                continue
            lien_desabo = f"{frontend}/desabonnement?token={emails.token_desabonnement(uid)}"
            envois.append({
                "from": f"GenDon <{os.getenv('RESEND_FROM_EMAIL', 'onboarding@resend.dev')}>",
                "to": [email],
                "subject": "Les derniers dons à Gennevilliers cette semaine",
                "headers": {"List-Unsubscribe": f"<{lien_desabo}>"},
                "html": f"""
                <div style="font-family:sans-serif;max-width:560px;margin:auto;color:#111">
                  <p style="font-size:18px;font-weight:700;margin-bottom:4px">Les derniers dons près de chez vous</p>
                  <p style="color:#6b7280;margin-top:0">via <strong>GenDon</strong> · Gennevilliers</p>

                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                         style="background:#f0fdf4;border-left:4px solid #16a34a;border-radius:8px;margin:20px 0">
                    <tr><td style="padding:14px 18px">
                      <p style="margin:0;font-weight:600">Un objet qui ne vous sert plus ?</p>
                      <p style="margin:6px 0 0;color:#374151;font-size:14px">
                        Offrez-lui une seconde vie : déposez votre don en 2 minutes, c'est gratuit
                        et il profitera à un habitant du quartier.
                      </p>
                      <p style="margin:14px 0 0">
                        <a href="{frontend}/annonces/new"
                           style="background:#16a34a;color:#fff;text-decoration:none;padding:10px 20px;border-radius:9999px;font-weight:600;display:inline-block;font-size:14px">Déposer un don</a>
                      </p>
                    </td></tr>
                  </table>

                  <p style="font-weight:700;margin-bottom:12px">Les 5 derniers dons publiés</p>
                  {cartes}

                  <p style="margin-top:20px">
                    <a href="{frontend}/annonces" style="color:#16a34a;font-weight:600">Voir tous les dons disponibles</a>
                  </p>

                  <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0"/>
                  <p style="color:#9ca3af;font-size:12px">
                    GenDon · Dons gratuits entre habitants de Gennevilliers<br/>
                    <a href="{lien_desabo}" style="color:#9ca3af">Ne plus recevoir cet email</a>
                  </p>
                </div>
                """,
            })

        # Envoi par lots de 100 (API batch Resend) avec une pause entre les lots :
        # un appel par destinataire dépassait la limite de débit et des emails étaient perdus.
        # La clé d'idempotence évite un double envoi si la tâche est relancée le même jour.
        jour = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for i in range(0, len(envois), 100):
            lot = envois[i:i + 100]
            for tentative in range(3):
                try:
                    resend.Batch.send(
                        lot,
                        {"idempotency_key": f"newsletter-{jour}-{i}", "batch_validation": "permissive"},
                    )
                    break
                except Exception:
                    time.sleep(2 * (tentative + 1))
            time.sleep(1)
    except Exception:
        pass
    finally:
        db.close()


# Conversation dont l'annonce n'existe plus : conservée ce délai après le dernier message,
# le temps de finaliser la remise de l'objet
DELAI_CONVERSATION_SANS_ANNONCE_JOURS = 30


def purger_conversations():
    """Supprime les conversations abandonnées : annonce retirée et plus d'activité depuis 30 jours,
    ou quittées par les deux participants. Une conversation signalée et non traitée est gardée
    pour que l'équipe puisse la lire."""
    db = SessionLocal()
    try:
        limite = datetime.now(timezone.utc) - timedelta(days=DELAI_CONVERSATION_SANS_ANNONCE_JOURS)
        en_attente = (
            db.query(models.Signalement.conversation_id)
            .filter(models.Signalement.conversation_id != None, models.Signalement.traite == False)
        )
        db.query(models.Conversation).filter(
            ((models.Conversation.annonce_id == None) & (models.Conversation.dernier_message_at < limite))
            | ((models.Conversation.donneur_actif == False) & (models.Conversation.demandeur_actif == False)),
            ~models.Conversation.id.in_(en_attente),
        ).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


MAX_ANNONCES_PAR_EMAIL_ALERTE = 10


def _annonces_pour_alerte(db, alerte, depuis, jusqua):
    requete = db.query(models.Annonce).filter(
        models.Annonce.created_at > depuis,
        models.Annonce.created_at <= jusqua,
        models.Annonce.donne_at == None,
        models.Annonce.clerk_user_id != alerte.clerk_user_id,
        auteur_non_suspendu(),
    )
    if alerte.categorie:
        requete = requete.filter(models.Annonce.categorie == alerte.categorie)
    if alerte.quartier:
        requete = requete.filter(models.Annonce.quartier == alerte.quartier)
    if alerte.recherche:
        requete = requete.filter(filtre_recherche(alerte.recherche, models.Annonce.titre, models.Annonce.description))
    return requete.order_by(models.Annonce.created_at.desc()).limit(MAX_ANNONCES_PAR_EMAIL_ALERTE).all()


def libelle_alerte(alerte) -> str:
    morceaux = [f"« {alerte.recherche} »" if alerte.recherche else None, alerte.categorie, alerte.quartier]
    return " · ".join(m for m in morceaux if m)


# Alertes : un email part dès qu'un don correspondant est publié (le premier qui écrit
# récupère souvent l'objet), mais jamais plus d'un par heure et par personne, et jamais la nuit.
# Les dons publiés entre-temps sont regroupés dans l'envoi suivant (tâche horaire).
INTERVALLE_MIN_ALERTES = timedelta(hours=1)
HEURE_DEBUT_ALERTES, HEURE_FIN_ALERTES = 8, 22  # heure de Paris, fin exclue


def _heure_paris() -> int:
    return datetime.now(ZoneInfo("Europe/Paris")).hour


def alertes_autorisees() -> bool:
    return HEURE_DEBUT_ALERTES <= _heure_paris() < HEURE_FIN_ALERTES


def _email_alertes(email: str, annonces: list, criteres: list) -> None:
    frontend = emails.frontend_url()
    lignes = "".join(
        f'<p style="margin:0 0 10px"><a href="{frontend}/annonces/{a.id}" '
        f'style="color:#16a34a;font-weight:700;text-decoration:underline">{escape(a.titre)}</a>'
        f'<br/><span style="color:#6b7280;font-size:13px">{escape(a.quartier)} · '
        f'{escape(a.categorie)}</span></p>'
        for a in annonces
    )
    corps = (
        f"<p>De nouveaux dons correspondent à vos alertes "
        f"({escape(', '.join(criteres))}) :</p>{lignes}"
        f'<p style="margin-top:20px">{emails.bouton(f"{frontend}/annonces", "Voir les dons")}</p>'
    )
    pied = f'<a href="{frontend}/profil" style="color:#9ca3af">Gérer ou supprimer mes alertes</a>'
    titre = "Nouveau don" if len(annonces) == 1 else f"{len(annonces)} nouveaux dons"
    emails.envoyer(
        email,
        f"{titre} pour votre alerte GenDon",
        emails.gabarit("Un don correspond à votre recherche", corps, pied),
    )


def traiter_alertes_utilisateur(db, uid: str) -> None:
    """Envoie à un utilisateur, en un seul email, les nouveaux dons de toutes ses alertes,
    sauf s'il en a déjà reçu un dans l'heure. Commit inclus."""
    # Heure de la base, la même qui date les annonces (created_at) : pas de décalage d'horloge
    maintenant = db.query(func.now()).scalar()
    # Verrou sur ses alertes : deux publications simultanées n'envoient pas deux emails
    alertes = (
        db.query(models.Alerte)
        .filter(models.Alerte.clerk_user_id == uid)
        .order_by(models.Alerte.id)
        .with_for_update()
        .all()
    )
    if not alertes:
        db.commit()
        return
    dernier = max((a.dernier_envoi_at for a in alertes if a.dernier_envoi_at), default=None)
    if dernier and maintenant - dernier < INTERVALLE_MIN_ALERTES:
        db.commit()  # trop tôt : ces dons partiront dans l'envoi suivant
        return
    trouvees, criteres = {}, []
    for alerte in alertes:
        resultats = _annonces_pour_alerte(db, alerte, alerte.verifie_jusqu_a, maintenant)
        if resultats:
            criteres.append(libelle_alerte(alerte))
        for a in resultats:
            trouvees.setdefault(a.id, a)
    envoye = False
    if trouvees:
        email = clerk.email_utilisateur(uid)
        if email:
            _email_alertes(email, list(trouvees.values())[:MAX_ANNONCES_PAR_EMAIL_ALERTE], criteres)
            envoye = True
    for alerte in alertes:
        alerte.verifie_jusqu_a = maintenant
        if envoye:
            alerte.dernier_envoi_at = maintenant
    db.commit()


def alerter_nouvelle_annonce(annonce_id: int) -> None:
    """Après une publication (tâche de fond) : prévient tout de suite les personnes dont une
    alerte correspond, dans la limite du plafond horaire et hors de la nuit."""
    if not alertes_autorisees():
        return  # l'envoi de 8 h regroupera les dons de la nuit
    db = SessionLocal()
    try:
        annonce = db.query(models.Annonce).filter(models.Annonce.id == annonce_id).first()
        if not annonce:
            return
        candidats = {
            uid for (uid,) in db.query(models.Alerte.clerk_user_id)
            .filter(models.Alerte.clerk_user_id != annonce.clerk_user_id).distinct().all()
        }
        for uid in candidats:
            # Seuls ceux dont une alerte correspond à cette annonce : les autres attendent l'heure suivante
            if any(
                annonce.id in {a.id for a in _annonces_pour_alerte(db, alerte, alerte.verifie_jusqu_a, annonce.created_at)}
                for alerte in db.query(models.Alerte).filter(models.Alerte.clerk_user_id == uid).all()
            ):
                try:
                    traiter_alertes_utilisateur(db, uid)
                except Exception:
                    db.rollback()
    finally:
        db.close()


def envoyer_alertes():
    """Toutes les heures en journée : envoie ce qui n'a pas pu partir immédiatement (plafond horaire, nuit)."""
    if not alertes_autorisees():
        return
    db = SessionLocal()
    try:
        for (uid,) in db.query(models.Alerte.clerk_user_id).distinct().all():
            try:
                traiter_alertes_utilisateur(db, uid)
            except Exception:
                db.rollback()
    finally:
        db.close()


scheduler = BackgroundScheduler(daemon=True)


def planifier():
    """Enregistre les tâches et démarre le planificateur (au démarrage de l'API)."""
    # Horaires fixes (et non "toutes les 24 h") : un "interval" repart de zéro à chaque
    # redéploiement, et ne s'exécuterait jamais si l'on déploie plus d'une fois par jour.
    options = {"misfire_grace_time": 3600, "coalesce": True}
    scheduler.add_job(purger_annonces_expirees, CronTrigger(hour=3, minute=0, timezone="Europe/Paris"), **options)
    scheduler.add_job(purger_images_orphelines, CronTrigger(hour=3, minute=30, timezone="Europe/Paris"), **options)
    scheduler.add_job(purger_conversations, CronTrigger(hour=3, minute=15, timezone="Europe/Paris"), **options)
    scheduler.add_job(
        envoyer_alertes, CronTrigger(minute=5, timezone="Europe/Paris"), **options
    )
    scheduler.add_job(purger_journal_moderation, CronTrigger(hour=3, minute=45, timezone="Europe/Paris"), **options)
    scheduler.add_job(envoyer_rappels_expiration, CronTrigger(hour=10, minute=0, timezone="Europe/Paris"), **options)
    scheduler.add_job(nettoyer_rate_limit, "interval", minutes=30)
    scheduler.add_job(
        envoyer_newsletter_hebdo,
        CronTrigger(day_of_week="thu", hour=18, minute=30, timezone="Europe/Paris"),
        **options,
    )
    scheduler.start()
