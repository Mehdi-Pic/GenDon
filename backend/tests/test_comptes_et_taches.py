from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from starlette.requests import Request

from app import main, models

from helpers import publier, uploader


# ---------- Suppression de compte / changement de pseudo (webhook Clerk) ----------

def test_suppression_de_compte(client, utilisateur, services, db):
    url = uploader(client)[0]
    a = publier(client, images=[url])
    client.post(f"/annonces/{a['id']}/donne")
    utilisateur.uid = "u2"
    client.post("/conversations", json={"annonce_id": a["id"]})

    main.purger_donnees_utilisateur(db, "u1")

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

    main._traiter_evenement_clerk({"type": "user.updated", "data": {"id": "u1", "username": "nouveau"}})

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
    main.purger_annonces_expirees()
    assert db.query(models.Annonce).count() == 0
    assert services.images_detruites == ["gendon/img1"]


def test_annonce_recente_conservee(client, db):
    publier(client)
    vieillir(db, 10)
    main.purger_annonces_expirees()
    assert db.query(models.Annonce).count() == 1


def test_taches_planifiees_a_heure_fixe():
    """Un « interval » repartait de zéro à chaque redéploiement : les tâches quotidiennes
    doivent être des cron à heure fixe."""
    main.scheduler.remove_all_jobs()
    with TestClient(main.app):  # déclenche le démarrage (lifespan) qui enregistre les tâches
        taches = {j.func.__name__: str(j.trigger) for j in main.scheduler.get_jobs()}
    for nom in ("purger_annonces_expirees", "purger_images_orphelines", "envoyer_rappels_expiration",
                "envoyer_newsletter_hebdo"):
        assert taches[nom].startswith("cron"), (nom, taches[nom])


def test_newsletter_par_lots_de_100(client, services, monkeypatch):
    publier(client)
    comptes = [
        {"id": f"u{i}", "primary_email_address_id": "e",
         "email_addresses": [{"id": "e", "email_address": f"u{i}@exemple.fr"}]}
        for i in range(250)
    ]
    monkeypatch.setattr(main, "_tous_les_utilisateurs_clerk", lambda: comptes)
    main.envoyer_newsletter_hebdo()
    assert [len(lot) for lot, _ in services.lots_newsletter] == [100, 100, 50]


def test_newsletter_respecte_les_desabonnements(client, services, monkeypatch, db):
    publier(client)
    comptes = [
        {"id": uid, "primary_email_address_id": "e", "email_addresses": [{"id": "e", "email_address": f"{uid}@x.fr"}]}
        for uid in ("a", "b")
    ]
    monkeypatch.setattr(main, "_tous_les_utilisateurs_clerk", lambda: comptes)
    client.post("/newsletter/desabonnement", json={"token": main._token_desabonnement("a")})
    main.envoyer_newsletter_hebdo()
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
    assert main.ip_client(requete) == "203.0.113.9"


def test_nettoyage_du_rate_limit():
    main.verifier_rate_limit("u1", "test", maximum=5, fenetre_secondes=1)
    main._appels["test:u1"][0] -= main.FENETRE_MAX_SECONDES + 1
    main.nettoyer_rate_limit()
    assert "test:u1" not in main._appels


def test_admin_reserve_aux_moderateurs(client):
    assert client.get("/admin/stats").status_code == 403
