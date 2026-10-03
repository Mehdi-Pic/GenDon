from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from starlette.requests import Request

from app import clerk, emails, main, models, outils, taches
from app.routers import comptes

from helpers import publier, uploader


# ---------- Suppression de compte / changement de pseudo (webhook Clerk) ----------

def test_suppression_de_compte(client, utilisateur, services, db):
    url = uploader(client)[0]
    a = publier(client, images=[url])
    client.post(f"/annonces/{a['id']}/donne")
    utilisateur.uid = "u2"
    client.post("/conversations", json={"annonce_id": a["id"]})

    comptes.purger_donnees_utilisateur(db, "u1")

    assert db.query(models.Annonce).count() == 0
    assert db.query(models.Conversation).count() == 0
    assert db.query(models.ImageUploadee).count() == 0
    assert "gendon/img1" in services.images_detruites
    # Le don reste compté, mais anonymisé
    don = db.query(models.DonRealise).one()
    assert don.clerk_user_id is None and don.titre is None


def test_changement_de_pseudo(client, utilisateur, db):
    a = publier(client)
    utilisateur.uid = "u2"
    client.post("/conversations", json={"annonce_id": a["id"]})

    comptes._traiter_evenement_clerk({"type": "user.updated", "data": {"id": "u1", "username": "nouveau"}})

    db.expire_all()
    assert db.query(models.Annonce).one().pseudo == "nouveau"
    assert db.query(models.Conversation).one().donneur_pseudo == "nouveau"


# ---------- Tâches planifiées ----------

def vieillir(db, jours):
    db.query(models.Annonce).update(
        {models.Annonce.created_at: datetime.now(timezone.utc) - timedelta(days=jours)}
    )
    db.commit()


def test_purge_annonces_expirees(client, services, db):
    url = uploader(client)[0]
    publier(client, images=[url])
    vieillir(db, 31)
    taches.purger_annonces_expirees()
    assert db.query(models.Annonce).count() == 0
    assert services.images_detruites == ["gendon/img1"]


def test_annonce_recente_conservee(client, db):
    publier(client)
    vieillir(db, 10)
    taches.purger_annonces_expirees()
    assert db.query(models.Annonce).count() == 1


def test_taches_planifiees_a_heure_fixe():
    """Un « interval » repartait de zéro à chaque redéploiement : les tâches quotidiennes
    doivent être des cron à heure fixe."""
    taches.scheduler.remove_all_jobs()
    with TestClient(main.app):  # déclenche le démarrage (lifespan) qui enregistre les tâches
        planifiees = {j.func.__name__: str(j.trigger) for j in taches.scheduler.get_jobs()}
    for nom in ("purger_annonces_expirees", "purger_images_orphelines", "envoyer_rappels_expiration",
                "envoyer_newsletter_hebdo"):
        assert planifiees[nom].startswith("cron"), (nom, planifiees[nom])


def test_newsletter_par_lots_de_100(client, services, monkeypatch):
    publier(client)
    comptes = [
        {"id": f"u{i}", "primary_email_address_id": "e",
         "email_addresses": [{"id": "e", "email_address": f"u{i}@exemple.fr"}]}
        for i in range(250)
    ]
    monkeypatch.setattr(clerk, "tous_les_utilisateurs", lambda: comptes)
    taches.envoyer_newsletter_hebdo()
    assert [len(lot) for lot, _ in services.lots_newsletter] == [100, 100, 50]


def test_newsletter_respecte_les_desabonnements(client, services, monkeypatch, db):
    publier(client)
    comptes = [
        {"id": uid, "primary_email_address_id": "e", "email_addresses": [{"id": "e", "email_address": f"{uid}@x.fr"}]}
        for uid in ("a", "b")
    ]
    monkeypatch.setattr(clerk, "tous_les_utilisateurs", lambda: comptes)
    client.post("/newsletter/desabonnement", json={"token": emails.token_desabonnement("a")})
    taches.envoyer_newsletter_hebdo()
    destinataires = [email["to"][0] for lot, _ in services.lots_newsletter for email in lot]
    assert destinataires == ["b@x.fr"]


