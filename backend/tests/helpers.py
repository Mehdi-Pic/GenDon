def uploader(client, nombre=1):
    """Envoie `nombre` photos et renvoie leurs URL."""
    fichiers = [("files", (f"{i}.jpg", b"image", "image/jpeg")) for i in range(nombre)]
    reponse = client.post("/upload", files=fichiers)
    assert reponse.status_code == 200, reponse.text
    return reponse.json()["urls"]


def annonce(**champs):
    donnees = {
        "titre": "Canapé 3 places",
        "description": "Bon état",
        "categorie": "Mobilier",
        "quartier": "Le Luth",
        "images": [],
    }
    donnees.update(champs)
    return donnees


def publier(client, **champs):
    reponse = client.post("/annonces", json=annonce(**champs))
    assert reponse.status_code == 200, reponse.text
    return reponse.json()
