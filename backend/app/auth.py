import os
import time
from typing import Optional
import httpx
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()
security_optionnelle = HTTPBearer(auto_error=False)
_jwks: Optional[dict] = None
_jwks_charge_a = 0.0
# Un kid inconnu declenche un rechargement des cles, au plus une fois par minute :
# sinon n'importe qui pourrait forcer un appel a Clerk a chaque requete
DELAI_RECHARGEMENT_JWKS = 60


def _charger_jwks(force: bool = False) -> dict:
    global _jwks, _jwks_charge_a
    if force and _jwks is not None and time.monotonic() - _jwks_charge_a < DELAI_RECHARGEMENT_JWKS:
        return _jwks
    if _jwks is None or force:
        url = os.getenv("CLERK_JWKS_URL")
        if not url:
            raise HTTPException(status_code=500, detail="CLERK_JWKS_URL non configurée")
        try:
            _jwks = httpx.get(url, timeout=5).json()
            _jwks_charge_a = time.monotonic()
        except Exception:
            raise HTTPException(status_code=500, detail="Impossible de récupérer les clés Clerk")
    return _jwks


def _decoder_token(token: str) -> str:
    header = jwt.get_unverified_header(token)
    jwks = _charger_jwks()
    key_data = next((k for k in jwks["keys"] if k["kid"] == header.get("kid")), None)
    if not key_data:
        # kid inconnu : Clerk a peut-être tourné ses clés → on rafraîchit une fois
        jwks = _charger_jwks(force=True)
        key_data = next((k for k in jwks["keys"] if k["kid"] == header.get("kid")), None)
    if not key_data:
        raise HTTPException(status_code=401, detail="Clé JWT introuvable")
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
    payload = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        options={"verify_aud": False},
    )
    # azp = origine du site qui a obtenu le token. Verifie si CLERK_AUTHORIZED_PARTIES est defini
    # (origines separees par des virgules, ex. https://www.gendon.fr,https://gendon.fr)
    autorises = [o.strip().rstrip("/") for o in os.getenv("CLERK_AUTHORIZED_PARTIES", "").split(",") if o.strip()]
    if autorises and payload.get("azp") and payload["azp"].rstrip("/") not in autorises:
        raise jwt.InvalidTokenError("azp non autorise")
    return payload["sub"]


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    try:
        return _decoder_token(credentials.credentials)
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expirée, reconnectez-vous")
    except (jwt.InvalidTokenError, KeyError):
        raise HTTPException(status_code=401, detail="Token invalide")


def get_user_id_optionnel(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_optionnelle),
) -> Optional[str]:
    """Pour les endpoints publics : identifie l'utilisateur si un token valide est fourni, sinon None."""
    if credentials is None:
        return None
    try:
        return _decoder_token(credentials.credentials)
    except Exception:
        return None
