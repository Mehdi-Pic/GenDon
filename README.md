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

- **Frontend** — TypeScript, Next.js (App Router, React), Tailwind CSS · hébergé sur **Vercel**
- **Backend** — Python, FastAPI, SQLAlchemy · hébergé sur **Railway**
- **Base de données** — PostgreSQL

**Services externes**
- **Clerk** — authentification et gestion des comptes
- **Cloudinary** — stockage et optimisation des images
- **Resend** — emails transactionnels (mise en relation, rappels)
- **OVH** — nom de domaine et DNS
- **Google Search Console** — indexation

## Fonctionnalités

- 🔐 Inscription / connexion (Clerk)
- 📝 Dépôt d'une annonce avec jusqu'à 5 photos (compression côté navigateur + upload Cloudinary)
- 🔎 Listing paginé avec filtres (catégorie, quartier, recherche, tri, période) et recherche texte
- ❤️ Favoris et compteur de vues par annonce
- ✉️ Mise en relation avec le donneur par email (sans exposer les adresses)
- 👤 Espace profil : mes annonces et mes favoris
- 🗑️ Expiration automatique des annonces après 30 jours (+ email de rappel à J-3)
- 📱 Interface responsive, optimisée mobile
- 🔍 SEO : sitemap dynamique, métadonnées Open Graph (aperçus riches au partage)

## Architecture

Frontend et backend sont **séparés** et communiquent via une API REST :

```
Navigateur ─▶ Next.js (Vercel) ─▶ API FastAPI (Railway) ─▶ PostgreSQL
                                   │
                                   ├─ Clerk      (auth, vérification JWT)
                                   ├─ Cloudinary (images)
                                   └─ Resend     (emails)
```

L'authentification repose sur la **vérification des tokens JWT de Clerk côté serveur** (JWKS / RS256). Les endpoints publics utilisent une authentification optionnelle qui permet de calculer côté serveur les informations propres à l'utilisateur (ses annonces, ses favoris) sans qu'elles soient falsifiables par le client.

## Pistes d'amélioration

- Bouton "Signaler" et interface de modération
- Suppression de compte en self-service (RGPD)
- Suivi d'erreurs (Sentry)
- Tests automatisés (pytest / CI)