# ---------- Sécurité ----------

def test_lien_de_desabonnement_falsifie_refuse(client):
    assert client.post("/newsletter/desabonnement", json={"token": "u1.faux"}).status_code == 400


def test_ip_client_non_falsifiable():
    """Seule la dernière entrée de X-Forwarded-For (ajoutée par Railway) est fiable."""
    requete = Request({
        "type": "http",
        "headers": [(b"x-forwarded-for", b"1.2.3.4, 203.0.113.9")],
        "client": ("1.2.3.4", 0),
    })
    assert outils.ip_client(requete) == "203.0.113.9"


def test_nettoyage_du_rate_limit():
    outils.verifier_rate_limit("u1", "test", maximum=5, fenetre_secondes=1)
    outils._appels["test:u1"][0] -= outils.FENETRE_MAX_SECONDES + 1
    outils.nettoyer_rate_limit()
    assert "test:u1" not in outils._appels


def test_admin_reserve_aux_moderateurs(client):
    assert client.get("/admin/stats").status_code == 403


# ---------- Préférence newsletter depuis le profil ----------

def test_preference_newsletter(client, services, monkeypatch):
    assert client.get("/newsletter/moi").json() == {"abonne": True}  # abonné par défaut
    assert client.put("/newsletter/moi", json={"abonne": False}).json() == {"abonne": False}
    assert client.put("/newsletter/moi", json={"abonne": False}).status_code == 200  # idempotent
    assert client.get("/newsletter/moi").json() == {"abonne": False}

    # Désabonné : il ne reçoit pas la lettre
    publier(client)
    compte = {"id": "u1", "primary_email_address_id": "e", "email_addresses": [{"id": "e", "email_address": "u1@x.fr"}]}
    monkeypatch.setattr(clerk, "tous_les_utilisateurs", lambda: [compte])
    taches.envoyer_newsletter_hebdo()
    assert services.lots_newsletter == []

    # Réabonné : il la reçoit de nouveau
    client.put("/newsletter/moi", json={"abonne": True})
    assert client.get("/newsletter/moi").json() == {"abonne": True}
    taches.envoyer_newsletter_hebdo()
    assert len(services.lots_newsletter) == 1


def test_cors_autorise_put_depuis_le_site(client):
    """Le navigateur envoie une requête de contrôle avant un PUT : elle doit être acceptée."""
    reponse = client.options("/newsletter/moi", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "PUT",
        "Access-Control-Request-Headers": "authorization,content-type",
    })
    assert reponse.status_code == 200
    assert "PUT" in reponse.headers["access-control-allow-methods"]


# ---------- Minimisation des données côté équipe ----------

def test_emails_reserves_aux_admins(client, utilisateur, db, monkeypatch):
    compte = {"id": "u9", "username": "bob", "primary_email_address_id": "e",
              "email_addresses": [{"id": "e", "email_address": "bob@x.fr"}]}
    monkeypatch.setattr(clerk, "tous_les_utilisateurs", lambda: [compte])

    db.add(models.Role(clerk_user_id="u1", role="moderateur"))
    db.commit()
    assert client.get("/admin/utilisateurs").json()[0]["email"] is None

    monkeypatch.setenv("ADMIN_USER_ID", "u1")
    assert client.get("/admin/utilisateurs").json()[0]["email"] == "bob@x.fr"


def test_journal_purge_apres_un_an(db):
    ancien = datetime.now(timezone.utc) - timedelta(days=taches.DUREE_JOURNAL_MODERATION_JOURS + 1)
    db.add(models.ActionModeration(clerk_user_id="m1", action="vieux", created_at=ancien))
    db.add(models.ActionModeration(clerk_user_id="m1", action="recent"))
    db.commit()
    taches.purger_journal_moderation()
    db.expire_all()
    assert [a.action for a in db.query(models.ActionModeration).all()] == ["recent"]
