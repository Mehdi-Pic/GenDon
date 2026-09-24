"""Le frontend et le backend doivent proposer exactement les mêmes catégories et quartiers.

C'est ce décalage ("Mobilier" côté site, "Immobilier" côté API) qui a bloqué
la publication en « Mobilier » pendant plus de trois mois.
"""
import re
from pathlib import Path

from app import schemas

FICHIER_FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "app" / "lib" / "annonces.ts"


def liste_frontend(nom: str) -> list:
    source = FICHIER_FRONTEND.read_text(encoding="utf-8")
    bloc = re.search(rf"export const {nom} = \[(.*?)\]", source, re.S)
    assert bloc, f"{nom} introuvable dans {FICHIER_FRONTEND}"
    return re.findall(r'"([^"]*)"', bloc.group(1))


def test_memes_categories():
    assert liste_frontend("CATEGORIES") == schemas.CATEGORIES


def test_memes_quartiers():
    assert liste_frontend("QUARTIERS") == schemas.QUARTIERS
