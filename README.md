# SyncObsidian - Synchronisation Auto-Hébergée pour Obsidian

Service de synchronisation Obsidian self-hosted permettant de synchroniser vos notes et pièces jointes sur tous vos appareils (desktop, iOS, Android).

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Obsidian       │     │  Obsidian       │     │  Obsidian       │
│  Desktop        │     │  iOS            │     │  Android        │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │ HTTPS REST API
                                 ▼
                    ┌────────────────────────┐
                    │   SyncObsidian API     │
                    │   (FastAPI + SQLite)   │
                    │   Docker Container     │
                    └────────────────────────┘
```

## Démarrage Rapide (Local)

### Backend (Serveur)

1. **Cloner et configurer** :
```bash
cd backend
cp .env.example .env
# Éditer .env et changer SECRET_KEY !
```

2. **Lancer avec Docker** :
```bash
docker compose up -d
```

3. **Créer un compte** :
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "monuser", "email": "email@example.com", "password": "monpassword"}'
```

### Plugin Obsidian

1. **Compiler le plugin** :
```bash
cd obsidian-plugin
npm install
npm run build
```

2. **Installer dans Obsidian** :
   - Copier `main.js` et `manifest.json` dans `.obsidian/plugins/syncobsidian/`
   - Activer le plugin dans les paramètres Obsidian

3. **Configurer** :
   - Ouvrir les paramètres du plugin
   - Entrer l'URL du serveur (ex: `https://sync.example.com`)
   - Entrer vos identifiants
   - Cliquer sur "Se connecter"

---

## 🚀 Déploiement Production (HTTPS)

Pour un déploiement accessible depuis Internet avec HTTPS :

1. **Prérequis** :
   - Un serveur avec Docker (VM, VPS, machine locale...)
   - Un nom de domaine pointant vers l'IP publique du serveur
   - Port 443 accessible depuis Internet (ou port custom + challenge DNS-01)

2. **Configurer l'environnement** :
```bash
cd backend
cp .env.example .env
nano .env
```

```env
SECRET_KEY=votre_cle_secrete_generee
DOMAIN=sync.example.com

# Si challenge DNS-01 (voir section Caddy ci-dessous)
OVH_ENDPOINT=ovh-eu
OVH_APPLICATION_KEY=xxx
OVH_APPLICATION_SECRET=xxx
OVH_CONSUMER_KEY=xxx
```

3. **Configurer Caddy** (voir section détaillée ci-dessous)

4. **Lancer en production** :
```bash
docker compose -f docker-compose.prod.yml up -d
```

5. **Configurer Obsidian** :
   - **URL du serveur** : `https://sync.example.com` (avec le port si différent de 443)
   - **Identifiants** : ceux créés via `/auth/register`

### Mise à jour du serveur

Pour mettre à jour le backend après avoir récupéré les dernières modifications :

```bash
# 1. Aller dans le répertoire backend
cd ~/apps/sync-obsidian/backend
# (ou le chemin où se trouve ton repo)

# 2. Récupérer les modifications
git pull

# 3. Reconstruire et redémarrer le service syncobsidian uniquement
docker compose -f docker-compose.prod.yml up -d --build syncobsidian
```

**Explication** :
- `--build` : Reconstruit l'image Docker avec le nouveau code
- `syncobsidian` : Reconstruit uniquement le service API (pas Caddy)
- `-d` : Mode détaché (en arrière-plan)

**Alternative** : Reconstruire tous les services (rarement nécessaire) :
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

**Vérifier que ça fonctionne** :
```bash
# Voir les logs du service
docker compose -f docker-compose.prod.yml logs syncobsidian

# Vérifier le statut
docker compose -f docker-compose.prod.yml ps
```

**Note** : Si la connexion SSH se coupe pendant le build :
```bash
# Vérifier que le build est terminé et le conteneur démarré
docker compose -f docker-compose.prod.yml ps

# Si le conteneur n'est pas démarré, relancer
docker compose -f docker-compose.prod.yml up -d
```

