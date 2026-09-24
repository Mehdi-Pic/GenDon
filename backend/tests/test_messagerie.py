from app import models

from helpers import publier


def conversation(client, utilisateur):
    """u1 publie, u2 démarre la conversation. Renvoie (annonce, id de conversation)."""
    utilisateur.uid = "u1"
    a = publier(client)
    utilisateur.uid = "u2"
    reponse = client.post("/conversations", json={"annonce_id": a["id"]})
    assert reponse.status_code == 200, reponse.text
    return a, reponse.json()["id"]


def test_demarrer_une_seule_conversation(client, utilisateur):
    a, cid = conversation(client, utilisateur)
    assert client.post("/conversations", json={"annonce_id": a["id"]}).json()["id"] == cid


def test_ne_peut_pas_contacter_sa_propre_annonce(client):
    a = publier(client)
    assert client.post("/conversations", json={"annonce_id": a["id"]}).status_code == 400


def test_messages_et_non_lus(client, utilisateur):
    _, cid = conversation(client, utilisateur)
    client.post(f"/conversations/{cid}/messages", json={"contenu": "Bonjour"})
    client.post(f"/conversations/{cid}/messages", json={"contenu": "Toujours dispo ?"})

    utilisateur.uid = "u1"
    assert client.get("/messages/non-lus").json()["non_lus"] == 2
    convs = client.get("/conversations").json()
    assert convs[0]["dernier_message"] == "Toujours dispo ?"
    assert convs[0]["interlocuteur"] == "pseudo-u2"

    client.post(f"/conversations/{cid}/lu")
    assert client.get("/messages/non-lus").json()["non_lus"] == 0


def test_une_seule_notification_tant_que_non_lu(client, utilisateur, services):
    _, cid = conversation(client, utilisateur)
    client.post(f"/conversations/{cid}/messages", json={"contenu": "1"})
    client.post(f"/conversations/{cid}/messages", json={"contenu": "2"})
    assert len(services.notifications) == 1
    # Le destinataire lit : la prochaine réponse notifie à nouveau
    utilisateur.uid = "u1"
    client.post(f"/conversations/{cid}/lu")
    utilisateur.uid = "u2"
    client.post(f"/conversations/{cid}/messages", json={"contenu": "3"})
    assert len(services.notifications) == 2


def test_conversation_privee(client, utilisateur):
    _, cid = conversation(client, utilisateur)
    utilisateur.uid = "intrus"
    assert client.get(f"/conversations/{cid}/messages").status_code == 403
    assert client.post(f"/conversations/{cid}/messages", json={"contenu": "x"}).status_code == 403


def test_quitter_deux_fois_un_seul_message_systeme(client, utilisateur):
    _, cid = conversation(client, utilisateur)
    client.delete(f"/conversations/{cid}")
    client.delete(f"/conversations/{cid}")
    utilisateur.uid = "u1"
    fil = client.get(f"/conversations/{cid}/messages").json()
    assert sum(1 for m in fil["messages"] if m["systeme"]) == 1
    assert fil["autre_present"] is False
    # On ne peut plus écrire à quelqu'un qui est parti
    assert client.post(f"/conversations/{cid}/messages", json={"contenu": "x"}).status_code == 400


def test_quitter_des_deux_cotes_supprime(client, utilisateur, db):
    _, cid = conversation(client, utilisateur)
    client.delete(f"/conversations/{cid}")
    utilisateur.uid = "u1"
    client.delete(f"/conversations/{cid}")
    assert db.query(models.Conversation).count() == 0


def test_signaler_conversation_raison_longue_et_repetee(client, utilisateur, db):
    """Raison de 500 caractères + préfixe : plantait avant (colonne limitée à 500)."""
    _, cid = conversation(client, utilisateur)
    assert client.post(f"/conversations/{cid}/signaler", json={"raison": "x" * 500}).status_code == 200
    assert client.post(f"/conversations/{cid}/signaler", json={"raison": "encore"}).status_code == 200
    signalement = db.query(models.Signalement).one()
    assert signalement.raison.count(f"[Conversation #{cid}]") == 2
