# API Gen Don (déploiement Railway)
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, text, inspect as sa_inspect
from pydantic import BaseModel as PydanticBase, Field
from . import models, schemas
from .database import engine, get_db, SessionLocal
from .auth import get_current_user_id, get_user_id_optionnel
import httpx
import resend
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from typing import List
from datetime import datetime, timedelta, timezone
from math import ceil
from html import escape
from contextlib import asynccontextmanager
from collections import defaultdict, deque
from functools import partial
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from svix.webhooks import Webhook, WebhookVerificationError
from fastapi.responses import HTMLResponse
import hmac
import hashlib
import anyio.to_thread
import time
import os

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

# Création des tables + migration colonne clerk_user_id
models.Base.metadata.create_all(bind=engine)

with engine.connect() as conn:
    colonnes = [c["name"] for c in sa_inspect(engine).get_columns("annonces")]
    if "clerk_user_id" not in colonnes:
        conn.execute(text("ALTER TABLE annonces ADD COLUMN clerk_user_id VARCHAR(100)"))
        conn.commit()
    if "vues" not in colonnes:
        conn.execute(text("ALTER TABLE annonces ADD COLUMN vues INTEGER NOT NULL DEFAULT 0"))
        conn.commit()
    if "rappel_envoye" not in colonnes:
        conn.execute(text("ALTER TABLE annonces ADD COLUMN rappel_envoye BOOLEAN NOT NULL DEFAULT FALSE"))
        conn.commit()
    if "donne_at" not in colonnes:
        conn.execute(text("ALTER TABLE annonces ADD COLUMN donne_at TIMESTAMPTZ"))
        conn.commit()
    # Le compteur demarre a 1 : un don avait deja abouti avant l'ajout de cette fonctionnalite
    if sa_inspect(engine).has_table("dons_realises"):
        deja = conn.execute(text("SELECT COUNT(*) FROM dons_realises")).scalar()
        if not deja:
            conn.execute(text("INSERT INTO dons_realises (titre) VALUES ('Don realise avant le suivi')"))
            conn.commit()
    if sa_inspect(engine).has_table("conversations"):
        col_conv = [c["name"] for c in sa_inspect(engine).get_columns("conversations")]
        if "donneur_actif" not in col_conv:
            conn.execute(text("ALTER TABLE conversations ADD COLUMN donneur_actif BOOLEAN NOT NULL DEFAULT TRUE"))
            conn.commit()
        if "demandeur_actif" not in col_conv:
            conn.execute(text("ALTER TABLE conversations ADD COLUMN demandeur_actif BOOLEAN NOT NULL DEFAULT TRUE"))
            conn.commit()
    if sa_inspect(engine).has_table("messages"):
        col_msg = [c["name"] for c in sa_inspect(engine).get_columns("messages")]
        if "systeme" not in col_msg:
            conn.execute(text("ALTER TABLE messages ADD COLUMN systeme BOOLEAN NOT NULL DEFAULT FALSE"))
            conn.commit()

