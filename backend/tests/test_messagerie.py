from datetime import datetime, timedelta, timezone

from app import models, taches

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
    # Rattaché à la conversation elle-même (et non plus à l'annonce) : survit au retrait de l'annonce
    assert signalement.conversation_id == cid and signalement.annonce_id is None
    assert signalement.raison.endswith("\nencore")


# ---------- Conversations indépendantes de l'annonce ----------

def test_conversation_survit_a_la_suppression_de_l_annonce(client, utilisateur, db):
    a, cid = conversation(client, utilisateur)
    client.post(f"/conversations/{cid}/messages", json={"contenu": "Je passe ce soir"})
    utilisateur.uid = "u1"
    assert client.delete(f"/annonces/{a['id']}").status_code == 200

    fil = client.get(f"/conversations/{cid}/messages").json()
    assert fil["annonce_statut"] == "retiree"
    assert fil["annonce_titre"] == "Canapé 3 places"
    assert fil["messages"][0]["contenu"] == "Je passe ce soir"
    # On peut encore finaliser la remise
    assert client.post(f"/conversations/{cid}/messages", json={"contenu": "OK"}).status_code == 200
    assert client.get("/conversations").json()[0]["annonce_titre"] == "Canapé 3 places"


def test_titre_tenu_a_jour(client, utilisateur, db):
    a, cid = conversation(client, utilisateur)
    utilisateur.uid = "u1"
    client.patch(f"/annonces/{a['id']}", json={
        "titre": "Canapé 2 places", "description": "x", "categorie": "Mobilier", "quartier": "Le Luth", "images": [],
    })
    client.delete(f"/annonces/{a['id']}")
    assert client.get(f"/conversations/{cid}/messages").json()["annonce_titre"] == "Canapé 2 places"


def test_purge_conversations_abandonnees(client, utilisateur, db):
    a, cid = conversation(client, utilisateur)
    utilisateur.uid = "u1"
    client.delete(f"/annonces/{a['id']}")
    taches.purger_conversations()
    assert db.query(models.Conversation).count() == 1  # encore récente

    db.query(models.Conversation).update(
        {models.Conversation.dernier_message_at: datetime.now(timezone.utc) - timedelta(days=31)}
    )
    db.commit()
    taches.purger_conversations()
    assert db.query(models.Conversation).count() == 0


def test_conversation_signalee_gardee_pour_l_equipe(client, utilisateur, db):
    _, cid = conversation(client, utilisateur)
    client.post(f"/conversations/{cid}/signaler", json={"raison": "insultes"})
    client.delete(f"/conversations/{cid}")
    utilisateur.uid = "u1"
    client.delete(f"/conversations/{cid}")
    taches.purger_conversations()
    assert db.query(models.Conversation).count() == 1
    # Une fois le signalement traité, la purge la supprime
    db.query(models.Signalement).update({models.Signalement.traite: True})
    db.commit()
    taches.purger_conversations()
    assert db.query(models.Conversation).count() == 0
    assert db.query(models.Signalement).one().conversation_id is None  # le motif reste lisible


# ---------- Réservation ----------

def test_reserver_previent_les_autres(client, utilisateur):
    a, cid = conversation(client, utilisateur)
    utilisateur.uid = "u3"
    cid3 = client.post("/conversations", json={"annonce_id": a["id"]}).json()["id"]

    utilisateur.uid = "u1"
    reponse = client.post(f"/annonces/{a['id']}/reserver", json={"conversation_id": cid})
    assert reponse.status_code == 200 and reponse.json()["statut"] == "reservee"
    mes = client.get("/annonces/me").json()[0]
    assert mes["nb_interesses"] == 2 and mes["reserve_pour_pseudo"] == "pseudo-u2"
    fil = client.get(f"/conversations/{cid}/messages").json()
    assert fil["reservee_ici"] is True
    # Lu par les deux participants : formulation neutre
    assert fil["messages"][-1]["contenu"] == "Objet réservé pour pseudo-u2."

    utilisateur.uid = "u3"
    fil = client.get(f"/conversations/{cid3}/messages").json()
    assert fil["annonce_statut"] == "reservee" and fil["reservee_ici"] is False
    assert "Objet réservé pour une autre personne" in fil["messages"][-1]["contenu"]
    # Les messages système ne comptent pas comme non lus
    assert client.get("/messages/non-lus").json()["non_lus"] == 0
    # L'annonce reste visible avec son statut
    assert client.get(f"/annonces/{a['id']}").json()["statut"] == "reservee"


