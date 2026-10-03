from datetime import datetime, timedelta, timezone

import resend

from app import models, taches

from helpers import publier


def test_recherche_insensible_aux_accents(client, utilisateur):
    publier(client, titre="Vélo enfant", description="Très bon état")
    publier(client, titre="Lampe", description="ÉCLAIRAGE puissant")
    utilisateur.uid = "u2"
    assert [a["titre"] for a in client.get("/annonces?recherche=velo").json()["annonces"]] == ["Vélo enfant"]
    assert [a["titre"] for a in client.get("/annonces?recherche=VÉLO").json()["annonces"]] == ["Vélo enfant"]
    assert [a["titre"] for a in client.get("/annonces?recherche=eclairage").json()["annonces"]] == ["Lampe"]
    # Les jokers restent cherchés littéralement
    assert client.get("/annonces?recherche=%25").json()["total"] == 0


def test_creer_lister_supprimer_alertes(client):
    assert client.post("/alertes", json={}).status_code == 400
    assert client.post("/alertes", json={"categorie": "Inconnue"}).status_code == 422
    a = client.post("/alertes", json={"recherche": "  vélo  ", "quartier": "Le Luth"}).json()
    assert a["recherche"] == "vélo"
    # Doublon : pas de seconde alerte
    assert client.post("/alertes", json={"recherche": "vélo", "quartier": "Le Luth"}).json()["id"] == a["id"]
    assert len(client.get("/alertes").json()) == 1
    client.delete(f"/alertes/{a['id']}")
    assert client.get("/alertes").json() == []


def test_envoi_des_alertes(client, utilisateur, db, monkeypatch):
    envoyes = []
    monkeypatch.setattr(resend.Emails, "send", lambda payload: envoyes.append(payload))
    monkeypatch.setattr(taches.clerk, "email_utilisateur", lambda uid: f"{uid}@exemple.fr")

    utilisateur.uid = "u2"
    client.post("/alertes", json={"recherche": "velo"})
    publier(client, titre="Vélo à moi")  # sa propre annonce : jamais signalée
    db.query(models.Alerte).update(
        {models.Alerte.verifie_jusqu_a: datetime.now(timezone.utc) - timedelta(minutes=5)}
    )
    db.commit()

    utilisateur.uid = "u1"
    publier(client, titre="Vélo de course")
    publier(client, titre="Table")
    taches.envoyer_alertes()
    assert len(envoyes) == 1
    assert envoyes[0]["to"] == ["u2@exemple.fr"]
    assert "Vélo de course" in envoyes[0]["html"]
    assert "Table" not in envoyes[0]["html"] and "Vélo à moi" not in envoyes[0]["html"]

    # Déjà signalée : pas de second email
    taches.envoyer_alertes()
    assert len(envoyes) == 1


def test_suppression_de_compte_efface_les_alertes(client, db):
    from app.routers import comptes
    client.post("/alertes", json={"recherche": "velo"})
    client.put("/notifications/messages/moi", json={"actif": False})
    comptes.purger_donnees_utilisateur(db, "u1")
    assert db.query(models.Alerte).count() == 0
    assert db.query(models.DesabonnementMessages).count() == 0
