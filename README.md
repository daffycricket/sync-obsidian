# SyncObsidian - Synchronisation Auto-Hébergée pour Obsidian

Service de synchronisation Obsidian self-hosted permettant de synchroniser vos notes sur tous vos appareils (desktop, iOS, Android).

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
   - Ports 443 (ou un port custom) accessibles depuis Internet

2. **Configurer l'environnement** :
```bash
cd backend
cp .env.example .env
nano .env
```

```env
SECRET_KEY=votre_cle_secrete_generee
DOMAIN=sync.example.com
```

3. **Lancer en production** :
```bash
docker compose -f docker-compose.prod.yml up -d
```

Le fichier `docker-compose.prod.yml` inclut Caddy qui gère automatiquement les certificats Let's Encrypt.

4. **Configurer Obsidian** :
   - **URL du serveur** : `https://sync.example.com` (avec le port si différent de 443)
   - **Identifiants** : ceux créés via `/auth/register`

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

---

## Fonctionnalités

- ✅ Synchronisation bidirectionnelle des notes Markdown
- ✅ Authentification sécurisée (JWT + bcrypt)
- ✅ Détection et gestion des conflits
- ✅ Synchronisation automatique (configurable)
- ✅ Synchronisation manuelle via commande/bouton
- ✅ Indicateur de statut dans la barre latérale
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

Quand une note est supprimée sur un appareil :

1. Le plugin mémorise la liste des fichiers connus après chaque sync (`knownFiles`)
2. Au prochain sync, il compare les fichiers actuels avec `knownFiles`
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

## Structure du Projet

```
syncobsidian/
├── backend/
│   ├── app/
│   │   ├── main.py              # Point d'entrée FastAPI
│   │   ├── config.py            # Configuration
│   │   ├── models.py            # Modèles SQLAlchemy
│   │   ├── schemas.py           # Schémas Pydantic
│   │   ├── auth.py              # Authentification JWT
│   │   ├── sync.py              # Logique de synchronisation
│   │   └── storage.py           # Gestion fichiers
│   ├── Dockerfile
│   ├── docker-compose.yml       # Dev local
│   ├── docker-compose.prod.yml  # Production HTTPS
│   ├── Caddyfile                # Config reverse proxy
│   ├── logging.yaml             # Config logs avec timestamps
│   └── requirements.txt
│
└── obsidian-plugin/
    ├── src/
    │   ├── main.ts              # Point d'entrée plugin
    │   ├── types.ts             # Types TypeScript
    │   ├── settings.ts          # Page de configuration
    │   ├── api-client.ts        # Client API
    │   └── sync-service.ts      # Service de sync
    ├── manifest.json
    ├── package.json
    └── esbuild.config.mjs
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

### Tests
```bash
cd backend
pip install -r requirements-test.txt
pytest tests/ -v
```

### Plugin
```bash
cd obsidian-plugin
npm install
npm run dev  # Mode watch
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

---

## License

MIT
