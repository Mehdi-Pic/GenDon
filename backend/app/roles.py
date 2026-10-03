"""Rôles de l'équipe. La sécurité est entièrement côté serveur : identité prouvée par le JWT Clerk,
rôle lu en base (+ ADMIN_USER_ID en variable d'environnement pour l'admin principal)."""
import os

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from . import models
from .auth import get_current_user_id
from .database import get_db


def admins_principaux() -> list:
    """IDs admin définis sur Railway (ADMIN_USER_ID), séparés par des virgules."""
    return [a.strip() for a in os.getenv("ADMIN_USER_ID", "").split(",") if a.strip()]


def role_utilisateur(db: Session, user_id: str):
    if user_id and user_id in admins_principaux():
        return "admin"
    ligne = db.query(models.Role).filter(models.Role.clerk_user_id == user_id).first()
    return ligne.role if ligne else None


def exiger_moderateur(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    role = role_utilisateur(db, user_id)
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
