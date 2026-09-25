import io
from datetime import datetime, timedelta, timezone

from PIL import Image

from app import main, models

from helpers import IMAGE, annonce, image_jpeg, publier, uploader


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
    fichiers = [("files", (f"{i}.jpg", IMAGE, "image/jpeg")) for i in range(6)]
    assert client.post("/upload", files=fichiers).status_code == 400


def test_type_de_fichier_refuse(client):
    fichiers = [("files", ("virus.exe", b"MZ", "application/octet-stream"))]
    assert client.post("/upload", files=fichiers).status_code == 400


def test_rate_limit_compte_les_photos(client):
    """30 photos par heure : 6 envois de 5 passent, le 7e est refusé."""
    fichiers = [("files", (f"{i}.jpg", IMAGE, "image/jpeg")) for i in range(5)]
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


# ---------- Métadonnées des photos (EXIF / GPS) ----------

def exif_avec_gps():
    exif = Image.Exif()
    exif[0x010F] = "MarqueTelephone"            # fabricant
    exif[0x0112] = 6                            # orientation : photo prise en portrait
    gps = exif.get_ifd(0x8825)
    gps[1], gps[2] = "N", (48.0, 55.0, 30.0)    # latitude de Gennevilliers
    gps[3], gps[4] = "E", (2.0, 17.0, 45.0)
    return exif


def test_gps_et_exif_retires_avant_cloudinary(client, services):
    photo = image_jpeg(taille=(40, 20), exif=exif_avec_gps())
    assert Image.open(io.BytesIO(photo)).getexif().get_ifd(0x8825)  # la photo d'origine a bien un GPS

    reponse = client.post("/upload", files=[("files", ("photo.jpg", photo, "image/jpeg"))])
    assert reponse.status_code == 200, reponse.text

    envoye = Image.open(io.BytesIO(services.contenus_envoyes[0]))
    assert len(envoye.getexif()) == 0
    assert "exif" not in envoye.info
    # La rotation indiquée dans l'EXIF est appliquée : la photo reste droite
    assert envoye.size == (20, 40)


def test_png_sans_metadonnees_texte(client, services):
    from PIL import PngImagePlugin
    infos = PngImagePlugin.PngInfo()
    infos.add_text("Author", "Prénom Nom")
    sortie = io.BytesIO()
    Image.new("RGBA", (5, 5)).save(sortie, format="PNG", pnginfo=infos)
    client.post("/upload", files=[("files", ("a.png", sortie.getvalue(), "image/png"))])
    envoye = Image.open(io.BytesIO(services.contenus_envoyes[0]))
    assert "Author" not in envoye.info


def test_gif_anime_reste_anime(client, services):
    trames = [Image.new("RGB", (4, 4), couleur) for couleur in ("red", "green", "blue")]
    sortie = io.BytesIO()
    trames[0].save(sortie, format="GIF", save_all=True, append_images=trames[1:], comment=b"secret", duration=50)
    assert Image.open(io.BytesIO(sortie.getvalue())).n_frames == 3
    client.post("/upload", files=[("files", ("a.gif", sortie.getvalue(), "image/gif"))])
    envoye = Image.open(io.BytesIO(services.contenus_envoyes[0]))
    assert envoye.n_frames == 3
    assert "comment" not in envoye.info


def test_fichier_qui_n_est_pas_une_image_refuse(client, services):
    reponse = client.post("/upload", files=[("files", ("faux.jpg", b"pas une image", "image/jpeg"))])
    assert reponse.status_code == 400
    assert services.contenus_envoyes == []
