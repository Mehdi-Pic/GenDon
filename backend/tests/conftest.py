"""Configuration commune des tests.

Les tests tournent sur une base Postgres DEDIEE, jamais sur la production :
ils vident toutes les tables avant chaque test. L'adresse est lue dans
TEST_DATABASE_URL (ex. postgresql://postgres:postgres@localhost:5432/gendon_test).
"""
import os

import pytest

url_test = os.getenv("TEST_DATABASE_URL")
if not url_test:
    pytest.exit("TEST_DATABASE_URL n'est pas defini : les tests ont besoin d'une base Postgres dediee.", returncode=2)
if "rlwy.net" in url_test or "railway.internal" in url_test:
    pytest.exit("TEST_DATABASE_URL pointe vers Railway : refuse (les tests effacent la base).", returncode=2)

# Avant tout import de l'application : database.py lit DATABASE_URL au chargement
os.environ["DATABASE_URL"] = url_test
os.environ["NEWSLETTER_SECRET"] = "secret-de-test"
os.environ.pop("CLERK_AUTHORIZED_PARTIES", None)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import app.main as main  # noqa: E402
from app import models  # noqa: E402
from app.auth import get_current_user_id, get_user_id_optionnel  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402


class FauxServices:
    """Remplace Clerk, Cloudinary et Resend : aucun appel réseau pendant les tests."""

    def __init__(self):
        self.uploads = 0
        self.contenus_envoyes = []  # octets réellement transmis à Cloudinary
        self.images_detruites = []
        self.notifications = []
        self.lots_newsletter = []

    def upload(self, contenu, **kwargs):
        self.contenus_envoyes.append(contenu)
        self.uploads += 1
        n = self.uploads
        return {
            "secure_url": f"https://res.cloudinary.com/test/image/upload/v1/gendon/img{n}.jpg",
            "public_id": f"gendon/img{n}",
        }

    def destroy(self, public_id):
        self.images_detruites.append(public_id)


@pytest.fixture(autouse=True)
def base_vide():
    """Chaque test démarre sur une base vide et un rate limit remis à zéro."""
    tables = ", ".join(t.name for t in models.Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    main._appels.clear()
    main._cache_emails_equipe.update(emails=[], expire=0.0)
    yield


@pytest.fixture
def services(monkeypatch):
    faux = FauxServices()
    monkeypatch.setattr(main.cloudinary.uploader, "upload", faux.upload)
    monkeypatch.setattr(main.cloudinary.uploader, "destroy", faux.destroy)
    monkeypatch.setattr(main, "_pseudo_clerk", lambda uid: f"pseudo-{uid}")
    monkeypatch.setattr(main, "_notifier_nouveau_message", lambda *args: faux.notifications.append(args))
    monkeypatch.setattr(main.resend.Batch, "send", lambda lot, options: faux.lots_newsletter.append((lot, options)))
    monkeypatch.setattr(main.time, "sleep", lambda secondes: None)
    return faux


class Utilisateur:
    """Change l'utilisateur connecté : utilisateur.uid = "u2", ou None pour un visiteur."""

    def __init__(self):
        self.uid = "u1"


@pytest.fixture
def utilisateur():
    u = Utilisateur()
    main.app.dependency_overrides[get_current_user_id] = lambda: u.uid
    main.app.dependency_overrides[get_user_id_optionnel] = lambda: u.uid
    yield u
    main.app.dependency_overrides.clear()


@pytest.fixture
def client(services, utilisateur):
    return TestClient(main.app)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()
