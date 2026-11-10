# Audit de GenDon

Date : 10 novembre 2026. Périmètre : dépôt à l'état du commit `d2a6a4d` (backend FastAPI, frontend Next.js, CI).

## Suivi des corrections

Toutes les corrections ont été faites dans la foulée de l'audit. 111 tests backend verts (90 avant), `alembic check`, `tsc`, `eslint` et `npm run build` propres, `npm audit` et `pip-audit` sans faille.

| Point | État |
|---|---|
| 1. Dépendances | Corrigé : Next 16.4.6, Pillow 13.0.0, PyJWT 2.15.1, cryptography 50.0.2, `npm audit fix`. Dependabot activé (`.github/dependabot.yml`). |
| 2. Journalisation | Corrigé : `logging` configuré dans `main.py`, chaque erreur avalée est journalisée (visible dans les journaux Railway). |
| 3. Recontact | Corrigé : le demandeur qui avait quitté revient dans sa conversation (message « X est revenu ») ; si c'est le donneur qui est parti, erreur explicite. |
| 4. Limites de débit | Corrigé : 10 publications par jour, 30 annonces en ligne par compte, 30 modifications et 30 nouvelles conversations par heure. |
| 5. Cache des clés Clerk | Corrigé : une réponse d'erreur n'est plus mise en cache ; un rechargement raté garde les clés connues. |
| 6. Conversations vides | Corrigé : invisibles côté donneur et non comptées comme intéressés tant que personne n'a écrit, purgées après 24 h. |
| 7. Tests de `auth.py` | Corrigé : `tests/test_auth.py` (jeton valide, expiré, mauvaise clé, non signé, `azp`, rotation, erreurs Clerk, webhook signé ou non). Pas de test frontend ajouté. |