def test_seul_le_donneur_reserve(client, utilisateur):
    a, cid = conversation(client, utilisateur)
    assert client.post(f"/annonces/{a['id']}/reserver", json={"conversation_id": cid}).status_code == 403


def test_reservation_levee_si_le_beneficiaire_quitte(client, utilisateur):
    a, cid = conversation(client, utilisateur)
    utilisateur.uid = "u3"
    cid3 = client.post("/conversations", json={"annonce_id": a["id"]}).json()["id"]
    utilisateur.uid = "u1"
    client.post(f"/annonces/{a['id']}/reserver", json={"conversation_id": cid})
    utilisateur.uid = "u2"
    client.delete(f"/conversations/{cid}")
    utilisateur.uid = "u3"
    fil = client.get(f"/conversations/{cid3}/messages").json()
    assert fil["annonce_statut"] == "disponible"
    assert fil["messages"][-1]["contenu"] == "L'objet est de nouveau disponible."


def test_liberer_puis_donner(client, utilisateur):
    a, cid = conversation(client, utilisateur)
    utilisateur.uid = "u1"
    client.post(f"/annonces/{a['id']}/reserver", json={"conversation_id": cid})
    assert client.post(f"/annonces/{a['id']}/liberer").json()["statut"] == "publiee"
    client.post(f"/annonces/{a['id']}/donne")
    utilisateur.uid = "u2"
    fil = client.get(f"/conversations/{cid}/messages").json()
    assert fil["annonce_statut"] == "donnee"
    assert "a été donné" in fil["messages"][-1]["contenu"]


# ---------- Préférence des emails de messages ----------

def test_emails_messages_desactives(client, utilisateur, services):
    _, cid = conversation(client, utilisateur)
    utilisateur.uid = "u1"
    assert client.get("/notifications/messages/moi").json() == {"actif": True}
    client.put("/notifications/messages/moi", json={"actif": False})
    assert client.get("/notifications/messages/moi").json() == {"actif": False}
    utilisateur.uid = "u2"
    client.post(f"/conversations/{cid}/messages", json={"contenu": "Bonjour"})
    assert services.notifications == []


def test_accuse_de_lecture(client, utilisateur):
    _, cid = conversation(client, utilisateur)
    client.post(f"/conversations/{cid}/messages", json={"contenu": "Bonjour"})
    assert client.get(f"/conversations/{cid}/messages").json()["dernier_lu"] is False
    utilisateur.uid = "u1"
    client.post(f"/conversations/{cid}/lu")
    utilisateur.uid = "u2"
    assert client.get(f"/conversations/{cid}/messages").json()["dernier_lu"] is True


# ---------- Modération des conversations ----------

def test_equipe_lit_seulement_les_conversations_signalees(client, utilisateur, db):
    _, cid = conversation(client, utilisateur)
    client.post(f"/conversations/{cid}/messages", json={"contenu": "message déplacé"})
    db.add(models.Role(clerk_user_id="modo", role="moderateur"))
    db.commit()
    utilisateur.uid = "modo"
    assert client.get(f"/admin/conversations/{cid}").status_code == 404

    utilisateur.uid = "u1"
    client.post(f"/conversations/{cid}/signaler", json={"raison": "propos déplacés"})
    utilisateur.uid = "modo"
    fil = client.get(f"/admin/conversations/{cid}").json()
    assert fil["messages"][0] == {**fil["messages"][0], "auteur": "demandeur", "contenu": "message déplacé"}
    assert fil["demandeur"]["id"] == "u2"
    signalement = client.get("/admin/signalements").json()[0]
    assert signalement["type"] == "conversation" and signalement["conversation_id"] == cid
    assert db.query(models.ActionModeration).filter_by(action="conversation_consultee").count() == 1

    utilisateur.uid = "u3"  # simple utilisateur
    assert client.get(f"/admin/conversations/{cid}").status_code == 403


def test_suspension(client, utilisateur, db, monkeypatch):
    from app import clerk
    appels = []
    monkeypatch.setattr(clerk, "suspendre", lambda uid, suspendu: appels.append((uid, suspendu)) or True)
    db.add(models.Role(clerk_user_id="modo", role="moderateur"))
    db.add(models.Role(clerk_user_id="modo2", role="moderateur"))
    db.commit()
    utilisateur.uid = "modo"
    assert client.post("/admin/utilisateurs/u2/suspendre", json={"suspendu": True}).status_code == 200
    assert appels == [("u2", True)]
    # Un modérateur ne suspend ni un autre membre de l'équipe, ni lui-même
    assert client.post("/admin/utilisateurs/modo2/suspendre", json={"suspendu": True}).status_code == 403
    assert client.post("/admin/utilisateurs/modo/suspendre", json={"suspendu": True}).status_code == 400
    utilisateur.uid = "u3"
    assert client.post("/admin/utilisateurs/u2/suspendre", json={"suspendu": False}).status_code == 403


