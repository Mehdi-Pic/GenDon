from datetime import datetime, timedelta, timezone

import pytest
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


@pytest.fixture
def boite(monkeypatch):
    """Emails d'alerte envoyés ; heure de Paris fixée à midi (modifiable via boite.heure)."""
    class Boite(list):
        heure = 12
    envoyes = Boite()
    monkeypatch.setattr(resend.Emails, "send", lambda payload: envoyes.append(payload))
    monkeypatch.setattr(taches.clerk, "email_utilisateur", lambda uid: f"{uid}@exemple.fr")
    monkeypatch.setattr(taches, "_heure_paris", lambda: envoyes.heure)
    return envoyes


def vieillir_dernier_envoi(db, minutes):
    db.query(models.Alerte).update(
        {models.Alerte.dernier_envoi_at: datetime.now(timezone.utc) - timedelta(minutes=minutes)}
    )
    db.commit()


def test_alerte_envoyee_des_la_publication(client, utilisateur, boite):
    utilisateur.uid = "u2"
    client.post("/alertes", json={"recherche": "velo"})
    publier(client, titre="Vélo à moi")  # sa propre annonce : jamais signalée
    assert boite == []

    utilisateur.uid = "u1"
    publier(client, titre="Table")
    assert boite == []
    publier(client, titre="Vélo de course")
    assert len(boite) == 1 and boite[0]["to"] == ["u2@exemple.fr"]
    assert "Vélo de course" in boite[0]["html"] and "Vélo à moi" not in boite[0]["html"]


def test_un_email_par_heure_au_plus(client, utilisateur, db, boite):
    utilisateur.uid = "u2"
    client.post("/alertes", json={"recherche": "velo"})
    utilisateur.uid = "u1"
    publier(client, titre="Vélo de course")
    publier(client, titre="Vélo enfant")  # dans l'heure : pas de second email
    assert len(boite) == 1
    taches.envoyer_alertes()  # tâche horaire, toujours dans l'heure
    assert len(boite) == 1

    vieillir_dernier_envoi(db, 61)
    taches.envoyer_alertes()
    assert len(boite) == 2
    assert "Vélo enfant" in boite[1]["html"] and "Vélo de course" not in boite[1]["html"]
    taches.envoyer_alertes()  # rien de nouveau
    assert len(boite) == 2


def test_pas_d_alerte_la_nuit(client, utilisateur, boite):
    utilisateur.uid = "u2"
    client.post("/alertes", json={"recherche": "velo"})
    boite.heure = 23
    utilisateur.uid = "u1"
    publier(client, titre="Vélo de course")
    taches.envoyer_alertes()
    assert boite == []
    boite.heure = 8  # premier envoi du matin : les dons de la nuit
    taches.envoyer_alertes()
    assert len(boite) == 1 and "Vélo de course" in boite[0]["html"]


def test_suppression_de_compte_efface_les_alertes(client, db):
    from app.routers import comptes
    client.post("/alertes", json={"recherche": "velo"})
    client.put("/notifications/messages/moi", json={"actif": False})
    comptes.purger_donnees_utilisateur(db, "u1")
    assert db.query(models.Alerte).count() == 0
    assert db.query(models.DesabonnementMessages).count() == 0