Mineurs corrigés : alertes conservées si Clerk ne répond pas ; images limitées à 40 millions de pixels et GIF à 200 trames ; lecture d'une conversation par l'équipe limitée aux signalements en attente (lien masqué dans l'admin après traitement) ; comptes suspendus exclus de la newsletter et des rappels ; pastille de messages en pause quand l'onglet est masqué ; message de désabonnement sans « expiré » ; index ajoutés (migration `0005`) ; `.env.example`, README frontend et procédure locale ; `middleware.ts` renommé en `proxy.ts` (convention de Next 16).

Mineurs laissés en l'état, à décider : renouvellement qui réécrit la date de publication (demande une colonne `expire_at` et une migration de données) ; signalement effacé avec l'annonce ; suspendu encore joignable par ses interlocuteurs ; liste admin rechargeant tous les comptes Clerk ; `List-Unsubscribe-Post` (demande un point d'entrée dédié) ; `Content-Security-Policy` (à régler avec Clerk et Vercel Analytics, risque de casser la connexion) ; duplication des gabarits d'email ; tâches planifiées en mémoire ; licence (choix du propriétaire).

Les cinq points « À vérifier en production » restent à vérifier.

## Verdict

Le projet est sain. Aucun problème BLOQUANT trouvé : pas de faille d'accès aux données d'autrui, pas d'injection, pas de secret dans le dépôt. Le contrôle d'accès est fait partout côté serveur et il est correct.

Les vrais risques sont ailleurs : des dépendances en retard de correctifs de sécurité, une absence totale de journalisation (une panne d'email ou de purge passe inaperçue), et deux bugs fonctionnels confirmés dans la messagerie et la publication.

## Méthode et limites

Fait :

- lecture intégrale du backend (`backend/app`, migrations) ;
- lecture du frontend : pages publiques, messagerie, admin, appels API, pages légales (les 600 lignes de `profil/page.tsx` et les pages admin secondaires ont été survolées, pas lues ligne à ligne) ;
- exécution réelle : `pytest` (90 tests, tous verts), `alembic check` (schéma à jour), `tsc --noEmit` (0 erreur), `eslint --max-warnings 0` (0 avertissement), `npm audit`, `pip-audit` ;
- reproduction des bugs 3, 4 et 6 par un test jetable (non conservé dans le dépôt).

Non vérifié, car hors du dépôt : la configuration de production (variables Railway et Vercel, sauvegardes, protection de branche), le comportement réel des en-têtes du proxy Railway, le rendu visuel et l'accessibilité au clavier ou au lecteur d'écran. Le build Next.js n'a pas été lancé. Le détail de chaque avis de sécurité n'a pas été analysé : seuls leur nombre et la version corrigée sont rapportés.

## IMPORTANT

### 1. Dépendances avec des failles connues

| Paquet | Version | Avis | Corrigé en | Exposition |
|---|---|---|---|---|
| `next` | 16.2.6 | 20, dont critiques | au-delà de 16.4.0 | tout le site |
| `pillow` | 12.3.0 | 39 | 13.0.0 | décode les photos envoyées par n'importe quel inscrit |
| `pyjwt` | 2.13.0 | 15 | 2.15.0 | vérifie chaque jeton de connexion |
| `cryptography` | 48.0.1 | 6 | 50.0.0 | signature des jetons |

Les trois paquets Python sont précisément ceux qui traitent des données non fiables. Pour Next, plusieurs avis critiques visent des cas qui ne s'appliquent probablement pas ici (hébergement Windows, serveur autonome, `next/og`, `use cache`), mais je ne les ai pas vérifiés un par un : la mise à jour coûte moins cher que l'analyse.

Cause de fond : rien ne signale ces retards. Ni Dependabot, ni `npm audit` ou `pip-audit` dans la CI.

Correction : mettre à jour ces quatre paquets (Pillow 13 et Next sont des montées de version à tester, la suite de tests d'images couvre bien Pillow), puis ajouter `.github/dependabot.yml` pour `pip` et `npm`.

### 2. Aucune journalisation : les pannes sont invisibles

Le backend ne contient ni `logging`, ni Sentry, et 20 blocs `except Exception` qui avalent l'erreur, dont 10 dans `backend/app/taches.py`.

Conséquences concrètes :

- la newsletter du jeudi peut échouer entièrement (`taches.py:274`, `except Exception: pass`) sans laisser de trace ;
- une purge qui échoue chaque nuit laisse les annonces expirées en ligne indéfiniment ;
- une suppression Cloudinary ratée (`photos.py:44`) laisse des photos en ligne alors que la politique de confidentialité promet leur effacement ;
- un email « nouveau message » perdu (`emails.py:103`) ne se voit nulle part.

Correction : `logging.exception(...)` dans chaque bloc (les journaux Railway suffisent pour commencer), puis Sentry si le besoin d'alertes apparaît. C'est le chantier au meilleur rapport utilité sur effort de cette liste.

### 3. Bug : impossible de recontacter un donneur après avoir quitté la conversation (confirmé)

Scénario : un intéressé écrit au donneur, quitte la conversation, puis clique de nouveau sur « Contacter le donneur ».

`demarrer_conversation` (`backend/app/routers/messagerie.py:119`) renvoie la conversation existante sans regarder `demandeur_actif`. Le site redirige vers `/messages/{id}`, qui répond 404 puisque l'utilisateur l'a quittée. La contrainte d'unicité empêche d'en créer une autre : l'annonce devient définitivement incontactable pour cette personne.

Correction : si la conversation existe et que le demandeur l'a quittée, la réactiver (`demandeur_actif = True`, message système « X est revenu ») tant que le donneur est encore présent. Si le donneur l'a quittée, répondre par une erreur explicite au lieu d'un identifiant mort.

### 4. Publication et prise de contact sans limite de débit (confirmé)

`POST /annonces` n'a aucun plafond : 200 annonces publiées en rafale par un même compte passent toutes. Idem pour `PATCH /annonces/{id}` et `POST /conversations`. Les autres actions sont bien limitées (photos, messages, signalements, contact).

Un seul compte peut donc noyer le listing, la page d'accueil et le sitemap ; chaque publication lance en plus le calcul des alertes. Le plafond d'un email d'alerte par heure limite les dégâts côté email, pas côté site.

Correction : `verifier_rate_limit` sur la publication (par exemple 10 par jour) et sur l'ouverture de conversation (par exemple 30 par heure), plus un plafond d'annonces actives par compte.

### 5. Une mauvaise réponse de Clerk peut bloquer toutes les connexions jusqu'au redémarrage

`backend/app/auth.py:28` met en cache `httpx.get(url).json()` sans vérifier le code HTTP. Si Clerk répond une erreur au format JSON lors du premier chargement (429, 5xx), ce contenu est mémorisé. Ensuite `jwks["keys"]` lève `KeyError` à la ligne 37, avant le code de rechargement : chaque requête authentifiée reçoit « Token invalide », sans expiration du cache.

Peu probable, mais l'effet est une panne totale des comptes, silencieuse (voir point 2), qui ne se répare qu'en redéployant.

Correction : `raise_for_status()` et ne mémoriser la réponse que si elle contient `keys`.

### 6. Conversations vides comptées comme « personnes intéressées » (confirmé)

Cliquer sur « Contacter le donneur » crée la conversation avant tout message. Si la personne n'écrit rien, le donneur voit quand même une conversation vide dans sa liste et « 1 personne intéressée » sur son annonce (`annonces.py:128`). Combiné au point 4, un compte peut gonfler ce compteur sur toutes les annonces du site.

Correction la plus simple : ne lister et ne compter que les conversations ayant au moins un message d'utilisateur, et purger les conversations vides après 24 h.

### 7. Le code le plus sensible n'est pas testé

Les 90 tests remplacent systématiquement `get_current_user_id` : la vérification des jetons (`auth.py` : signature, expiration, `azp`, rotation des clés) n'est jamais exécutée par la suite. Même chose pour la vérification de signature du webhook Clerk. Côté frontend, aucun test : seuls les types, le lint et le build protègent des régressions.

Correction : 4 ou 5 tests sur `_decoder_token` avec une paire de clés générée dans le test (jeton valide, expiré, mauvaise clé, `azp` refusé, `kid` inconnu), et un test du webhook avec une signature invalide. Pour le frontend, un seul parcours Playwright (publier, contacter, réserver, donner) apporterait plus que des tests unitaires.

## MINEUR

- **Renouvellement** : il réécrit `created_at` (`annonces.py:213`). L'annonce renouvelée est donc renvoyée comme « nouveau don » aux alertes et réapparaît dans le filtre « cette semaine » ; la vraie date de publication est perdue. Une colonne `expire_at` distincte réglerait les trois effets.
- **Alertes perdues si Clerk ne répond pas** : `traiter_alertes_utilisateur` avance `verifie_jusqu_a` même quand l'adresse email n'a pas pu être lue (`taches.py:400-408`). Ces dons ne seront jamais signalés.
- **Images très grandes** : Pillow accepte jusqu'à environ 178 millions de pixels avant de refuser. Un fichier de quelques Mo peut consommer plusieurs centaines de Mo de mémoire au décodage et faire tomber l'instance. Fixer `Image.MAX_IMAGE_PIXELS` vers 40 millions, et plafonner le nombre de trames des GIF.
- **Conversation signalée lisible sans limite de durée** : `admin_lire_conversation` autorise la lecture dès qu'un signalement existe, même traité. La politique de confidentialité dit « pour traiter le signalement » : restreindre aux signalements en attente.
- **Signalement effacé avec l'annonce** : la suppression en cascade fait disparaître le signalement si l'auteur retire son annonce, donc la trace d'un comportement abusif.
- **Compte suspendu** : il reçoit encore la newsletter et les rappels d'expiration, et ses interlocuteurs peuvent continuer à lui écrire.
- **Liste des utilisateurs de l'admin** : elle recharge tous les comptes Clerk à chaque affichage (`admin.py:95`). Sans effet aujourd'hui, lent au-delà de quelques milliers de comptes.
- **Pastille de messages** : le `Header` interroge l'API toutes les 20 s même onglet masqué, contrairement aux pages de messagerie qui vérifient la visibilité.
- **Lien de désabonnement** : le message parle de lien « expiré » alors qu'il n'expire jamais ; l'en-tête `List-Unsubscribe` n'est pas accompagné de `List-Unsubscribe-Post` (désabonnement en un clic des messageries).
- **En-têtes de sécurité** : pas de `Content-Security-Policy` dans `next.config.ts`. Risque faible, React échappant tout le contenu affiché.
- **Code dupliqué** : `taches.py` et `contact.py` refont à la main les appels Clerk et le gabarit d'email que fournissent déjà `clerk.py` et `emails.py`.
- **Tâches planifiées en mémoire** : une tâche dont l'heure tombe pendant un redéploiement est sautée, et les compteurs de limitation de débit repartent de zéro à chaque déploiement. Acceptable avec une seule instance ; à revoir avant d'en lancer deux.
- **Documentation** : `frontend/README.md` est le modèle par défaut de Next.js ; pas de `.env.example` ni de procédure d'installation locale ; pas de licence alors que le dépôt est public.
- **Index** : aucun sur `annonces.clerk_user_id`, `annonces.created_at` ni `conversations.annonce_id`. Sans effet au volume d'une ville, les annonces étant purgées à 30 jours.

## À vérifier en production

Ces points ne se lisent pas dans le code :

1. `CLERK_AUTHORIZED_PARTIES` est-elle définie sur Railway ? Sans elle, le contrôle de l'origine du jeton (`azp`) est désactivé.
2. Les sauvegardes Postgres de Railway sont-elles activées, et une restauration a-t-elle déjà été essayée ?
3. Le service tourne-t-il bien sur une seule instance ? Les limites de débit et le planificateur le supposent.
4. `ip_client` prend la dernière adresse de `X-Forwarded-For`. C'est juste si le proxy Railway ajoute l'adresse réelle en dernier ; à contrôler une fois sur une requête réelle, sinon la limite par IP du formulaire de contact s'applique à la mauvaise adresse.
5. La branche `main` exige-t-elle une CI verte avant fusion ?

## Ce qui est bien fait

À conserver tel quel :

- **Contrôle d'accès** : propriété vérifiée sur chaque action, pseudo lu chez Clerk et jamais fourni par le client, rôles lus en base, réponses filtrées par schéma (aucun identifiant de compte ni adresse email ne fuit vers le public).
- **Photos** : réencodage systématique qui supprime EXIF et GPS, registre des images empêchant de référencer ou de faire supprimer celles d'un autre, nettoyage des orphelines.
- **Vie privée** : lecture des conversations par l'équipe conditionnée à un signalement et journalisée, emails masqués aux modérateurs, purge complète à la suppression du compte. La politique de confidentialité correspond au code, ce qui est rare.
- **Concurrence** : mises à jour atomiques pour le don, verrou sur les alertes, verrou consultatif pour les migrations, gestion des doubles clics par contrainte d'unicité.
- **CI** : tests sur une vraie base Postgres, contrôle de cohérence entre migrations et modèles, contrôle de cohérence des catégories entre frontend et backend, lint sans tolérance.

## Ordre de traitement recommandé

1. Mettre à jour les dépendances et activer Dependabot (point 1).
2. Ajouter la journalisation (point 2) : elle rend visibles tous les autres problèmes.
3. Corriger le bug de recontact et le cache JWKS (points 3 et 5) : quelques lignes chacun.
4. Limiter la publication et les prises de contact (points 4 et 6).
5. Tester `auth.py` (point 7).