scheduler = BackgroundScheduler(daemon=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Les jobs sont définis plus bas (résolus au démarrage)
    scheduler.add_job(purger_annonces_expirees, "interval", hours=24)
    scheduler.add_job(envoyer_rappels_expiration, "interval", hours=24)
    scheduler.add_job(
        envoyer_newsletter_hebdo,
        CronTrigger(day_of_week="thu", hour=18, minute=30, timezone="Europe/Paris"),
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


# Documentation API désactivée en production (exposer /docs révèle toute la structure,
# y compris les routes admin). Activable en local via ENABLE_DOCS=1.
_docs_actifs = os.getenv("ENABLE_DOCS") == "1"
app = FastAPI(
    title="Gen Don API",
    lifespan=lifespan,
    docs_url="/docs" if _docs_actifs else None,
    redoc_url="/redoc" if _docs_actifs else None,
    openapi_url="/openapi.json" if _docs_actifs else None,
)

_origins = ["http://localhost:3000"]
for _url in os.getenv("FRONTEND_URL", "").split(","):
    _url = _url.strip()
    if _url:
        _origins.append(_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


# Rate limiting en mémoire par utilisateur (1 seule instance Railway).
_appels: dict = defaultdict(deque)


def verifier_rate_limit(user_id: str, action: str, maximum: int, fenetre_secondes: int) -> None:
    cle = f"{action}:{user_id}"
    maintenant = time.monotonic()
    appels = _appels[cle]
    while appels and maintenant - appels[0] > fenetre_secondes:
        appels.popleft()
    if len(appels) >= maximum:
        raise HTTPException(status_code=429, detail="Trop de requêtes, réessayez plus tard")
    appels.append(maintenant)


def echapper_like(terme: str) -> str:
    """Neutralise les jokers LIKE (% et _) pour qu'ils soient cherchés littéralement."""
    return terme.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def extraire_public_id(url: str) -> str:
    """Extrait le public_id Cloudinary depuis une URL. Fonctionne pour le dossier gendon/."""
    try:
        apres_upload = url.split("/upload/")[1]
        idx = apres_upload.find("gendon/")
        if idx == -1:
            return ""
        return apres_upload[idx:].rsplit(".", 1)[0]  # gendon/filename sans extension
    except Exception:
        return ""


def supprimer_images_cloudinary(urls: list) -> None:
    for url in urls:
        public_id = extraire_public_id(url)
        if public_id:
            cloudinary.uploader.destroy(public_id)


def verifier_proprietaire(annonce: models.Annonce, user_id: str) -> None:
    if not annonce.clerk_user_id or annonce.clerk_user_id != user_id:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas le propriétaire de cette annonce")


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
        for annonce in expirees:
            supprimer_images_cloudinary(annonce.images or [])
            db.delete(annonce)
        if expirees:
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _email_principal(user: dict):
    primary_id = user.get("primary_email_address_id")
    return next((e["email_address"] for e in user.get("email_addresses", []) if e["id"] == primary_id), None)


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
                        email = _email_principal(res.json())
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


# ---------- Newsletter hebdomadaire (jeudi 18h30) ----------

def _vignette_email(url: str, largeur: int = 320) -> str:
    """Version réduite d'une image Cloudinary pour l'email."""
    return url.replace("/upload/", f"/upload/w_{largeur},q_auto,f_auto/") if "/upload/" in url else url


def _cle_desabonnement() -> bytes:
    return (os.getenv("NEWSLETTER_SECRET") or os.getenv("CLERK_SECRET_KEY") or "gendon").encode()


def _token_desabonnement(user_id: str) -> str:
    signature = hmac.new(_cle_desabonnement(), user_id.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{user_id}.{signature}"


def _verifier_token_desabonnement(token: str):
    try:
        user_id, signature = token.rsplit(".", 1)
    except ValueError:
        return None
    attendu = hmac.new(_cle_desabonnement(), user_id.encode(), hashlib.sha256).hexdigest()[:32]
    return user_id if hmac.compare_digest(signature, attendu) else None


def _tous_les_utilisateurs_clerk() -> list:
    """Récupère tous les comptes Clerk (pagination par lots de 100)."""
    headers = {"Authorization": f"Bearer {os.getenv('CLERK_SECRET_KEY')}"}
    utilisateurs, offset = [], 0
    while offset <= 2000:
        try:
            r = httpx.get(
                f"https://api.clerk.com/v1/users?limit=100&offset={offset}",
                headers=headers,
                timeout=15,
            )
        except Exception:
            break
        if not r.is_success:
            break
        lot = r.json()
        utilisateurs.extend(lot)
        if len(lot) < 100:
            break
        offset += 100
    return utilisateurs


def envoyer_newsletter_hebdo():
    """Chaque jeudi 18h30 : rappel du principe du don + les 5 dernières annonces."""
    db = SessionLocal()
    try:
        annonces = (
            db.query(models.Annonce)
            .filter(models.Annonce.donne_at == None)
            .order_by(models.Annonce.created_at.desc())
            .limit(5)
            .all()
        )
        if not annonces:
            return  # rien à annoncer, on n'envoie pas d'email vide

        desabonnes = {d.clerk_user_id for d in db.query(models.DesabonnementNewsletter).all()}
        utilisateurs = _tous_les_utilisateurs_clerk()
        if not utilisateurs:
            return

        frontend = os.getenv("FRONTEND_URL", "").split(",")[0].strip() or "https://www.gendon.fr"
        resend.api_key = os.getenv("RESEND_API_KEY")

        cartes = ""
        for a in annonces:
            image = _vignette_email(a.images[0]) if a.images else None
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

        for u in utilisateurs:
            uid = u.get("id")
            if not uid or uid in desabonnes:
                continue
            email = _email_principal(u)
            if not email:
                continue
            lien_desabo = f"{frontend}/desabonnement?token={_token_desabonnement(uid)}"
            try:
                resend.Emails.send({
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
            except Exception:
                continue
    except Exception:
        pass
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "Gen Don API"}


def purger_donnees_utilisateur(db: Session, clerk_user_id: str):
    """Efface toutes les données GenDon liées à un utilisateur (RGPD / suppression de compte)."""
    annonces = db.query(models.Annonce).filter(models.Annonce.clerk_user_id == clerk_user_id).all()
    for annonce in annonces:
        supprimer_images_cloudinary(annonce.images or [])
        db.delete(annonce)  # favoris et signalements liés partent en cascade
    db.query(models.Favori).filter(models.Favori.clerk_user_id == clerk_user_id).delete()
    db.query(models.Signalement).filter(models.Signalement.clerk_user_id == clerk_user_id).delete()
    db.query(models.Role).filter(models.Role.clerk_user_id == clerk_user_id).delete()
    db.query(models.DesabonnementNewsletter).filter(
        models.DesabonnementNewsletter.clerk_user_id == clerk_user_id
    ).delete()
    conversations = (
        db.query(models.Conversation)
        .filter(
            (models.Conversation.donneur_id == clerk_user_id)
            | (models.Conversation.demandeur_id == clerk_user_id)
        )
        .all()
    )
    for conv in conversations:
        db.delete(conv)  # messages liés partent en cascade
    db.commit()


@app.post("/webhooks/clerk")
async def webhook_clerk(request: Request, db: Session = Depends(get_db)):
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

    if evenement.get("type") == "user.deleted":
        uid = (evenement.get("data") or {}).get("id")
        if uid:
            purger_donnees_utilisateur(db, uid)
    return {"recu": True}


TYPES_IMAGE_AUTORISES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
TAILLE_MAX_IMAGE = 10 * 1024 * 1024  # 10 Mo


@app.post("/upload")
async def upload_images(
    files: List[UploadFile] = File(...),
    user_id: str = Depends(get_current_user_id),
):
    verifier_rate_limit(user_id, "upload", maximum=20, fenetre_secondes=3600)
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 photos par annonce")
    urls = []
    for file in files:
        if file.content_type not in TYPES_IMAGE_AUTORISES:
            raise HTTPException(status_code=400, detail="Seules les images JPEG, PNG, WebP et GIF sont acceptées")
        contenu = await file.read()
        if len(contenu) > TAILLE_MAX_IMAGE:
            raise HTTPException(status_code=400, detail="Image trop volumineuse (max 10 Mo)")
        # Appel Cloudinary synchrone → thread pour ne pas bloquer l'event loop
        resultat = await anyio.to_thread.run_sync(
            partial(
                cloudinary.uploader.upload,
                contenu,
                folder="gendon",
                transformation=[{"quality": "auto", "fetch_format": "auto"}],
            )
        )
        urls.append(resultat["secure_url"])
    return {"urls": urls}


@app.post("/annonces", response_model=schemas.AnnonceResponse)
def créer_annonce(
    annonce: schemas.AnnonceCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    db_annonce = models.Annonce(**annonce.model_dump(), clerk_user_id=user_id)
    db.add(db_annonce)
    db.commit()
    db.refresh(db_annonce)
    return db_annonce


LIMITE_PAR_PAGE = 18

@app.get("/annonces", response_model=schemas.AnnoncesPaginées)
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
    if user_id:
        # L'utilisateur connecté ne voit pas ses propres annonces dans le listing
        query = query.filter(
            (models.Annonce.clerk_user_id != user_id) |
            (models.Annonce.clerk_user_id == None)
        )
    if photos:
        query = query.filter(func.cardinality(models.Annonce.images) > 0)
    if periode == "semaine":
        query = query.filter(models.Annonce.created_at >= datetime.now(timezone.utc) - timedelta(days=7))
    elif periode == "mois":
        query = query.filter(models.Annonce.created_at >= datetime.now(timezone.utc) - timedelta(days=30))
    if tri == "ancien":
        query = query.order_by(models.Annonce.created_at.asc())
    else:
        query = query.order_by(models.Annonce.created_at.desc())
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
    return {"annonces": annonces, "total": total, "pages": ceil(total / LIMITE_PAR_PAGE) if total > 0 else 1, "page": page}


@app.get("/annonces/me", response_model=list[schemas.AnnonceResponse])
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


@app.get("/annonces/{annonce_id}", response_model=schemas.AnnonceResponse)
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


@app.patch("/annonces/{annonce_id}", response_model=schemas.AnnonceResponse)
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
    images_supprimees = set(annonce.images or []) - set(data.images or [])
    supprimer_images_cloudinary(list(images_supprimees))
    for key, value in data.model_dump().items():
        setattr(annonce, key, value)
    db.commit()
    db.refresh(annonce)
    return annonce


# Une annonce vit 30 jours ; elle est renouvelable une fois passe ce delai d'anciennete
DUREE_VIE_JOURS = 30
RENOUVELABLE_APRES_JOURS = 7


@app.post("/annonces/{annonce_id}/renouveler", response_model=schemas.AnnonceResponse)
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


@app.post("/annonces/{annonce_id}/donne", response_model=schemas.AnnonceResponse)
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
    if annonce.donne_at:
        raise HTTPException(status_code=400, detail="Ce don est deja enregistre")

    annonce.donne_at = datetime.now(timezone.utc)
    # Trace independante de l'annonce : le compteur survit a la purge des 3 jours
    db.add(models.DonRealise(clerk_user_id=user_id, titre=annonce.titre[:100]))
    db.commit()
    db.refresh(annonce)
    return annonce


@app.post("/annonces/{annonce_id}/vue")
def compter_vue(
    annonce_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id_optionnel),
):
    """Appelé par le navigateur à l'affichage réel de la page (pas par les bots/prefetch/metadata)."""
    annonce = db.query(models.Annonce).filter(models.Annonce.id == annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    if user_id and annonce.clerk_user_id == user_id:
        return {"comptee": False}
    db.query(models.Annonce).filter(models.Annonce.id == annonce_id).update(
        {models.Annonce.vues: models.Annonce.vues + 1}
    )
    db.commit()
    return {"comptee": True}


@app.post("/annonces/{annonce_id}/favori")
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
        db.commit()
    return {"est_favori": True}


@app.delete("/annonces/{annonce_id}/favori")
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


@app.get("/favoris", response_model=list[schemas.AnnonceResponse])
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


@app.post("/annonces/{annonce_id}/signaler")
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
        db.commit()
    return {"message": "Signalement enregistré"}


# ---------- Administration ----------
# La sécurité est entièrement côté serveur : identité prouvée par le JWT Clerk,
# rôle lu en base (+ ADMIN_USER_ID en variable d'environnement pour l'admin principal).

def _admins_principaux() -> list:
    """IDs admin définis sur Railway (ADMIN_USER_ID), séparés par des virgules."""
    return [a.strip() for a in os.getenv("ADMIN_USER_ID", "").split(",") if a.strip()]


def _role_utilisateur(db: Session, user_id: str):
    if user_id and user_id in _admins_principaux():
        return "admin"
    ligne = db.query(models.Role).filter(models.Role.clerk_user_id == user_id).first()
    return ligne.role if ligne else None


def exiger_moderateur(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    role = _role_utilisateur(db, user_id)
    if role not in ("admin", "moderateur"):
        raise HTTPException(status_code=403, detail="Accès réservé")
    return {"user_id": user_id, "role": role}


def exiger_admin(acteur: dict = Depends(exiger_moderateur)) -> dict:
    if acteur["role"] != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    return acteur


def journaliser(db: Session, user_id: str, action: str, details: str = ""):
    db.add(models.ActionModeration(clerk_user_id=user_id, action=action, details=details))
    db.commit()


@app.get("/admin/moi")
def admin_moi(acteur: dict = Depends(exiger_moderateur)):
    return {"role": acteur["role"]}


@app.get("/admin/stats")
def admin_stats(db: Session = Depends(get_db), acteur: dict = Depends(exiger_moderateur)):
    il_y_a_7_jours = datetime.now(timezone.utc) - timedelta(days=7)
    return {
        "annonces": db.query(models.Annonce).count(),
        "annonces_semaine": db.query(models.Annonce).filter(models.Annonce.created_at >= il_y_a_7_jours).count(),
        "vues_totales": db.query(func.coalesce(func.sum(models.Annonce.vues), 0)).scalar(),
        "favoris": db.query(models.Favori).count(),
        "dons_realises": db.query(models.DonRealise).count(),
        "signalements_en_attente": db.query(models.Signalement).filter(models.Signalement.traite == False).count(),
    }


@app.get("/admin/annonces", response_model=schemas.AnnoncesPaginées)
def admin_lister_annonces(
    recherche: str = None,
    page: int = 1,
    db: Session = Depends(get_db),
    acteur: dict = Depends(exiger_moderateur),
):
    page = max(1, page)
    query = db.query(models.Annonce)
    if recherche:
        terme = f"%{echapper_like(recherche.strip()[:100])}%"
        query = query.filter(
            models.Annonce.titre.ilike(terme, escape="\\")
            | models.Annonce.description.ilike(terme, escape="\\")
            | models.Annonce.pseudo.ilike(terme, escape="\\")
        )
    query = query.order_by(models.Annonce.created_at.desc())
    total = query.count()
    annonces = query.offset((page - 1) * LIMITE_PAR_PAGE).limit(LIMITE_PAR_PAGE).all()
    return {"annonces": annonces, "total": total, "pages": ceil(total / LIMITE_PAR_PAGE) if total > 0 else 1, "page": page}


@app.delete("/admin/annonces/{annonce_id}")
def admin_supprimer_annonce(
    annonce_id: int,
    db: Session = Depends(get_db),
    acteur: dict = Depends(exiger_moderateur),
):
    annonce = db.query(models.Annonce).filter(models.Annonce.id == annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    journaliser(db, acteur["user_id"], "suppression_annonce", f"#{annonce_id} « {annonce.titre} » de {annonce.pseudo}")
    supprimer_images_cloudinary(annonce.images or [])
    db.delete(annonce)
    db.commit()
    return {"message": "Annonce supprimée"}


@app.get("/admin/utilisateurs")
async def admin_lister_utilisateurs(
    db: Session = Depends(get_db),
    acteur: dict = Depends(exiger_moderateur),
):
    headers_clerk = {"Authorization": f"Bearer {os.getenv('CLERK_SECRET_KEY')}"}
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get("https://api.clerk.com/v1/users?limit=100&order_by=-created_at", headers=headers_clerk)
    if not res.is_success:
        raise HTTPException(status_code=502, detail="Impossible de récupérer les utilisateurs")
    comptes = dict(
        db.query(models.Annonce.clerk_user_id, func.count(models.Annonce.id))
        .group_by(models.Annonce.clerk_user_id)
        .all()
    )
    roles = {r.clerk_user_id: r.role for r in db.query(models.Role).all()}
    admins = _admins_principaux()
    utilisateurs = []
    for u in res.json():
        uid = u["id"]
        utilisateurs.append({
            "id": uid,
            "pseudo": u.get("username") or u.get("first_name") or "(sans pseudo)",
            "email": _email_principal(u),
            "image": u.get("image_url"),
            "created_at": u.get("created_at"),
            "nb_annonces": comptes.get(uid, 0),
            "role": "admin" if uid in admins else roles.get(uid),
            "est_admin_principal": uid in admins,
        })
    return utilisateurs


class RoleUpdate(PydanticBase):
    role: str = Field(pattern="^(moderateur|aucun)$")


@app.post("/admin/utilisateurs/{uid}/role")
def admin_changer_role(
    uid: str,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    acteur: dict = Depends(exiger_admin),
):
    if uid in _admins_principaux():
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
    return {"role": None if data.role == "aucun" else data.role}


@app.get("/admin/signalements")
def admin_lister_signalements(
    db: Session = Depends(get_db),
    acteur: dict = Depends(exiger_moderateur),
):
    lignes = (
        db.query(models.Signalement, models.Annonce.titre)
        .outerjoin(models.Annonce, models.Annonce.id == models.Signalement.annonce_id)
        .order_by(models.Signalement.traite.asc(), models.Signalement.created_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": s.id,
            "annonce_id": s.annonce_id,
            "annonce_titre": titre,
            "raison": s.raison,
            "traite": s.traite,
            "created_at": s.created_at,
        }
        for s, titre in lignes
    ]


@app.patch("/admin/signalements/{signalement_id}/traiter")
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


@app.get("/admin/journal")
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
    return [
        {"id": l.id, "par": l.clerk_user_id, "action": l.action, "details": l.details, "created_at": l.created_at}
        for l in lignes
    ]


# ---------- Messagerie (chat) ----------

def _est_participant(conv, user_id: str) -> bool:
    return user_id in (conv.donneur_id, conv.demandeur_id)


async def _pseudo_clerk(user_id: str) -> str:
    """Récupère le pseudo d'affichage d'un utilisateur via Clerk (au démarrage d'une conversation)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"https://api.clerk.com/v1/users/{user_id}",
                headers={"Authorization": f"Bearer {os.getenv('CLERK_SECRET_KEY')}"},
            )
        if r.is_success:
            u = r.json()
            return u.get("username") or u.get("first_name") or "Un habitant"
    except Exception:
        pass
    return "Un habitant"


async def _notifier_nouveau_message(destinataire_id: str, expediteur_pseudo: str, annonce_titre: str, conversation_id: int):
    """Email 'nouveau message' au destinataire (best-effort, jamais bloquant)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"https://api.clerk.com/v1/users/{destinataire_id}",
                headers={"Authorization": f"Bearer {os.getenv('CLERK_SECRET_KEY')}"},
            )
        if not r.is_success:
            return
        email = _email_principal(r.json())
        if not email:
            return
        frontend = os.getenv("FRONTEND_URL", "").split(",")[0].strip() or "https://www.gendon.fr"
        resend.api_key = os.getenv("RESEND_API_KEY")
        payload = {
            "from": f"GenDon <{os.getenv('RESEND_FROM_EMAIL', 'onboarding@resend.dev')}>",
            "to": [email],
            "subject": f"Nouveau message de {expediteur_pseudo} sur GenDon",
            "html": f"""
            <div style="font-family:sans-serif;max-width:560px;margin:auto;color:#111">
              <p style="font-size:18px;font-weight:700;margin-bottom:4px">Vous avez un nouveau message</p>
              <p style="color:#6b7280;margin-top:0">via <strong>GenDon</strong> · Gennevilliers</p>
              <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0"/>
              <p><strong>{escape(expediteur_pseudo)}</strong> vous a écrit à propos de :</p>
              <p style="background:#f9fafb;border-left:3px solid #16a34a;padding:12px 16px;border-radius:4px;font-weight:600">{escape(annonce_titre)}</p>
              <p style="margin-top:24px">
                <a href="{frontend}/messages/{conversation_id}" style="background:#16a34a;color:#fff;text-decoration:none;padding:11px 22px;border-radius:9999px;font-weight:600;display:inline-block">Voir la conversation</a>
              </p>
              <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0"/>
              <p style="color:#9ca3af;font-size:12px">GenDon · Dons gratuits entre habitants de Gennevilliers</p>
            </div>
            """,
        }
        await anyio.to_thread.run_sync(partial(resend.Emails.send, payload))
    except Exception:
        pass


class ConversationCreate(PydanticBase):
    annonce_id: int


class MessageCreate(PydanticBase):
    contenu: str = Field(min_length=1, max_length=2000)


@app.post("/conversations")
async def demarrer_conversation(
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

    demandeur_pseudo = await _pseudo_clerk(user_id)
    conv = models.Conversation(
        annonce_id=data.annonce_id,
        donneur_id=annonce.clerk_user_id,
        demandeur_id=user_id,
        donneur_pseudo=(annonce.pseudo or "Un habitant")[:50],
        demandeur_pseudo=demandeur_pseudo[:50],
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {"id": conv.id}


@app.get("/conversations")
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
    resultat = []
    for c in convs:
        dernier = (
            db.query(models.Message)
            .filter(models.Message.conversation_id == c.id)
            .order_by(models.Message.created_at.desc())
            .first()
        )
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


@app.get("/conversations/{conversation_id}/messages")
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


@app.post("/conversations/{conversation_id}/messages")
async def envoyer_message(
    conversation_id: int,
    data: MessageCreate,
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
        await _notifier_nouveau_message(destinataire_id, expediteur_pseudo, annonce_titre, conversation_id)

    return {"id": msg.id, "contenu": msg.contenu, "created_at": msg.created_at, "a_moi": True, "systeme": False}


@app.post("/conversations/{conversation_id}/lu")
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


@app.get("/messages/non-lus")
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


@app.delete("/conversations/{conversation_id}")
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


@app.post("/conversations/{conversation_id}/signaler")
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
    # Rattaché à l'annonce de la conversation pour apparaître dans le panel admin existant
    raison = f"[Conversation] {data.raison.strip()}"
    existant = (
        db.query(models.Signalement)
        .filter(models.Signalement.clerk_user_id == user_id, models.Signalement.annonce_id == conv.annonce_id)
        .first()
    )
    if existant:
        existant.raison = raison
        existant.traite = False
    else:
        db.add(models.Signalement(annonce_id=conv.annonce_id, clerk_user_id=user_id, raison=raison))
    db.commit()
    return {"ok": True}


@app.delete("/annonces/{annonce_id}")
def supprimer_annonce(
    annonce_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    annonce = db.query(models.Annonce).filter(models.Annonce.id == annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    verifier_proprietaire(annonce, user_id)
    supprimer_images_cloudinary(annonce.images or [])
    db.delete(annonce)
    db.commit()
    return {"message": "Annonce supprimée"}


# ---------- Désabonnement newsletter (public, via lien signé dans l'email) ----------

class DesabonnementRequete(PydanticBase):
    token: str


@app.post("/newsletter/desabonnement")
def desabonner_newsletter(data: DesabonnementRequete, db: Session = Depends(get_db)):
    uid = _verifier_token_desabonnement(data.token)
    if not uid:
        raise HTTPException(status_code=400, detail="Lien de désabonnement invalide ou expiré")
    existe = (
        db.query(models.DesabonnementNewsletter)
        .filter(models.DesabonnementNewsletter.clerk_user_id == uid)
        .first()
    )
    if not existe:
        db.add(models.DesabonnementNewsletter(clerk_user_id=uid))
        db.commit()
    return {"ok": True}


# ---------- Contact : écrit à l'équipe (admins + modérateurs) ----------

class MessageContactSite(PydanticBase):
    nom: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=5, max_length=120)
    sujet: str = Field(min_length=3, max_length=120)
    message: str = Field(min_length=10, max_length=2000)
    # Champ piege : invisible pour un humain, souvent rempli par les robots
    site_web: str = Field(default="", max_length=200)


def _emails_equipe(db: Session) -> list:
    """Emails des administrateurs (variable Railway) et des modérateurs (table roles)."""
    identifiants = set(_admins_principaux())
    identifiants.update(r.clerk_user_id for r in db.query(models.Role).all())
    headers = {"Authorization": f"Bearer {os.getenv('CLERK_SECRET_KEY')}"}
    emails = []
    for uid in identifiants:
        try:
            r = httpx.get(f"https://api.clerk.com/v1/users/{uid}", headers=headers, timeout=10)
            if r.is_success:
                adresse = _email_principal(r.json())
                if adresse:
                    emails.append(adresse)
        except Exception:
            continue
    return emails


@app.post("/contact")
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
    if "@" not in expediteur or "." not in expediteur.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Adresse email invalide")

    # Anti-spam : par compte si connecté, sinon par adresse IP
    cle = user_id or (request.client.host if request.client else "inconnu")
    verifier_rate_limit(cle, "contact_site", maximum=3, fenetre_secondes=3600)

    destinataires = _emails_equipe(db)
    if not destinataires:
        raise HTTPException(status_code=503, detail="Aucun contact disponible pour le moment")

    resend.api_key = os.getenv("RESEND_API_KEY")
    try:
        resend.Emails.send({
            "from": f"GenDon <{os.getenv('RESEND_FROM_EMAIL', 'onboarding@resend.dev')}>",
            "to": destinataires,
            "reply_to": expediteur,
            "subject": f"[Contact GenDon] {data.sujet.strip()}",
            "html": f"""
            <div style="font-family:sans-serif;max-width:560px;margin:auto;color:#111">
              <p style="font-size:18px;font-weight:700;margin-bottom:4px">Nouveau message via le formulaire de contact</p>
              <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0"/>
              <p><strong>De :</strong> {escape(data.nom.strip())} ({escape(expediteur)})</p>
              <p><strong>Sujet :</strong> {escape(data.sujet.strip())}</p>
              <p><strong>Message :</strong></p>
              <blockquote style="background:#f9fafb;border-left:3px solid #d1d5db;padding:12px 16px;margin:0;border-radius:4px;color:#374151;white-space:pre-wrap">{escape(data.message.strip())}</blockquote>
              <p style="margin-top:20px;color:#6b7280;font-size:13px">Répondez directement à cet email pour joindre l'expéditeur.</p>
            </div>
            """,
        })
    except Exception:
        raise HTTPException(status_code=500, detail="L'envoi du message a échoué")
    return {"ok": True}
