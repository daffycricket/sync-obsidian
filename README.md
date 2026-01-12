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
docker-compose up -d
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

## 🚀 Déploiement Production (Raspberry Pi + HTTPS gratuit)

Cette section explique comment déployer SyncObsidian sur un Raspberry Pi avec :
- ✅ **HTTPS gratuit** (Let's Encrypt)
- ✅ **URL stable gratuite** (DuckDNS)
- ✅ **Accessible depuis Internet** (Mac, Android, iOS...)

### Architecture Production

```
Internet
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  https://votre-nom.duckdns.org                              │
└─────────────────────────────────────────────────────────────┘
    │
    ▼ (ports 80/443)
┌─────────────────────────────────────────────────────────────┐
│  Freebox (NAT/Port Forwarding)                              │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Raspberry Pi                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Caddy     │─▶│ SyncObsidian │  │    DuckDNS       │   │
│  │ (HTTPS/TLS) │  │    API       │  │ (mise à jour IP) │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Étape 1 : Créer un domaine DuckDNS (gratuit)

1. Aller sur **[duckdns.org](https://www.duckdns.org)**
2. Se connecter avec Google, GitHub ou autre
3. Créer un sous-domaine (ex: `mon-vault`) → vous obtenez `mon-vault.duckdns.org`
4. **Copier votre token** affiché en haut de la page

### Étape 2 : Préparer le Raspberry Pi

```bash
# Installer Docker si pas déjà fait
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Se déconnecter/reconnecter pour appliquer

# Cloner le projet
git clone https://github.com/votre-repo/syncobsidian.git
cd syncobsidian/backend
```

### Étape 3 : Configurer l'environnement

1. **Générer une clé secrète** :
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. **Créer le fichier `.env`** :
```bash
nano .env
```

Contenu :
```env
# Clé secrète JWT (IMPORTANT: utiliser la clé générée ci-dessus)
SECRET_KEY=votre_cle_secrete_generee

# Configuration DuckDNS
DUCKDNS_SUBDOMAIN=mon-vault
DUCKDNS_TOKEN=votre-token-duckdns-ici

# Domaine (doit correspondre au subdomain DuckDNS)
DOMAIN=mon-vault.duckdns.org
```

3. **Mettre à jour le Caddyfile** :
```bash
nano Caddyfile
```

Remplacer la première ligne par votre domaine :
```
mon-vault.duckdns.org {
    ...
}
```

### Étape 4 : Configurer la Freebox

1. Accéder à **[mafreebox.freebox.fr](http://mafreebox.freebox.fr)**
2. Aller dans **Paramètres de la Freebox** → **Gestion des ports**
3. Ajouter deux redirections :

| Port externe | Port interne | IP destination | Protocole |
|--------------|--------------|----------------|-----------|
| 80           | 80           | IP du Raspberry | TCP      |
| 443          | 443          | IP du Raspberry | TCP      |

> 💡 Pour trouver l'IP de votre Raspberry : `hostname -I`

### Étape 5 : Lancer les services

```bash
cd ~/syncobsidian/backend
docker-compose -f docker-compose.prod.yml up -d
```

Vérifier que tout fonctionne :
```bash
# Voir les logs
docker-compose -f docker-compose.prod.yml logs -f

# Vérifier les conteneurs
docker ps
```

### Étape 6 : Créer votre compte

```bash
curl -X POST https://mon-vault.duckdns.org/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "monuser", "email": "email@example.com", "password": "motdepasse-fort"}'
```

### Étape 7 : Configurer Obsidian

Dans les paramètres du plugin SyncObsidian :
- **URL du serveur** : `https://mon-vault.duckdns.org`
- **Nom d'utilisateur** : `monuser`
- **Mot de passe** : `motdepasse-fort`

C'est prêt ! 🎉

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
| `DUCKDNS_SUBDOMAIN` | Sous-domaine DuckDNS | - |
| `DUCKDNS_TOKEN` | Token d'authentification DuckDNS | - |
| `DOMAIN` | Domaine complet | - |

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

1. Vérifier que les ports 80 et 443 sont bien ouverts sur la Freebox
2. Vérifier que le domaine DuckDNS pointe vers votre IP :
```bash
nslookup mon-vault.duckdns.org
```

### L'API ne répond pas

```bash
# Vérifier les logs
docker-compose -f docker-compose.prod.yml logs syncobsidian

# Vérifier que les conteneurs tournent
docker ps
```

### L'IP DuckDNS n'est pas à jour

Le conteneur `duckdns` met à jour l'IP automatiquement toutes les 5 minutes. Pour forcer :
```bash
docker-compose -f docker-compose.prod.yml restart duckdns
```

---

## License

MIT