def test_annonces_d_un_compte_suspendu_masquees(client, utilisateur, db, monkeypatch):
    from app import clerk
    monkeypatch.setattr(clerk, "suspendre", lambda uid, suspendu: True)
    a, cid = conversation(client, utilisateur)  # u1 publie, u2 écrit
    db.add(models.Role(clerk_user_id="modo", role="moderateur"))
    db.commit()
    utilisateur.uid = "modo"
    client.post("/admin/utilisateurs/u1/suspendre", json={"suspendu": True})

    utilisateur.uid = "u3"
    assert client.get("/annonces").json()["total"] == 0
    assert client.get(f"/annonces/{a['id']}").status_code == 404
    assert client.get("/stats").json()["annonces"] == 0
    assert client.post("/conversations", json={"annonce_id": a["id"]}).status_code == 404

    utilisateur.uid = "modo"
    client.post("/admin/utilisateurs/u1/suspendre", json={"suspendu": False})
    utilisateur.uid = "u3"
    assert client.get("/annonces").json()["total"] == 1


def test_etat_de_suspension_dans_la_conversation_signalee(client, utilisateur, db, monkeypatch):
    from app import clerk
    monkeypatch.setattr(clerk, "suspendre", lambda uid, suspendu: True)
    _, cid = conversation(client, utilisateur)
    client.post(f"/conversations/{cid}/signaler", json={"raison": "insultes"})
    db.add(models.Role(clerk_user_id="modo", role="moderateur"))
    db.commit()
    utilisateur.uid = "modo"
    assert client.get(f"/admin/conversations/{cid}").json()["demandeur"]["suspendu"] is False
    client.post("/admin/utilisateurs/u2/suspendre", json={"suspendu": True})
    fil = client.get(f"/admin/conversations/{cid}").json()
    assert fil["demandeur"]["suspendu"] is True and fil["donneur"]["suspendu"] is False


def test_bannissement_depuis_clerk_synchronise(client, db):
    from app.routers import comptes
    publier(client)
    comptes._traiter_evenement_clerk({"type": "user.updated", "data": {"id": "u1", "username": "x", "banned": True}})
    assert client.get("/annonces").json()["total"] == 0
    comptes._traiter_evenement_clerk({"type": "user.updated", "data": {"id": "u1", "username": "x", "banned": False}})
    assert client.get("/annonces").json()["total"] == 1


def test_journal_affiche_les_pseudos(client, utilisateur, db, monkeypatch):
    monkeypatch.setenv("ADMIN_USER_ID", "admin1")
    _, cid = conversation(client, utilisateur)
    client.post(f"/conversations/{cid}/signaler", json={"raison": "insultes"})
    utilisateur.uid = "admin1"
    client.get(f"/admin/conversations/{cid}")
    assert client.get("/admin/journal").json()[0]["par"] == "pseudo-admin1"


def test_admin_distingue_annonces_masquees(client, utilisateur, db, monkeypatch):
    """Le tableau de bord compte comme la page d'accueil et explique l'écart avec la liste admin."""
    from app import clerk
    monkeypatch.setattr(clerk, "suspendre", lambda uid, suspendu: True)
    publier(client)
    donnee = publier(client)
    db.query(models.Annonce).filter_by(id=donnee["id"]).update({"donne_at": datetime.now(timezone.utc)})
    db.commit()
    utilisateur.uid = "u2"
    publier(client)
    db.add(models.Role(clerk_user_id="modo", role="moderateur"))
    db.commit()
    utilisateur.uid = "modo"
    client.post("/admin/utilisateurs/u2/suspendre", json={"suspendu": True})

    stats = client.get("/admin/stats").json()
    assert (stats["annonces"], stats["annonces_donnees"], stats["annonces_suspendues"]) == (1, 1, 1)
    assert stats["annonces"] == client.get("/stats").json()["annonces"]
    liste = client.get("/admin/annonces").json()
    assert liste["total"] == 3
    assert sorted((a["donne_at"] is not None, a["auteur_suspendu"]) for a in liste["annonces"]) == [
        (False, False), (False, True), (True, False)
    ]
