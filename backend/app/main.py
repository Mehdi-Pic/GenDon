from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
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
import anyio.to_thread
import asyncio
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

scheduler = BackgroundScheduler(daemon=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # purger_annonces_expirees est défini plus bas (résolu au démarrage)
    scheduler.add_job(purger_annonces_expirees, "interval", hours=24)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Gen Don API", lifespan=lifespan)

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


def purger_annonces_expirees():
    db = SessionLocal()
    try:
        limite = datetime.now(timezone.utc) - timedelta(days=30)
        expirees = db.query(models.Annonce).filter(models.Annonce.created_at < limite).all()
        for annonce in expirees:
            supprimer_images_cloudinary(annonce.images or [])
            db.delete(annonce)
        if expirees:
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "Gen Don API"}


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
    query = db.query(models.Annonce)
    if categorie:
        query = query.filter(models.Annonce.categorie == categorie)
    if recherche:
        terme = f"%{recherche}%"
        query = query.filter(
            models.Annonce.titre.ilike(terme) | models.Annonce.description.ilike(terme)
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
    images_supprimees = set(annonce.images or []) - set(data.images or [])
    supprimer_images_cloudinary(list(images_supprimees))
    for key, value in data.model_dump().items():
        setattr(annonce, key, value)
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


class MessageContact(PydanticBase):
    message: str = Field(min_length=1, max_length=2000)


@app.post("/annonces/{annonce_id}/contact")
async def contacter_donneur(
    annonce_id: int,
    data: MessageContact,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    annonce = db.query(models.Annonce).filter(models.Annonce.id == annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    if not annonce.clerk_user_id:
        raise HTTPException(status_code=400, detail="Impossible de contacter ce donneur")
    if annonce.clerk_user_id == user_id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas contacter votre propre annonce")

    verifier_rate_limit(user_id, "contact", maximum=5, fenetre_secondes=3600)

    clerk_secret = os.getenv("CLERK_SECRET_KEY")
    headers_clerk = {"Authorization": f"Bearer {clerk_secret}"}

    async with httpx.AsyncClient(timeout=10) as client:
        donor_res, requester_res = await asyncio.gather(
            client.get(f"https://api.clerk.com/v1/users/{annonce.clerk_user_id}", headers=headers_clerk),
            client.get(f"https://api.clerk.com/v1/users/{user_id}", headers=headers_clerk),
        )

    if not donor_res.is_success or not requester_res.is_success:
        raise HTTPException(status_code=400, detail="Impossible de contacter ce donneur")

    donor = donor_res.json()
    requester = requester_res.json()

    def email_principal(user: dict):
        primary_id = user.get("primary_email_address_id")
        return next((e["email_address"] for e in user.get("email_addresses", []) if e["id"] == primary_id), None)

    donor_email = email_principal(donor)
    requester_email = email_principal(requester)

    if not donor_email:
        raise HTTPException(status_code=400, detail="Impossible de contacter ce donneur")

    requester_name = requester.get("username") or requester.get("first_name") or "Un habitant de Gennevilliers"

    resend.api_key = os.getenv("RESEND_API_KEY")

    email_payload = {
        "from": f"GenDon <{os.getenv('RESEND_FROM_EMAIL', 'onboarding@resend.dev')}>",
        "to": [donor_email],
        **({"reply_to": requester_email} if requester_email else {}),
        "subject": f"{requester_name} est intéressé(e) par votre don : {annonce.titre}",
        "html": f"""
        <div style="font-family:sans-serif;max-width:560px;margin:auto;color:#111">
          <p style="font-size:18px;font-weight:700;margin-bottom:4px">Quelqu'un veut votre don !</p>
          <p style="color:#6b7280;margin-top:0">via <strong>GenDon</strong> — Gennevilliers</p>
          <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0"/>
          <p><strong>{escape(requester_name)}</strong> est intéressé(e) par votre annonce :</p>
          <p style="background:#f9fafb;border-left:3px solid #16a34a;padding:12px 16px;border-radius:4px;font-weight:600">{escape(annonce.titre)}</p>
          <p>Son message :</p>
          <blockquote style="background:#f9fafb;border-left:3px solid #d1d5db;padding:12px 16px;margin:0;border-radius:4px;color:#374151">
            {escape(data.message)}
          </blockquote>
          <p style="margin-top:24px">Pour lui répondre, <strong>répondez simplement à cet email</strong>.</p>
          <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0"/>
          <p style="color:#9ca3af;font-size:12px">GenDon · Dons gratuits entre habitants de Gennevilliers</p>
        </div>
        """,
    }

    try:
        # Resend (basé sur requests, synchrone) → thread pour ne pas bloquer l'event loop
        await anyio.to_thread.run_sync(partial(resend.Emails.send, email_payload))
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur lors de l'envoi du message")

    return {"message": "Message envoyé"}


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