**Important** : Le service `syncobsidian` est le seul à reconstruire après un changement de code backend. Caddy ne change que si tu modifies `Dockerfile.caddy` ou `Caddyfile`.

---

## 🌐 Caddy - Reverse Proxy HTTPS

### Rôle de Caddy

Caddy est un reverse proxy qui gère automatiquement :
- **Certificats HTTPS** : obtention et renouvellement automatique via Let's Encrypt
- **Proxy** : redirige les requêtes HTTPS vers l'API (HTTP interne)
- **Sécurité** : headers de sécurité (HSTS, X-Frame-Options, etc.)

```
Internet (HTTPS:443)
        │
        ▼
    ┌───────┐
    │ Caddy │  ← TLS/HTTPS + certificats Let's Encrypt
    └───┬───┘
        │ HTTP:8000
        ▼
┌───────────────┐
│ SyncObsidian  │  ← API FastAPI
└───────────────┘
```

### Configuration du Caddyfile

Le fichier `backend/Caddyfile` définit le comportement de Caddy :

```caddyfile
{$DOMAIN:sync.example.com} {
    # Configuration TLS (voir options ci-dessous)
    tls {
        # ...
    }
    
    # Proxy vers l'API
    reverse_proxy syncobsidian:8000
    
    # Headers de sécurité
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
    }
}
```

### Méthodes d'obtention du certificat

#### Option 1 : Challenge HTTP-01 (par défaut)

Si le port 443 est directement accessible depuis Internet :

```caddyfile
{$DOMAIN:sync.example.com} {
    # Caddy obtient automatiquement le certificat
    reverse_proxy syncobsidian:8000
}
```

Let's Encrypt contacte votre serveur sur le port 80 pour vérifier que vous contrôlez le domaine.

#### Option 2 : Challenge DNS-01 (recommandé si port 80/443 bloqué)

Si vous ne pouvez pas ouvrir les ports 80/443 (FAI restrictif, port custom...), utilisez le challenge DNS-01. Let's Encrypt vérifie via un enregistrement DNS TXT.

**Exemple avec OVH** :

