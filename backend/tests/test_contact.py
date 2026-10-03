"""Formulaire de contact : anti-robot, limites par expéditeur et globales, champs nettoyés."""
import pytest

import httpx
import resend

from app import models, roles
from app.routers import contact


def message(**champs):
    donnees = {
        "nom": "Habitant",
        "email": "habitant@exemple.fr",
        "sujet": "Question sur un don",
        "message": "Bonjour, j'ai une question sur une annonce.",
    }
    donnees.update(champs)
    return donnees


@pytest.fixture
def envois(client, monkeypatch):
    """Capture les emails envoyés à l'équipe ; l'équipe est fixée sans appeler Clerk."""
    envoyes = []
    monkeypatch.setattr(resend.Emails, "send", lambda payload: envoyes.append(payload))
    monkeypatch.setattr(contact, "_emails_equipe", lambda db: ["equipe@exemple.fr"])
    return envoyes


def visiteur(ip):
    """Client non connecté vu depuis une IP donnée (dernière entrée de X-Forwarded-For)."""
    return {"x-forwarded-for": f"198.51.100.1, {ip}"}


@pytest.fixture
def anonyme(utilisateur):
    utilisateur.uid = None


def test_message_envoye_a_l_equipe(client, envois, anonyme):
    reponse = client.post("/contact", json=message(), headers=visiteur("203.0.113.1"))
    assert reponse.status_code == 200
    assert envois[0]["to"] == ["equipe@exemple.fr"]
    assert envois[0]["reply_to"] == "habitant@exemple.fr"


def test_champ_piege_rien_n_est_envoye(client, envois, anonyme):
    reponse = client.post("/contact", json=message(site_web="http://spam"), headers=visiteur("203.0.113.1"))
    assert reponse.status_code == 200  # le robot croit avoir réussi
    assert envois == []


def test_limite_par_ip(client, envois, anonyme):
    codes = [client.post("/contact", json=message(), headers=visiteur("203.0.113.1")).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]


def test_plafond_global_malgre_changement_d_ip(client, envois, anonyme):
    """Un robot qui change d'IP à chaque envoi est arrêté par le plafond global."""
    codes = [
        client.post("/contact", json=message(), headers=visiteur(f"203.0.113.{i}")).status_code
        for i in range(contact.CONTACT_MAX_PAR_HEURE + 5)
    ]
    assert codes.count(200) == contact.CONTACT_MAX_PAR_HEURE
    assert codes[-1] == 429
    assert len(envois) == contact.CONTACT_MAX_PAR_HEURE


def test_plafond_quotidien(client, envois, anonyme, monkeypatch):
    monkeypatch.setattr(contact, "CONTACT_MAX_PAR_HEURE", 1000)
    codes = [
        client.post("/contact", json=message(), headers=visiteur(f"198.18.{i // 250}.{i % 250}")).status_code
        for i in range(contact.CONTACT_MAX_PAR_JOUR + 3)
    ]
    assert codes.count(200) == contact.CONTACT_MAX_PAR_JOUR


@pytest.mark.parametrize("adresse", ["pas-une-adresse", "a@b", "a b@exemple.fr", "a@exemple.fr\nBcc: x@y.fr"])
def test_adresse_invalide_refusee(client, envois, anonyme, adresse):
    reponse = client.post("/contact", json=message(email=adresse), headers=visiteur("203.0.113.1"))
    assert reponse.status_code in (400, 422)  # 422 : refusée dès la validation des longueurs
    assert envois == []


def test_sujet_et_nom_sur_une_seule_ligne(client, envois, anonyme):
    client.post(
        "/contact",
        json=message(sujet="Bonjour\r\nBcc: victime@exemple.fr", nom="Jean\nDupont"),
        headers=visiteur("203.0.113.1"),
    )
    sujet = envois[0]["subject"]
    assert "\n" not in sujet and "\r" not in sujet
    assert sujet == "[Contact GenDon] Bonjour Bcc: victime@exemple.fr"
    assert "Jean Dupont" in envois[0]["html"]


def test_contenu_html_echappe(client, envois, anonyme):
    client.post(
        "/contact",
        json=message(message="<script>alert(1)</script> et un <a href='x'>lien</a>"),
        headers=visiteur("203.0.113.1"),
    )
    assert "<script>" not in envois[0]["html"]
    assert "&lt;script&gt;" in envois[0]["html"]


def test_adresses_equipe_en_cache(client, monkeypatch, anonyme):
    """Les adresses de l'équipe sont lues chez Clerk une fois, puis gardées 10 minutes."""
    monkeypatch.setattr(roles, "admins_principaux", lambda: ["admin1"])
    appels = []

    class Reponse:
        is_success = True

        def json(self):
            return {"primary_email_address_id": "e", "email_addresses": [{"id": "e", "email_address": "admin@exemple.fr"}]}

    def faux_get(url, **kwargs):
        appels.append(url)
        return Reponse()

    monkeypatch.setattr(httpx, "get", faux_get)
    monkeypatch.setattr(resend.Emails, "send", lambda payload: None)
    for i in range(3):
        assert client.post("/contact", json=message(), headers=visiteur(f"203.0.113.{i}")).status_code == 200
    assert len(appels) == 1


def test_adresses_equipe_jamais_renvoyees(client, envois, anonyme):
    reponse = client.post("/contact", json=message(), headers=visiteur("203.0.113.1"))
    assert "equipe@exemple.fr" not in reponse.text


def test_adresse_du_site_remplace_celle_des_admins(db, monkeypatch):
    """Avec CONTACT_EMAIL, les admins principaux reçoivent via l'adresse du site ; les modérateurs gardent la leur."""
    monkeypatch.setenv("ADMIN_USER_ID", "admin1")
    monkeypatch.setenv("CONTACT_EMAIL", "contact@gendon.fr")
    db.add(models.Role(clerk_user_id="modo1", role="moderateur"))
    db.commit()
    appels = []

    class Reponse:
        is_success = True

        def __init__(self, uid):
            self.uid = uid

        def json(self):
            return {"primary_email_address_id": "e", "email_addresses": [{"id": "e", "email_address": f"{self.uid}@perso.fr"}]}

    def faux_get(url, **kwargs):
        uid = url.rsplit("/", 1)[-1]
        appels.append(uid)
        return Reponse(uid)

    monkeypatch.setattr(httpx, "get", faux_get)
    assert contact._emails_equipe(db) == ["contact@gendon.fr", "modo1@perso.fr"]
    assert appels == ["modo1"]
