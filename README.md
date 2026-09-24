# GenDon

**Plateforme de dons gratuits entre habitants de Gennevilliers (92).**
Un site local où chacun peut déposer un objet dont il n'a plus besoin et le donner à un voisin, sans argent ni transaction.

🔗 **En production : [gendon.fr](https://www.gendon.fr)**

---

## À propos

GenDon est une application web full-stack développée et déployée de bout en bout.
Objectif : faciliter le réemploi local à l'échelle d'une ville, dans l'esprit d'un "Leboncoin du don" hyper-local.

Projet d'apprentissage du développement web (Frontend + Backend + services externes), conçu avec l'accompagnement de Claude comme pédagogue.

## Stack technique

- **Frontend** : TypeScript, Next.js (App Router, React), Tailwind CSS · hébergé sur **Vercel**
- **Backend** : Python, FastAPI, SQLAlchemy, APScheduler · hébergé sur **Railway**
- **Base de données** : PostgreSQL (Railway)
- **CI** : GitHub Actions (tests, types, lint à chaque pull request)

**Services externes**
- **Clerk** : authentification, gestion des comptes, webhooks (suppression de compte, changement de pseudo)
- **Cloudinary** : stockage et optimisation des images
- **Resend** : emails (notification de message, rappel d'expiration, lettre hebdomadaire, formulaire de contact)
- **OVH** : nom de domaine et DNS
- **Google Search Console** : indexation

## Fonctionnalités

**Pour les habitants**
- 🔐 Inscription / connexion (Clerk)
- 📝 Dépôt d'une annonce avec jusqu'à 5 photos (compression côté navigateur + upload Cloudinary)
- 🔎 Listing paginé avec filtres (catégorie, quartier, recherche, tri, période, avec photo)
- ❤️ Favoris et compteur de vues (une vue par visiteur toutes les 6 h)
- 💬 Messagerie intégrée entre donneur et intéressé, sans exposer les adresses email, avec notification par email et signalement d'une conversation
- ✅ « Objet donné » : l'annonce quitte le site sous 3 jours et le don est compté sur la page d'accueil
- 🔁 Renouvellement d'une annonce pour 30 jours de plus (à partir de 7 jours d'ancienneté)
- 👤 Espace profil : mes annonces et mes favoris
- 📰 Lettre hebdomadaire (jeudi 18h30) avec les derniers dons, désabonnement en un clic
- 📨 Formulaire de contact vers l'équipe (anti-robots et anti-spam)
- 🛟 Message « Service momentanément indisponible » si l'API ne répond pas, au lieu d'un site qui paraît vide
- 📱 Interface responsive, optimisée mobile
- 🔍 SEO : sitemap dynamique, métadonnées Open Graph (aperçus riches au partage)

**Pour l'équipe (panel `/admin`)**
- Rôles administrateur / modérateur
- Statistiques, recherche et suppression d'annonces, liste des comptes
- Traitement des signalements, journal des actions de modération

**Automatismes (backend)**
- Expiration des annonces après 30 jours, avec email de rappel à J-3
- Nettoyage des photos envoyées mais jamais publiées (48 h)
- Suppression de toutes les données d'un utilisateur à la suppression de son compte Clerk (RGPD)

## Architecture

Frontend et backend sont **séparés** et communiquent via une API REST :

```
Navigateur ─▶ Next.js (Vercel) ─▶ API FastAPI (Railway) ─▶ PostgreSQL
                                   │
                                   ├─ Clerk      (auth, vérification JWT, webhooks)
                                   ├─ Cloudinary (images)
                                   └─ Resend     (emails)
```

L'authentification repose sur la **vérification des tokens JWT de Clerk côté serveur** (JWKS / RS256). Les endpoints publics utilisent une authentification optionnelle qui permet de calculer côté serveur les informations propres à l'utilisateur (ses annonces, ses favoris) sans qu'elles soient falsifiables par le client.

**Choix de sécurité notables**
- Le pseudo affiché et le statut d'une annonce sont fixés par le serveur, jamais par le client
- Une annonce ne peut contenir que des photos envoyées par son auteur (registre des uploads)
- Limites de débit par compte ou par IP (upload, messages, signalements, contact)
- Documentation de l'API (`/docs`) désactivée en production

## Déploiement

- Chaque merge sur `main` déploie automatiquement le frontend (Vercel) et le backend (Railway).
- `main` est protégée : on ne peut merger une pull request que si la CI est verte.
- Railway attend la CI verte avant de déployer le backend (option *Wait for CI*).
- Le schéma de la base est créé et migré au démarrage du backend (`backend/app/main.py`).

**Variables d'environnement** (noms uniquement, les valeurs sont dans Railway et Vercel)

| Backend (Railway) | Rôle |
| :--- | :--- |
| `DATABASE_URL` | Connexion PostgreSQL (référence vers le service Postgres) |
| `CLERK_JWKS_URL`, `CLERK_SECRET_KEY` | Vérification des tokens, appels à l'API Clerk |
| `CLERK_WEBHOOK_SECRET` | Signature des webhooks Clerk (`user.deleted`, `user.updated`) |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Stockage des photos |
| `RESEND_API_KEY`, `RESEND_FROM_EMAIL` | Envoi des emails |
| `FRONTEND_URL` | Origines autorisées (CORS) et liens dans les emails |
| `ADMIN_USER_ID` | Identifiants Clerk des administrateurs principaux |
| `NEWSLETTER_SECRET` *(optionnel)* | Clé des liens de désabonnement (sinon `CLERK_SECRET_KEY`) |
| `CLERK_AUTHORIZED_PARTIES` *(optionnel)* | Origines autorisées à émettre des tokens |
| `ENABLE_DOCS` *(optionnel)* | `1` pour activer `/docs` en local |

| Frontend (Vercel) | Rôle |
| :--- | :--- |
| `NEXT_PUBLIC_API_URL` | Adresse de l'API |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY` | Authentification Clerk |

## Tests et CI

À chaque pull request et à chaque push sur `main`, GitHub Actions lance
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) :

- **Backend (tests)** : 45 tests pytest sur une base Postgres jetable : annonces, photos, messagerie, suppression de compte, tâches planifiées, newsletter, sécurité, et cohérence des catégories et quartiers entre le site et l'API
- **Frontend (TypeScript)** : vérification des types et lint (aucune erreur ni aucun avertissement toléré)

Le résultat s'affiche en bas de chaque pull request et dans l'onglet **Actions** du dépôt.

Pour lancer les tests en local, il faut une base Postgres **dédiée**
(les tests la vident à chaque exécution ; une adresse Railway est refusée) :

```bash
cd backend
pip install -r requirements-dev.txt
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/gendon_test pytest
```

Côté frontend :

```bash
cd frontend
npm ci
npx tsc --noEmit
npx eslint app --max-warnings 0
```

## Pistes d'amélioration

- Suivi d'erreurs (Sentry)
- Consentement explicite à la lettre d'information dans le profil
- Notification au propriétaire quand un modérateur supprime son annonce
- Arrêt du rafraîchissement des messages quand l'onglet est en arrière-plan
- Catégories et quartiers servis par l'API (une seule source de vérité)
- Migrations de base de données avec Alembic
- Compatibilité Mac
