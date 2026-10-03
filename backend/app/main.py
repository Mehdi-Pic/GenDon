# API Gen Don (déploiement Railway)
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect as sa_inspect, text

load_dotenv()

from . import models  # noqa: E402
from .database import engine  # noqa: E402
from .photos import router as router_photos  # noqa: E402
from .routers import admin, annonces, comptes, contact, messagerie  # noqa: E402
from .taches import planifier, scheduler  # noqa: E402

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
    # La categorie "Immobilier" a ete renommee "Mobilier" (idempotent)
    conn.execute(text("UPDATE annonces SET categorie = 'Mobilier' WHERE categorie = 'Immobilier'"))
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
    if sa_inspect(engine).has_table("signalements"):
        type_raison = next(
            (str(c["type"]) for c in sa_inspect(engine).get_columns("signalements") if c["name"] == "raison"), ""
        )
        # Les signalements de conversation ajoutent un prefixe : 500 caracteres ne suffisaient plus
        if type_raison.upper().startswith("VARCHAR"):
            conn.execute(text("ALTER TABLE signalements ALTER COLUMN raison TYPE TEXT"))
            conn.commit()
    if sa_inspect(engine).has_table("messages"):
        col_msg = [c["name"] for c in sa_inspect(engine).get_columns("messages")]
        if "systeme" not in col_msg:
            conn.execute(text("ALTER TABLE messages ADD COLUMN systeme BOOLEAN NOT NULL DEFAULT FALSE"))
            conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    planifier()
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
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/")
def root():
    return {"message": "Gen Don API"}


for module in (router_photos, annonces.router, messagerie.router, admin.router, comptes.router, contact.router):
    app.include_router(module)
