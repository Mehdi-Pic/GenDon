# API Gen Don (déploiement Railway)
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from .migrations import migrer  # noqa: E402
from .photos import router as router_photos  # noqa: E402
from .routers import admin, alertes, annonces, comptes, contact, messagerie  # noqa: E402
from .taches import planifier, scheduler  # noqa: E402

# Schéma de la base à jour avant de servir la moindre requête
migrer()


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


for module in (router_photos, annonces.router, messagerie.router, admin.router, comptes.router, contact.router,
               alertes.router):
    app.include_router(module)
