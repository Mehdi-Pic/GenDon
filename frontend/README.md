# GenDon : site (Next.js)

Voir le [README principal](../README.md) pour la présentation du projet.

## Lancer en local

L'API (dossier `backend`) doit tourner, par défaut sur `http://localhost:8000`.

```bash
cp .env.example .env.local   # puis renseigner les clés Clerk
npm ci
npm run dev                  # http://localhost:3000
```

## Vérifications (les mêmes que la CI)

```bash
npx tsc --noEmit
npx eslint app --max-warnings 0
npm run build
```
