import os
from typing import Optional
import httpx
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()
_jwks: Optional[dict] = None


def _charger_jwks(force: bool = False) -> dict:
    global _jwks
    if _jwks is None or force:
        url = os.getenv("CLERK_JWKS_URL")
        if not url:
            raise HTTPException(status_code=500, detail="CLERK_JWKS_URL non configurée")
        try:
            _jwks = httpx.get(url, timeout=5).json()
        except Exception:
            raise HTTPException(status_code=500, detail="Impossible de récupérer les clés Clerk")
    return _jwks


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    token = credentials.credentials
    try:
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
        return payload["sub"]
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expirée, reconnectez-vous")
    except (jwt.InvalidTokenError, KeyError):
        raise HTTPException(status_code=401, detail="Token invalide")