1. Créer des credentials API sur [api.ovh.com/createToken](https://api.ovh.com/createToken) avec les droits `GET/POST/PUT/DELETE /domain/zone/*`

2. Configurer le Caddyfile :
```caddyfile
{$DOMAIN:sync.example.com} {
    tls {
        dns ovh {
            endpoint {$OVH_ENDPOINT}
            application_key {$OVH_APPLICATION_KEY}
            application_secret {$OVH_APPLICATION_SECRET}
            consumer_key {$OVH_CONSUMER_KEY}
        }
    }
    reverse_proxy syncobsidian:8000
}
```

3. Ajouter les variables dans `.env` et les passer au conteneur Caddy dans `docker-compose.prod.yml`

**Autres providers DNS supportés** : Cloudflare, Google Cloud DNS, AWS Route53, Azure DNS, etc.  
→ Voir [github.com/caddy-dns](https://github.com/caddy-dns) pour la liste complète.

### Personnaliser l'image Caddy

Pour le challenge DNS-01, il faut une image Caddy avec le plugin DNS. Le fichier `Dockerfile.caddy` :

```dockerfile
FROM caddy:2-builder AS builder
RUN xcaddy build --with github.com/caddy-dns/ovh

FROM caddy:2-alpine
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
```

Remplacer `ovh` par votre provider si différent.

---

## 🔒 Sécurité

### Bonnes pratiques

| Élément | Recommandation |
|---------|----------------|
| `SECRET_KEY` | Utiliser une clé générée aléatoirement (32+ caractères) |
| Mot de passe | Minimum 12 caractères, complexe |
| HTTPS | **Obligatoire** en production (inclus avec Caddy) |
| Mises à jour | Mettre à jour régulièrement les images Docker |

### Ce qui est sécurisé

- ✅ Mots de passe hachés avec **bcrypt**
- ✅ Authentification par token **JWT**
- ✅ HTTPS avec certificat **Let's Encrypt** (auto-renouvelé)
- ✅ Headers de sécurité (HSTS, X-Frame-Options, etc.)

---

## Configuration du Serveur

### Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `SECRET_KEY` | Clé secrète JWT (CHANGER EN PRODUCTION!) | `change-this-...` |
| `DATABASE_URL` | URL de la base SQLite | `sqlite+aiosqlite:///./data/syncobsidian.db` |
| `STORAGE_PATH` | Chemin de stockage des fichiers | `./data/storage` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de validité du token | `1440` (24h) |
| `DOMAIN` | Domaine pour HTTPS (production) | - |

### Fichiers de configuration

| Fichier | Usage |
|---------|-------|
| `docker-compose.yml` | Développement local (HTTP) |
| `docker-compose.prod.yml` | Production avec HTTPS |
| `Caddyfile` | Configuration du reverse proxy |
| `.env` | Variables d'environnement (ne pas commiter!) |

---

## API Endpoints

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/health` | GET | Health check |
| `/auth/register` | POST | Créer un compte |
| `/auth/login` | POST | Connexion (retourne JWT) |
| `/auth/me` | GET | Infos utilisateur courant |
| `/sync` | POST | Endpoint principal de sync |
| `/sync/push` | POST | Envoyer des notes |
| `/sync/pull` | POST | Récupérer des notes |
| `/sync/attachments/push` | POST | Envoyer des pièces jointes |
| `/sync/attachments/pull` | POST | Récupérer des pièces jointes |
| `/sync/notes` | GET | Lister les notes synchronisées |
| `/sync/compare` | POST | Comparer client/serveur |

---

## Fonctionnalités

- ✅ Synchronisation bidirectionnelle des notes Markdown
- ✅ Synchronisation des pièces jointes (images, PDFs, etc. - max 25 Mo)
- ✅ Authentification sécurisée (JWT + bcrypt)
- ✅ Détection et gestion des conflits
- ✅ Propagation des suppressions entre appareils
- ✅ Synchronisation automatique (configurable)
- ✅ Synchronisation manuelle via commande/bouton
- ✅ Indicateur de statut dans la barre latérale
- ✅ Rapport de synchronisation détaillé
- ✅ Compatible desktop, iOS et Android
- ✅ Docker-ready pour déploiement facile
- ✅ HTTPS automatique avec Let's Encrypt

---

## Gestion des Conflits

Quand une note est modifiée sur plusieurs appareils simultanément :

1. Le serveur détecte le conflit (hash différent, timestamps proches)
2. Le plugin crée un fichier `note (conflit YYYY-MM-DD).md` avec la version serveur
3. L'utilisateur peut manuellement fusionner les versions

---

## Synchronisation des Suppressions

Quand une note ou pièce jointe est supprimée sur un appareil :

1. Le plugin mémorise la liste des fichiers connus après chaque sync (`knownFiles`, `knownAttachments`)
2. Au prochain sync, il compare les fichiers actuels avec ces listes
3. Les fichiers disparus sont envoyés au serveur avec `is_deleted: true`
4. Le serveur propage la suppression aux autres appareils
5. Les autres appareils suppriment le fichier local lors du pull

### Comportement

| Scénario | Résultat |
|----------|----------|
| Suppression sur Device A | Propagée à Device B au prochain sync |
| Suppression puis re-création | Le fichier revient avec le nouveau contenu |
| Modification après suppression | Le fichier modifié "gagne" et ressuscite |
| Premier sync d'un nouveau device | Aucune fausse suppression (knownFiles vide) |

### Gestion des conflits de suppression

Si Device A supprime une note pendant que Device B la modifie :
- Si la modification est **plus récente** que la suppression → la note est recréée
- Si la suppression est **plus récente** → la note est supprimée sur Device B

---

## Synchronisation des Pièces Jointes

Les fichiers binaires (images, PDFs, ZIPs, etc.) sont synchronisés automatiquement avec les notes.

### Caractéristiques

| Élément | Valeur |
|---------|--------|
| Taille max par fichier | 25 Mo |
| Transport | Base64 en JSON |
| Stockage | Filesystem (comme les notes) |
| Types supportés | Tous (images, PDFs, documents, archives...) |

### Fonctionnement

1. **Collecte** : Le plugin détecte tous les fichiers non-.md du vault
2. **Comparaison** : Hash SHA256 pour détecter les modifications
3. **Transfert** : Seuls les fichiers modifiés sont envoyés/reçus
4. **Suppressions** : Propagées entre devices (comme les notes)

### Limites

- Les fichiers > 25 Mo sont ignorés (avec avertissement)
- Les fichiers binaires ne sont pas fusionnés en cas de conflit (le plus récent gagne)

### Types MIME

Le type MIME est **détecté automatiquement** basé sur l'extension du fichier (pas sur le contenu).
Il est stocké comme métadonnée mais **n'est pas validé** côté serveur.

**Extensions reconnues** :
- Images : PNG, JPEG, GIF, WebP, SVG, BMP, ICO
- Documents : PDF, DOC(X), XLS(X), PPT(X)
- Audio/Vidéo : MP3, WAV, MP4, WebM
- Archives : ZIP, RAR, 7z, TAR, GZ
- Autres : TXT, JSON, XML, CSV

> **Note** : La validation MIME (vérification du contenu réel) est prévue en amélioration future (voir TODO.md).

---

## Structure du Projet

```
syncobsidian/
├── backend/
│   ├── app/
│   │   ├── main.py              # Point d'entrée FastAPI (monte les routers)
│   │   ├── config.py            # Configuration (env vars)
│   │   ├── database.py          # Connexion SQLite async
│   │   ├── models.py            # Modèles SQLAlchemy (User, Note, Attachment)
│   │   ├── schemas.py           # Schémas Pydantic (validation API)
│   │   ├── auth.py              # Authentification JWT + bcrypt
│   │   ├── sync.py              # Facade (rétrocompatibilité)
│   │   ├── storage.py           # Gestion fichiers (lecture/écriture)
│   │   ├── logging_config.py    # Configuration des logs
│   │   ├── routers/             # Endpoints API (Controleurs)
│   │   │   ├── auth.py          # /auth/* (register, login, me)
│   │   │   └── sync.py          # /sync/* (push, pull, compare...)
│   │   └── services/            # Logique métier
│   │       ├── sync_utils.py    # Helpers partagés (datetime, queries)
│   │       ├── notes_sync.py    # Sync notes (push, pull, process)
│   │       ├── attachments_sync.py  # Sync attachments
│   │       └── compare_sync.py  # Comparaison client/serveur
│   ├── tests/                   # Tests d'intégration (API)
│   │   ├── conftest.py          # Fixtures pytest (client, auth, db)
│   │   ├── test_auth.py         # Tests authentification
│   │   ├── test_sync_*.py       # Tests synchronisation
│   │   ├── test_attachments*.py # Tests pièces jointes
│   │   └── unit/                # Tests unitaires (mocks)
│   │       ├── test_sync_utils.py
│   │       ├── test_notes_sync.py
│   │       ├── test_attachments_sync.py
│   │       └── test_compare_sync.py
│   ├── run_tests.sh             # Lancement des tests d'intégration
│   ├── tests_remote.sh          # Tests E2E post-déploiement
│   ├── data/                    # Données persistantes (volume Docker)
│   │   ├── syncobsidian.db      # Base SQLite
│   │   └── storage/             # Fichiers par utilisateur
│   ├── Dockerfile
│   ├── docker-compose.yml       # Dev local (HTTP)
│   ├── docker-compose.prod.yml  # Production (HTTPS + Caddy)
│   ├── Caddyfile                # Config reverse proxy
│   ├── logging.yaml             # Config logs avec timestamps
│   └── requirements.txt
│
├── obsidian-plugin/
│   ├── src/
│   │   ├── main.ts              # Point d'entrée plugin Obsidian
│   │   ├── types.ts             # Types TypeScript (API + settings)
│   │   ├── settings.ts          # Page de configuration + rapport sync
│   │   ├── api-client.ts        # Client HTTP pour l'API
│   │   ├── sync-service.ts      # Service de sync (notes + attachments)
│   │   ├── __mocks__/
│   │   │   └── obsidian.ts      # Mocks de l'API Obsidian pour les tests
│   │   └── __tests__/
│   │       ├── api-client.test.ts    # Tests ApiClient (28 tests)
│   │       ├── sync-service.test.ts  # Tests SyncService (31 tests)
│   │       └── settings.test.ts      # Tests formatage rapport (26 tests)
│   ├── jest.config.js           # Configuration Jest
│   ├── manifest.json            # Métadonnées plugin (version 1.6.0)
│   ├── package.json
│   └── esbuild.config.mjs
│
├── README.md                    # Documentation principale
├── TODO.md                      # Roadmap et améliorations futures
└── SPEC-attachments-sync.md     # Spécification technique attachments
```

---

## Développement

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Tests backend

```bash
cd backend
source venv/bin/activate  # Si pas déjà actif

# Tests unitaires uniquement (rapide, avec mocks)
pytest tests/unit/ -v                    # 60 tests

# Tests d'intégration uniquement (API réelle)
pytest tests/ --ignore=tests/unit/ -v    # ~138 tests

# Tous les tests
pytest tests/ -v                         # ~198 tests

# Via le script (intégration uniquement, gère le venv)
./run_tests.sh
./run_tests.sh -v           # Verbose
./run_tests.sh test_auth    # Filtrer par nom
```

### Plugin
```bash
cd obsidian-plugin
npm install
npm run dev  # Mode watch
```

### Tests plugin
```bash
cd obsidian-plugin
npm test              # Lancer tous les tests (85 tests)
npm run test:watch    # Mode watch (re-run on change)
npm run test:coverage # Avec rapport de couverture
```

---

## Dépannage

### Le certificat HTTPS ne se génère pas

1. Vérifier que le domaine pointe vers l'IP du serveur :
```bash
nslookup sync.example.com
```
2. Vérifier que le port 443 est accessible depuis Internet
3. Consulter les logs Caddy : `docker compose -f docker-compose.prod.yml logs caddy`

### L'API ne répond pas

```bash
# Vérifier les logs
docker compose -f docker-compose.prod.yml logs syncobsidian

# Vérifier que les conteneurs tournent
docker ps
```

---

## 🗄️ Administration des données

### Base de données SQLite

La base de données se trouve dans `backend/data/syncobsidian.db`.

**Accès à la CLI SQLite** :
```bash
sqlite3 backend/data/syncobsidian.db
```

**Commandes utiles** :
```sql
-- Lister les tables
.tables

-- Voir la structure d'une table
.schema users
.schema notes
.schema attachments

-- Lister les utilisateurs
SELECT id, username, email, created_at, is_active FROM users;

-- Lister les notes d'un utilisateur (ex: user_id = 1)
SELECT id, path, content_hash, modified_at, is_deleted FROM notes WHERE user_id = 1;

-- Compter les notes par utilisateur
SELECT u.username, COUNT(n.id) as nb_notes 
FROM users u LEFT JOIN notes n ON u.id = n.user_id 
GROUP BY u.id;

-- Supprimer un utilisateur (cascade sur notes et attachments)
DELETE FROM users WHERE id = 1;

-- Quitter SQLite
.quit
```

**Structure des tables** :

| Table | Colonnes |
|-------|----------|
| `users` | `id`, `username`, `email`, `hashed_password`, `created_at`, `is_active` |
| `notes` | `id`, `user_id`, `path`, `content_hash`, `modified_at`, `synced_at`, `is_deleted` |
| `attachments` | `id`, `user_id`, `path`, `content_hash`, `size`, `mime_type`, `modified_at`, `synced_at`, `is_deleted` |

**Contraintes et index** :

| Table | Contrainte | Description |
|-------|------------|-------------|
| `users` | `UNIQUE(username)` | Un seul compte par username |
| `users` | `UNIQUE(email)` | Un seul compte par email |
| `notes` | `UNIQUE(user_id, path)` | Une seule note par chemin par utilisateur |
| `attachments` | `UNIQUE(user_id, path)` | Un seul attachment par chemin par utilisateur |

### Fichiers (notes et attachments)

Les fichiers sont stockés dans `backend/data/storage/`.

**Structure** :
```
data/storage/
├── 1/                          # user_id = 1
│   ├── notes/
│   │   ├── dossier/
│   │   │   └── ma-note.md
│   │   └── autre-note.md
│   └── attachments/
│       └── images/
│           └── photo.png
├── 2/                          # user_id = 2
│   └── notes/
│       └── ...
```

**Commandes utiles** :
```bash
# Lister les notes d'un utilisateur
ls -la backend/data/storage/1/notes/

# Voir le contenu d'une note
cat backend/data/storage/1/notes/ma-note.md

# Supprimer une note manuellement (mettre aussi is_deleted=1 dans la BDD)
rm backend/data/storage/1/notes/ma-note.md

# Voir l'espace disque utilisé par utilisateur
du -sh backend/data/storage/*/
```

> ⚠️ **Important** : Si vous supprimez un fichier manuellement, pensez à mettre à jour la base de données (marquer `is_deleted = 1`) sinon la synchronisation pourrait recréer le fichier.

### Accès aux données en production (Docker)

En production, les données sont dans un **volume Docker** et nécessitent `sudo` :

```bash
# Trouver le chemin du volume
docker volume inspect backend_syncobsidian-data --format '{{ .Mountpoint }}'
# → /var/lib/docker/volumes/backend_syncobsidian-data/_data

# Lister le contenu
sudo ls -la /var/lib/docker/volumes/backend_syncobsidian-data/_data

# Accéder à SQLite
sudo sqlite3 /var/lib/docker/volumes/backend_syncobsidian-data/_data/syncobsidian.db
```

**Nettoyage des données de test** :

```sql
-- Vérifier les utilisateurs de test
SELECT id, username, email FROM users WHERE username LIKE 'testuser_%';

-- Vérifier les notes associées
SELECT n.id, u.username, n.path FROM notes n 
JOIN users u ON n.user_id = u.id 
WHERE u.username LIKE 'testuser_%';

-- Vérifier les attachments associés
SELECT a.id, u.username, a.path FROM attachments a 
JOIN users u ON a.user_id = u.id 
WHERE u.username LIKE 'testuser_%';

-- Supprimer les notes des utilisateurs de test
DELETE FROM notes WHERE user_id IN (SELECT id FROM users WHERE username LIKE 'testuser_%');

-- Supprimer les attachments des utilisateurs de test
DELETE FROM attachments WHERE user_id IN (SELECT id FROM users WHERE username LIKE 'testuser_%');

-- Supprimer les utilisateurs de test
DELETE FROM users WHERE username LIKE 'testuser_%';

-- Vérifier le résultat
SELECT * FROM users;
```

```bash
# Supprimer les dossiers de fichiers associés (remplacer 2, 3 par les IDs supprimés)
sudo rm -rf /var/lib/docker/volumes/backend_syncobsidian-data/_data/storage/2
sudo rm -rf /var/lib/docker/volumes/backend_syncobsidian-data/_data/storage/3
```

---

## License

MIT
