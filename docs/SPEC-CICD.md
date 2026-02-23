# SPEC-CICD — GitHub Actions CI/CD

## Contexte

Automatiser le build, les tests et le déploiement sur Pi des deux services :
- `personal-page` — Astro static site servi par nginx
- `syncobsidian` — FastAPI backend + plugin Obsidian TypeScript

Actuellement tout est manuel (build local, scp, ssh). L'objectif est un pipeline complet déclenché par tag Git.

## Stratégie de déclenchement

- **push sur `main`** → build + tests uniquement (feedback rapide)
- **tag `v*`** → build + tests + push image GHCR + deploy SSH sur Pi

## Architecture des workflows

### 1. personal-page — `.github/workflows/deploy.yml`

```
Trigger: push main OU tag v*
Jobs:
  build-test:
    - checkout
    - npm ci
    - npm run build  (astro build → dist/)
    - (pas de tests unitaires Astro, le build suffit)
    - docker buildx build --platform linux/arm64 -t ghcr.io/<owner>/personal-page:$TAG
    - push GHCR (seulement si tag)

  deploy: (seulement si tag, dépend de build-test)
    - SSH sur Pi
    - docker pull ghcr.io/<owner>/personal-page:$TAG
    - docker compose up -d --force-recreate
```

### 2. syncobsidian — `.github/workflows/deploy.yml`

```
Trigger: push main OU tag v*
Jobs:
  test-backend:
    - checkout
    - python 3.11
    - pip install -r backend/requirements-test.txt
    - pytest backend/tests/ (via pytest.ini)

  test-plugin:
    - checkout
    - node 20
    - npm ci (dans obsidian-plugin/)
    - npm test

  build-push: (dépend de test-backend + test-plugin, seulement si tag)
    - docker buildx build --platform linux/arm64 -t ghcr.io/<owner>/syncobsidian:$TAG
    - push GHCR

  deploy: (dépend de build-push, seulement si tag)
    - SSH sur Pi
    - cd ~/apps/syncobsidian/backend
    - docker pull ghcr.io/<owner>/syncobsidian:$TAG
    - docker compose -f docker-compose.prod.yml up -d --force-recreate
```

## Secrets GitHub à configurer

Dans chaque repo → Settings → Secrets and variables → Actions :

| Secret | Valeur | Usage |
|--------|--------|-------|
| `PI_SSH_KEY` | clé privée SSH (Ed25519) | connexion Pi |
| `PI_HOST` | IP publique du Pi | SSH |
| `PI_USER` | `nico` | SSH |
| `PI_SSH_PORT` | `20022` | SSH (port non-standard) |

Note: `GITHUB_TOKEN` est fourni automatiquement par GitHub Actions — il suffit pour push sur GHCR.

## Accès SSH Pi depuis GitHub Actions

Le Pi est accessible sur le port 20022. Étapes de setup :

1. Générer une paire de clés SSH dédiée CI (à faire une seule fois) :
   ```bash
   ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions_ci
   ```

2. Ajouter la clé publique sur le Pi :
   ```bash
   ssh-copy-id -i ~/.ssh/github_actions_ci.pub -p 20022 nico@<pi-ip>
   ```

3. Copier la clé privée dans le secret GitHub `PI_SSH_KEY` :
   ```bash
   cat ~/.ssh/github_actions_ci
   ```

## Fichiers à créer

- `personal-page/.github/workflows/deploy.yml`
- `syncobsidian/.github/workflows/deploy.yml`

## Points d'attention

- Les images sont buildées pour `linux/arm64` (Pi ARM) avec `docker buildx`
- GHCR est gratuit pour les repos publics et privés (inclus dans GitHub Free)
- L'image dans `docker-compose.prod.yml` (syncobsidian) devra référencer le tag GHCR plutôt qu'un build local
- Pour personal-page, même chose dans `docker-compose.yml`

## Vérification

1. Push sur `main` → onglet Actions → jobs build+test verts
2. Créer un tag et pousser :
   ```bash
   git tag v0.1.0 && git push --tags
   ```
3. Voir le job deploy se déclencher dans Actions
4. Vérifier sur le Pi :
   ```bash
   docker ps  # nouvelle image avec le bon tag
   curl https://nicolasl.fr
   curl https://sync.nicolasl.fr/health
   ```
