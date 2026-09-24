from app import models

from helpers import annonce, publier


def test_publier_en_mobilier(client):
    a = publier(client, categorie="Mobilier")
    assert a["categorie"] == "Mobilier"


def test_categorie_inconnue_refusee(client):
    assert client.post("/annonces", json=annonce(categorie="Immobilier")).status_code == 422


def test_pseudo_et_statut_fixes_par_le_serveur(client):
    """Le client ne peut ni usurper un pseudo ni imposer un statut."""
    reponse = client.post("/annonces", json=annonce(pseudo="quelqu-un-d-autre", statut="x" * 50))
    assert reponse.status_code == 200
    assert reponse.json()["pseudo"] == "pseudo-u1"
    assert reponse.json()["statut"] == "publiee"


def test_listing_filtre_et_masque_mes_annonces(client, utilisateur):
    publier(client, categorie="Mobilier")
    publier(client, categorie="Sport")
    # Le propriétaire ne voit pas ses propres annonces dans le listing
    assert client.get("/annonces").json()["total"] == 0
    utilisateur.uid = "u2"
    assert client.get("/annonces").json()["total"] == 2
    assert client.get("/annonces?categorie=Mobilier").json()["total"] == 1


def test_modifier_reservee_au_proprietaire(client, utilisateur):
    a = publier(client)
    utilisateur.uid = "u2"
    assert client.patch(f"/annonces/{a['id']}", json=annonce(titre="Pirate")).status_code == 403
    utilisateur.uid = "u1"
    reponse = client.patch(f"/annonces/{a['id']}", json=annonce(titre="Nouveau titre"))
    assert reponse.status_code == 200
    assert reponse.json()["titre"] == "Nouveau titre"


def test_supprimer_reservee_au_proprietaire(client, utilisateur):
    a = publier(client)
    utilisateur.uid = "u2"
    assert client.delete(f"/annonces/{a['id']}").status_code == 403
    utilisateur.uid = "u1"
    assert client.delete(f"/annonces/{a['id']}").status_code == 200
    assert client.get(f"/annonces/{a['id']}").status_code == 404


def test_don_compte_une_seule_fois(client, db):
    a = publier(client)
    assert client.post(f"/annonces/{a['id']}/donne").status_code == 200
    assert client.post(f"/annonces/{a['id']}/donne").status_code == 400
    assert db.query(models.DonRealise).count() == 1
    # Une annonce donnée n'est plus modifiable et disparaît du listing
    assert client.patch(f"/annonces/{a['id']}", json=annonce()).status_code == 400


def test_annonce_donnee_absente_du_listing(client, utilisateur):
    a = publier(client)
    client.post(f"/annonces/{a['id']}/donne")
    utilisateur.uid = "u2"
    assert client.get("/annonces").json()["total"] == 0
    # La page reste accessible (bandeau « déjà donné ») mais on ne peut plus contacter
    assert client.get(f"/annonces/{a['id']}").json()["donne_at"] is not None
    assert client.post("/conversations", json={"annonce_id": a["id"]}).status_code == 400


def test_renouveler_trop_tot_refuse(client):
    a = publier(client)
    assert client.post(f"/annonces/{a['id']}/renouveler").status_code == 400


def test_vue_comptee_une_fois_par_visiteur(client, utilisateur):
    a = publier(client)
    # Le propriétaire ne compte pas
    assert client.post(f"/annonces/{a['id']}/vue").json()["comptee"] is False
    utilisateur.uid = "u2"
    assert client.post(f"/annonces/{a['id']}/vue").json()["comptee"] is True
    assert client.post(f"/annonces/{a['id']}/vue").json()["comptee"] is False
    assert client.get(f"/annonces/{a['id']}").json()["vues"] == 1


def test_favori_idempotent(client, utilisateur):
    a = publier(client)
    assert client.post(f"/annonces/{a['id']}/favori").status_code == 400  # sa propre annonce
    utilisateur.uid = "u2"
    assert client.post(f"/annonces/{a['id']}/favori").status_code == 200
    assert client.post(f"/annonces/{a['id']}/favori").status_code == 200
    assert len(client.get("/favoris").json()) == 1
    client.delete(f"/annonces/{a['id']}/favori")
    assert client.get("/favoris").json() == []


def test_signalement_idempotent(client, utilisateur, db):
    a = publier(client)
    utilisateur.uid = "u2"
    for _ in range(2):
        assert client.post(f"/annonces/{a['id']}/signaler", json={"raison": "Arnaque"}).status_code == 200
    assert db.query(models.Signalement).count() == 1


def test_stats_publiques(client):
    publier(client)
    assert client.get("/stats").json() == {"annonces": 1, "dons_realises": 0}
