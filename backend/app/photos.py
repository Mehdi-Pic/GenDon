"""Photos des annonces : nettoyage des métadonnées, envoi à Cloudinary, contrôle de propriété."""
import io
import os
from typing import List

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image, ImageOps, ImageSequence, UnidentifiedImageError
from sqlalchemy.orm import Session

from . import models
from .auth import get_current_user_id
from .database import get_db
from .outils import verifier_rate_limit

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

router = APIRouter()


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
            try:
                cloudinary.uploader.destroy(public_id)
            except Exception:
                pass  # image déjà absente ou Cloudinary indisponible : on ne bloque pas le reste


def valider_images(db: Session, user_id: str, images: list, deja_presentes: list = ()) -> None:
    """Une annonce ne peut contenir que des images envoyées par son auteur via /upload
    (ou déjà présentes dans l'annonce). Empêche de référencer, puis faire supprimer,
    les photos d'un autre utilisateur."""
    nouvelles = set(images or []) - set(deja_presentes or [])
    if not nouvelles:
        return
    connues = {
        url for (url,) in db.query(models.ImageUploadee.url)
        .filter(models.ImageUploadee.url.in_(nouvelles), models.ImageUploadee.clerk_user_id == user_id)
        .all()
    }
    if nouvelles - connues:
        raise HTTPException(status_code=400, detail="Image invalide : envoyez vos photos depuis le formulaire")


TYPES_IMAGE_AUTORISES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
FORMATS_IMAGE_AUTORISES = {"JPEG", "PNG", "WEBP", "GIF"}


def nettoyer_metadonnees(contenu: bytes) -> bytes:
    """Réencode l'image sans ses métadonnées (EXIF, GPS, XMP, commentaires).
    Une photo prise au téléphone contient souvent la position GPS de la prise de vue,
    c'est-à-dire, pour un don, le domicile du donneur."""
    try:
        with Image.open(io.BytesIO(contenu)) as image:
            format_image = image.format
            if format_image not in FORMATS_IMAGE_AUTORISES:
                raise HTTPException(status_code=400, detail="Format d'image non pris en charge")
            sortie = io.BytesIO()
            # Le profil de couleur n'est pas une donnée personnelle : on le garde pour ne pas ternir les photos
            profil = image.info.get("icc_profile")
            if format_image == "GIF":
                images = [trame.copy() for trame in ImageSequence.Iterator(image)]
                for trame in images:
                    trame.info.pop("comment", None)
                images[0].save(
                    sortie, format="GIF", save_all=True, append_images=images[1:],
                    loop=image.info.get("loop", 0), duration=image.info.get("duration", 100),
                )
            else:
                # Applique la rotation indiquée dans l'EXIF avant de le supprimer, sinon la photo s'afficherait couchée
                propre = ImageOps.exif_transpose(image)
                options = {"icc_profile": profil} if profil else {}
                if format_image in ("JPEG", "WEBP"):
                    options["quality"] = 92
                if format_image == "JPEG" and propre.mode not in ("RGB", "L", "CMYK"):
                    propre = propre.convert("RGB")
                if format_image == "PNG" and "transparency" in image.info:
                    options["transparency"] = image.info["transparency"]
                propre.save(sortie, format=format_image, **options)
            return sortie.getvalue()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(status_code=400, detail="Image illisible ou corrompue")
TAILLE_MAX_IMAGE = 10 * 1024 * 1024  # 10 Mo


# Fonction synchrone : FastAPI l'exécute dans un thread, Cloudinary et la base ne bloquent pas l'event loop
@router.post("/upload")
def upload_images(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 photos par annonce")
    # La limite compte les photos, pas les requêtes
    verifier_rate_limit(user_id, "upload", maximum=30, fenetre_secondes=3600, poids=len(files))
    urls = []
    for file in files:
        if file.content_type not in TYPES_IMAGE_AUTORISES:
            raise HTTPException(status_code=400, detail="Seules les images JPEG, PNG, WebP et GIF sont acceptées")
        contenu = file.file.read(TAILLE_MAX_IMAGE + 1)
        if len(contenu) > TAILLE_MAX_IMAGE:
            raise HTTPException(status_code=400, detail="Image trop volumineuse (max 10 Mo)")
        resultat = cloudinary.uploader.upload(
            nettoyer_metadonnees(contenu),
            folder="gendon",
            transformation=[{"quality": "auto", "fetch_format": "auto"}],
        )
        db.add(models.ImageUploadee(
            url=resultat["secure_url"], public_id=resultat["public_id"], clerk_user_id=user_id,
        ))
        db.commit()
        urls.append(resultat["secure_url"])
    return {"urls": urls}
