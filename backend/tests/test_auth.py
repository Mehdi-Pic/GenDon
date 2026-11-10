"""Vérification des jetons Clerk et du webhook : le code réel, sans les remplacements des autres tests."""
import base64
import json
import time
from datetime import datetime, timezone

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from svix.webhooks import Webhook

from app import auth, models

from helpers import publier


def nouvelle_cle():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


CLE = nouvelle_cle()
AUTRE_CLE = nouvelle_cle()


def jwk(cle, kid):
    donnees = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cle.public_key()))
    return {**donnees, "kid": kid, "alg": "RS256", "use": "sig"}


def jeton(cle=CLE, kid="k1", **champs):
    contenu = {"sub": "user_1", "exp": int(time.time()) + 60, **champs}
    return jwt.encode(contenu, cle, algorithm="RS256", headers={"kid": kid})


def identifier(token):
    return auth.get_current_user_id(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))


class FauxClerk:
    """Remplace l'appel HTTP aux clés publiques Clerk (JWKS)."""

    def __init__(self, *reponses):
        self.reponses = list(reponses)
        self.appels = 0

    def get(self, url, timeout=None):
        self.appels += 1
        statut, corps = self.reponses.pop(0) if len(self.reponses) > 1 else self.reponses[0]
        return httpx.Response(statut, json=corps, request=httpx.Request("GET", url))


@pytest.fixture
def clerk_jwks(monkeypatch):
    monkeypatch.setenv("CLERK_JWKS_URL", "https://clerk.test/.well-known/jwks.json")
    monkeypatch.delenv("CLERK_AUTHORIZED_PARTIES", raising=False)
    monkeypatch.setattr(auth, "_jwks", None)
    monkeypatch.setattr(auth, "_jwks_charge_a", 0.0)

    def installer(*reponses):
        faux = FauxClerk(*reponses)
        monkeypatch.setattr(auth.httpx, "get", faux.get)
        return faux

    return installer


def test_jeton_valide(clerk_jwks):
    clerk_jwks((200, {"keys": [jwk(CLE, "k1")]}))
    assert identifier(jeton()) == "user_1"


def test_jeton_expire(clerk_jwks):
    clerk_jwks((200, {"keys": [jwk(CLE, "k1")]}))
    with pytest.raises(HTTPException) as e:
        identifier(jeton(exp=int(time.time()) - 10))
    assert e.value.status_code == 401 and "expirée" in e.value.detail


def test_jeton_signe_par_une_autre_cle(clerk_jwks):
    clerk_jwks((200, {"keys": [jwk(CLE, "k1")]}))
    with pytest.raises(HTTPException) as e:
        identifier(jeton(cle=AUTRE_CLE))
    assert e.value.status_code == 401


def test_jeton_non_signe_refuse(clerk_jwks):
    clerk_jwks((200, {"keys": [jwk(CLE, "k1")]}))
    non_signe = jwt.encode({"sub": "user_1"}, None, algorithm="none", headers={"kid": "k1"})
    with pytest.raises(HTTPException) as e:
        identifier(non_signe)
    assert e.value.status_code == 401


def test_origine_azp_controlee(clerk_jwks, monkeypatch):
    clerk_jwks((200, {"keys": [jwk(CLE, "k1")]}))
    monkeypatch.setenv("CLERK_AUTHORIZED_PARTIES", "https://www.gendon.fr, https://gendon.fr")
    assert identifier(jeton(azp="https://www.gendon.fr/")) == "user_1"
    with pytest.raises(HTTPException) as e:
        identifier(jeton(azp="https://site-pirate.example"))
    assert e.value.status_code == 401


def test_rotation_des_cles_rechargee_une_fois(clerk_jwks):
    faux = clerk_jwks((200, {"keys": [jwk(CLE, "k1")]}), (200, {"keys": [jwk(CLE, "k1"), jwk(AUTRE_CLE, "k2")]}))
    assert identifier(jeton()) == "user_1"
    auth._jwks_charge_a -= auth.DELAI_RECHARGEMENT_JWKS + 1
    assert identifier(jeton(cle=AUTRE_CLE, kid="k2")) == "user_1"
    assert faux.appels == 2
    # Un kid inconnu ne relance pas Clerk avant le délai
    with pytest.raises(HTTPException):
        identifier(jeton(kid="inconnu"))
    assert faux.appels == 2


def test_erreur_clerk_pas_mise_en_cache(clerk_jwks):
    """Une réponse d'erreur au premier chargement ne doit pas bloquer les connexions jusqu'au redémarrage."""
    faux = clerk_jwks((429, {"errors": [{"message": "Too many requests"}]}), (200, {"keys": [jwk(CLE, "k1")]}))
    with pytest.raises(HTTPException) as e:
        identifier(jeton())
    assert e.value.status_code == 503
    assert identifier(jeton()) == "user_1"
    assert faux.appels == 2


def test_rechargement_force_rate_garde_les_cles(clerk_jwks):
    faux = clerk_jwks((200, {"keys": [jwk(CLE, "k1")]}), (500, {"erreur": "panne"}))
    assert identifier(jeton()) == "user_1"
    auth._jwks_charge_a -= auth.DELAI_RECHARGEMENT_JWKS + 1
    with pytest.raises(HTTPException) as e:
        identifier(jeton(kid="inconnu"))
    assert e.value.status_code == 401
    # Les clés connues fonctionnent toujours, et Clerk n'est pas rappelé dans la minute
    assert identifier(jeton()) == "user_1"
    with pytest.raises(HTTPException):
        identifier(jeton(kid="inconnu"))
    assert faux.appels == 2


# ---------- Webhook Clerk ----------

SECRET_WEBHOOK = "whsec_" + base64.b64encode(b"cle-de-test-du-webhook-clerk").decode()


def envoyer_webhook(client, evenement, secret=SECRET_WEBHOOK):
    corps = json.dumps(evenement)
    entetes = {"svix-id": "msg_1", "svix-timestamp": str(int(time.time()))}
    entetes["svix-signature"] = Webhook(secret).sign("msg_1", datetime.now(timezone.utc), corps)
    return client.post("/webhooks/clerk", content=corps, headers=entetes)


def test_webhook_signature_invalide_refusee(client, utilisateur, db, monkeypatch):
    monkeypatch.setenv("CLERK_WEBHOOK_SECRET", SECRET_WEBHOOK)
    publier(client)
    faux_secret = "whsec_" + base64.b64encode(b"une-autre-cle-pas-la-bonne").decode()
    reponse = envoyer_webhook(client, {"type": "user.deleted", "data": {"id": "u1"}}, secret=faux_secret)
    assert reponse.status_code == 401
    assert db.query(models.Annonce).count() == 1


def test_webhook_signe_supprime_le_compte(client, utilisateur, db, monkeypatch):
    monkeypatch.setenv("CLERK_WEBHOOK_SECRET", SECRET_WEBHOOK)
    publier(client)
    reponse = envoyer_webhook(client, {"type": "user.deleted", "data": {"id": "u1"}})
    assert reponse.status_code == 200
    assert db.query(models.Annonce).count() == 0
