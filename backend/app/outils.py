"""Outils transverses : limitation de débit, IP du visiteur, recherche textuelle."""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request
from sqlalchemy import func

# Rate limiting en mémoire par utilisateur (1 seule instance Railway).
_appels: dict = defaultdict(deque)
_verrou_appels = threading.Lock()
FENETRE_MAX_SECONDES = 24 * 3600  # plus grande fenêtre utilisée (plafond quotidien du contact) : sert au nettoyage


def limite_atteinte(user_id: str, action: str, maximum: int, fenetre_secondes: int, poids: int = 1) -> bool:
    """Enregistre `poids` appels et renvoie True (sans rien enregistrer) si la limite serait dépassée."""
    cle = f"{action}:{user_id}"
    maintenant = time.monotonic()
    with _verrou_appels:
        appels = _appels[cle]
        while appels and maintenant - appels[0] > fenetre_secondes:
            appels.popleft()
        if len(appels) + poids > maximum:
            return True
        appels.extend([maintenant] * poids)
        return False


def verifier_rate_limit(user_id: str, action: str, maximum: int, fenetre_secondes: int, poids: int = 1) -> None:
    if limite_atteinte(user_id, action, maximum, fenetre_secondes, poids):
        raise HTTPException(status_code=429, detail="Trop de requêtes, réessayez plus tard")


def nettoyer_rate_limit():
    """Retire les compteurs inactifs : sans cela le dictionnaire grossit indéfiniment."""
    limite = time.monotonic() - FENETRE_MAX_SECONDES
    with _verrou_appels:
        for cle in [c for c, appels in _appels.items() if not appels or appels[-1] < limite]:
            del _appels[cle]


def ip_client(request: Request) -> str:
    """IP réelle du visiteur. On prend la DERNIÈRE entrée de X-Forwarded-For, ajoutée par le proxy
    Railway : la première peut être écrite librement par le client (contournement du rate limit)."""
    transmis = request.headers.get("x-forwarded-for", "")
    if transmis:
        return transmis.split(",")[-1].strip()
    return request.client.host if request.client else "inconnu"


def echapper_like(terme: str) -> str:
    """Neutralise les jokers LIKE (% et _) pour qu'ils soient cherchés littéralement."""
    return terme.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")



# Recherche insensible aux accents : « velo » trouve « Vélo ». Même table de correspondance
# côté Python (terme saisi) et côté Postgres (colonnes), via translate() : aucune extension
# à installer sur la base. Les majuscules accentuées sont listées car lower() ne les convertit
# pas sur une base en locale « C ».
_ACCENTS = "àáâãäåçèéêëìíîïñòóôõöùúûüýÿÀÁÂÃÄÅÇÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝŸ"
_SANS_ACCENTS = "aaaaaaceeeeiiiinooooouuuuyyaaaaaaceeeeiiiinooooouuuuyy"
_TABLE_ACCENTS = str.maketrans(_ACCENTS, _SANS_ACCENTS)


def sans_accents(texte: str) -> str:
    return texte.lower().translate(_TABLE_ACCENTS)


def colonne_sans_accents(colonne):
    return func.translate(func.lower(colonne), _ACCENTS, _SANS_ACCENTS)


def filtre_recherche(terme: str, *colonnes):
    """Condition « le terme apparaît dans l'une des colonnes », sans tenir compte des accents ni de la casse."""
    motif = f"%{echapper_like(sans_accents(terme.strip()[:100]))}%"
    condition = None
    for colonne in colonnes:
        c = colonne_sans_accents(colonne).like(motif, escape="\\")
        condition = c if condition is None else condition | c
    return condition
