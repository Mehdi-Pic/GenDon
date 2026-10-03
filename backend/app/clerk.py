"""Accès à l'API Clerk (comptes utilisateurs). Les autres modules appellent ces fonctions
via le module (clerk.pseudo_clerk(...)) : les tests peuvent ainsi les remplacer."""
import os

import httpx

API_CLERK = "https://api.clerk.com/v1"
MAX_UTILISATEURS_CLERK = 20000  # garde-fou contre une boucle infinie


def _entetes() -> dict:
    return {"Authorization": f"Bearer {os.getenv('CLERK_SECRET_KEY')}"}


def email_principal(user: dict):
    primary_id = user.get("primary_email_address_id")
    return next((e["email_address"] for e in user.get("email_addresses", []) if e["id"] == primary_id), None)


def pseudo_depuis_clerk(user: dict) -> str:
    return (user.get("username") or user.get("first_name") or "Un habitant")[:50]


def utilisateur(user_id: str):
    """Compte Clerk complet, ou None si introuvable ou si Clerk ne répond pas."""
    try:
        r = httpx.get(f"{API_CLERK}/users/{user_id}", headers=_entetes(), timeout=10)
        if r.is_success:
            return r.json()
    except Exception:
        pass
    return None


def email_utilisateur(user_id: str):
    compte = utilisateur(user_id)
    return email_principal(compte) if compte else None


def pseudo_clerk(user_id: str) -> str:
    """Pseudo d'affichage d'un utilisateur, lu chez Clerk (jamais fourni par le client)."""
    compte = utilisateur(user_id)
    return pseudo_depuis_clerk(compte) if compte else "Un habitant"


def tous_les_utilisateurs(ordre: str = "-created_at") -> list:
    """Récupère tous les comptes Clerk (pagination par lots de 100)."""
    utilisateurs, offset = [], 0
    while offset < MAX_UTILISATEURS_CLERK:
        try:
            r = httpx.get(
                f"{API_CLERK}/users?limit=100&offset={offset}&order_by={ordre}",
                headers=_entetes(),
                timeout=15,
            )
        except Exception:
            break
        if not r.is_success:
            break
        lot = r.json()
        utilisateurs.extend(lot)
        if len(lot) < 100:
            break
        offset += 100
    return utilisateurs


def suspendre(user_id: str, suspendu: bool) -> bool:
    """Bannit (ou réactive) un compte chez Clerk : ses sessions sont révoquées et il ne peut
    plus se connecter. Renvoie False si Clerk a refusé ou n'a pas répondu."""
    action = "ban" if suspendu else "unban"
    try:
        r = httpx.post(f"{API_CLERK}/users/{user_id}/{action}", headers=_entetes(), timeout=10)
        return r.is_success
    except Exception:
        return False
