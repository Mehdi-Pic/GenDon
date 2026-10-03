"""Mise à jour du schéma de la base au démarrage de l'API (Alembic).

Avant Alembic, les tables étaient créées par create_all() et les colonnes ajoutées à la main
au démarrage. Une base de cette époque (sans table alembic_version) est d'abord complétée
par ces anciennes retouches, puis marquée « 0001 » ; les migrations suivantes s'appliquent
ensuite normalement. Toutes les tables existent déjà dans une telle base : l'ancien code
lançait create_all() à chaque démarrage.
"""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from .database import engine

DOSSIER_BACKEND = Path(__file__).resolve().parents[1]
REVISION_INITIALE = "0001"
# Verrou Postgres : deux instances qui démarrent ensemble ne migrent pas en même temps
CLE_VERROU = 7_216_430


def _config(connexion) -> Config:
    config = Config(str(DOSSIER_BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(DOSSIER_BACKEND / "migrations"))
    config.attributes["connexion"] = connexion
    return config


def _mettre_a_niveau_ancienne_base(conn) -> None:
    """Retouches qu'appliquait l'ancien code de démarrage (idempotentes)."""
    inspecteur = inspect(conn)

    def colonnes(table):
        return [c["name"] for c in inspecteur.get_columns(table)] if inspecteur.has_table(table) else None

    col_annonces = colonnes("annonces")
    for nom, ddl in (
        ("clerk_user_id", "VARCHAR(100)"),
        ("vues", "INTEGER NOT NULL DEFAULT 0"),
        ("rappel_envoye", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("donne_at", "TIMESTAMPTZ"),
    ):
        if nom not in col_annonces:
            conn.execute(text(f"ALTER TABLE annonces ADD COLUMN {nom} {ddl}"))
    conn.execute(text("UPDATE annonces SET categorie = 'Mobilier' WHERE categorie = 'Immobilier'"))
    col_conv = colonnes("conversations")
    if col_conv is not None:
        for nom in ("donneur_actif", "demandeur_actif"):
            if nom not in col_conv:
                conn.execute(text(f"ALTER TABLE conversations ADD COLUMN {nom} BOOLEAN NOT NULL DEFAULT TRUE"))
    if inspecteur.has_table("signalements"):
        type_raison = next(
            (str(c["type"]) for c in inspecteur.get_columns("signalements") if c["name"] == "raison"), ""
        )
        if type_raison.upper().startswith("VARCHAR"):
            conn.execute(text("ALTER TABLE signalements ALTER COLUMN raison TYPE TEXT"))
    col_msg = colonnes("messages")
    if col_msg is not None and "systeme" not in col_msg:
        conn.execute(text("ALTER TABLE messages ADD COLUMN systeme BOOLEAN NOT NULL DEFAULT FALSE"))
    # Le compteur démarre à 1 : un don avait déjà abouti avant l'ajout de cette fonctionnalité
    if not conn.execute(text("SELECT COUNT(*) FROM dons_realises")).scalar():
        conn.execute(text("INSERT INTO dons_realises (titre) VALUES ('Don realise avant le suivi')"))


def migrer() -> None:
    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(:cle)"), {"cle": CLE_VERROU})
        inspecteur = inspect(conn)
        config = _config(conn)
        if not inspecteur.has_table("alembic_version") and inspecteur.has_table("annonces"):
            _mettre_a_niveau_ancienne_base(conn)
            command.stamp(config, REVISION_INITIALE)
        command.upgrade(config, "head")
