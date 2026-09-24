# GenDon

**Plateforme de dons gratuits entre habitants de Gennevilliers (92).**
Un site local où chacun peut déposer un objet dont il n'a plus besoin et le donner à un voisin, sans argent ni transaction.

🔗 **En ligne : [gendon.fr](https://www.gendon.fr)**

---

## À propos

Objectif : faciliter le réemploi local à l'échelle d'une ville, dans l'esprit d'un « Leboncoin du don » hyper-local.

Projet d'apprentissage du développement web (frontend, backend et services externes), développé et déployé de bout en bout avec l'accompagnement de Claude comme pédagogue.

## Ce qu'on peut faire sur GenDon

- 📝 **Donner** : déposer une annonce avec jusqu'à 5 photos, en quelques minutes
- 🔎 **Chercher** : parcourir les dons par catégorie, par quartier ou par mot-clé
- 💬 **Échanger** : discuter avec le donneur via la messagerie du site, sans partager son adresse email
- ❤️ **Suivre** : garder ses annonces préférées en favoris
- ✅ **Clôturer** : indiquer qu'un objet a été donné ; chaque don réalisé est compté sur la page d'accueil
- 🔁 **Prolonger** : une annonce reste en ligne 30 jours et peut être renouvelée
- 📰 **Être informé** : recevoir chaque jeudi les derniers dons publiés (désabonnement en un clic)
- 🛡️ **Signaler** : une annonce ou une conversation problématique, traitée par l'équipe de modération

Le site est entièrement gratuit, sans publicité, et pensé d'abord pour le mobile.

## Sous le capot

- **Site** : Next.js, React, TypeScript, Tailwind CSS
- **API** : Python, FastAPI, PostgreSQL
- **Services** : Clerk (comptes), Cloudinary (photos), Resend (emails)
- **Qualité** : tests automatiques et vérifications à chaque modification (GitHub Actions)

```
Navigateur ─▶ Site Next.js ─▶ API FastAPI ─▶ PostgreSQL
```
