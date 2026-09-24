from datetime import datetime, timedelta, timezone

from app import main, models

from helpers import annonce, publier, uploader


def test_publier_avec_sa_photo(client):
    url = uploader(client)[0]
    assert publier(client, images=[url])["images"] == [url]


def test_photo_d_un_autre_refusee(client, utilisateur):
    """Faille corrigée : référencer la photo d'un autre permettait de la faire supprimer."""
    url_u1 = uploader(client)[0]
    utilisateur.uid = "u2"
    assert client.post("/annonces", json=annonce(images=[url_u1])).status_code == 400


def test_url_externe_refusee(client):
    assert client.post("/annonces", json=annonce(images=["https://exemple.com/x.jpg"])).status_code == 400


def test_modifier_ne_peut_pas_ajouter_la_photo_d_un_autre(client, utilisateur):
    utilisateur.uid = "u2"
    url_u2 = uploader(client)[0]
    utilisateur.uid = "u1"
    a = publier(client)
    assert client.patch(f"/annonces/{a['id']}", json=annonce(images=[url_u2])).status_code == 400


def test_retirer_une_photo_la_supprime(client, services):
    url = uploader(client)[0]
    a = publier(client, images=[url])
    reponse = client.patch(f"/annonces/{a['id']}", json=annonce(images=[]))
    assert reponse.status_code == 200
    assert services.images_detruites == ["gendon/img1"]


def test_supprimer_annonce_supprime_ses_photos(client, services):
    url = uploader(client)[0]
    a = publier(client, images=[url])
    client.delete(f"/annonces/{a['id']}")
    assert services.images_detruites == ["gendon/img1"]


def test_maximum_cinq_photos(client):
    fichiers = [("files", (f"{i}.jpg", b"image", "image/jpeg")) for i in range(6)]
    assert client.post("/upload", files=fichiers).status_code == 400


def test_type_de_fichier_refuse(client):
    fichiers = [("files", ("virus.exe", b"MZ", "application/octet-stream"))]
    assert client.post("/upload", files=fichiers).status_code == 400


def test_rate_limit_compte_les_photos(client):
    """30 photos par heure : 6 envois de 5 passent, le 7e est refusé."""
    fichiers = [("files", (f"{i}.jpg", b"image", "image/jpeg")) for i in range(5)]
    codes = [client.post("/upload", files=fichiers).status_code for _ in range(7)]
    assert codes == [200] * 6 + [429]


def test_purge_des_photos_orphelines(client, services, db):
    url_publiee, url_orpheline = uploader(client, 2)
    publier(client, images=[url_publiee])
    # Les deux photos ont plus de 2 jours
    db.query(models.ImageUploadee).update(
        {models.ImageUploadee.created_at: datetime.now(timezone.utc) - timedelta(days=5)}
    )
    db.commit()
    main.purger_images_orphelines()
    assert services.images_detruites == ["gendon/img2"]
    restantes = {i.url for i in db.query(models.ImageUploadee).all()}
    assert restantes == {url_publiee}


def test_photo_recente_non_purgee(client, services):
    uploader(client)
    main.purger_images_orphelines()
    assert services.images_detruites == []
