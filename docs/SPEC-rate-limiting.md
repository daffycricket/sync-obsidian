# Spécification : Rate Limiting avec Caddy

**Statut :** Implémenté (01/02/2026) - Commit `d0142f7`

---

## 1. Contexte et objectifs

### Problème

L'API est actuellement exposée sans protection contre :
- **Attaques par force brute** sur `/auth/login`
- **Attaques DDoS** (layer 7) sur tous les endpoints
- **Abus** de l'endpoint `/health` (monitoring agressif)

### Solution retenue

Ajouter le module `caddy-ratelimit` à l'image Caddy existante pour limiter les requêtes par IP et par endpoint.

### Limites définies

| Endpoint | Limite | Justification |
|----------|--------|---------------|
| `/auth/login` | 5 req/min | Protection brute force |
| `/health` | 20 req/min | Monitoring raisonnable |
| `/*` (autres) | 120 req/min | Usage normal sync |

---

## 2. Architecture cible

```
Internet (HTTPS:20443)
        │
        ▼
┌─────────────────────────────────────┐
│            Caddy                    │
│  ┌───────────────────────────────┐  │
│  │  TLS (Let's Encrypt DNS-01)  │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │  Rate Limiter (par IP)       │  │
│  │  - /auth/login  → 5/min      │  │
│  │  - /health      → 20/min     │  │
│  │  - /*           → 120/min    │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │  Reverse Proxy               │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
        │ HTTP:8000
        ▼
┌─────────────────────────────────────┐
│         FastAPI (syncobsidian)      │
└─────────────────────────────────────┘
```

---

## 3. Modifications à effectuer

### 3.1 Fichier `backend/Dockerfile.caddy`

**Avant :**
```dockerfile
FROM caddy:2-builder AS builder
RUN xcaddy build --with github.com/caddy-dns/ovh

FROM caddy:2-alpine
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
```

**Après :**
```dockerfile
FROM caddy:2-builder AS builder
RUN xcaddy build \
    --with github.com/caddy-dns/ovh \
    --with github.com/mholt/caddy-ratelimit

FROM caddy:2-alpine
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
```

**Impact :** Rebuild de l'image Caddy nécessaire (~2-3 min)

---

### 3.2 Fichier `backend/Caddyfile`

**Avant :**
```caddyfile
{$DOMAIN:vault.mon-domaine.fr} {
    tls {
        dns ovh {
            endpoint {$OVH_ENDPOINT}
            application_key {$OVH_APPLICATION_KEY}
            application_secret {$OVH_APPLICATION_SECRET}
            consumer_key {$OVH_CONSUMER_KEY}
        }
    }

    reverse_proxy syncobsidian:8000

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
    }

    log {
        output stdout
        format console
    }
}
```

**Après :**
```caddyfile
{
    # Activer le rate limiting avant le reverse proxy
    order rate_limit before reverse_proxy
}

{$DOMAIN:vault.mon-domaine.fr} {
    tls {
        dns ovh {
            endpoint {$OVH_ENDPOINT}
            application_key {$OVH_APPLICATION_KEY}
            application_secret {$OVH_APPLICATION_SECRET}
            consumer_key {$OVH_CONSUMER_KEY}
        }
    }

    # ===========================================
    # RATE LIMITING PAR ENDPOINT
    # ===========================================

    # /auth/login - 5 requêtes/minute (protection brute force)
    @login {
        path /auth/login
    }
    rate_limit @login {
        zone login {
            key    {remote_host}
            events 5
            window 1m
        }
    }

    # /health - 20 requêtes/minute (monitoring)
    @health {
        path /health
    }
    rate_limit @health {
        zone health {
            key    {remote_host}
            events 20
            window 1m
        }
    }

    # Tous les autres endpoints - 120 requêtes/minute
    rate_limit {
        zone api {
            key    {remote_host}
            events 120
            window 1m
        }
    }

    # ===========================================
    # REVERSE PROXY
    # ===========================================
    reverse_proxy syncobsidian:8000

    # ===========================================
    # HEADERS DE SECURITE
    # ===========================================
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
    }

    # ===========================================
    # LOGS
    # ===========================================
    log {
        output stdout
        format console
    }
}
```

---

## 4. Comportement du rate limiter

### Réponse en cas de dépassement

Quand la limite est atteinte, Caddy renvoie :

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
Content-Type: text/plain

rate limit exceeded
```

### Fenêtre glissante

Le module utilise une **fenêtre glissante** (sliding window), pas une fenêtre fixe :
- Plus précis que les fenêtres fixes
- Évite les pics en début de fenêtre

### Clé de rate limiting

`{remote_host}` = adresse IP du client. En cas de proxy amont (Cloudflare, etc.), utiliser `{http.request.header.X-Forwarded-For}` à la place.

---

## 5. Procédure de déploiement

### 5.1 Prérequis

- Accès SSH au serveur de production
- Docker et docker-compose installés
- Repo git à jour

### 5.2 Étapes

```bash
# 1. Se connecter au serveur
ssh user@serveur-prod

# 2. Aller dans le répertoire du projet
cd ~/apps/sync-obsidian/backend

# 3. Récupérer les modifications
git pull

# 4. Vérifier les fichiers modifiés
cat Dockerfile.caddy
cat Caddyfile

# 5. Rebuild et redémarrer Caddy (ATTENTION: interruption ~30s)
docker compose -f docker-compose.prod.yml up -d --build caddy

# 6. Vérifier les logs de démarrage
docker compose -f docker-compose.prod.yml logs -f caddy
# Attendre de voir: "certificate obtained successfully" ou similar
# Ctrl+C pour quitter les logs

# 7. Vérifier que le service répond
curl -I https://vault.mon-domaine.fr:20443/health
```

### 5.3 Rollback en cas de problème

```bash
# Revenir à la version précédente
git checkout HEAD~1 -- Dockerfile.caddy Caddyfile

# Rebuild avec l'ancienne config
docker compose -f docker-compose.prod.yml up -d --build caddy
```

---

## 6. Tests de validation

### 6.1 Test manuel du rate limiting sur /auth/login

```bash
# Envoyer 10 requêtes rapidement (limite = 5/min)
for i in {1..10}; do
  echo "Request $i:"
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST https://vault.mon-domaine.fr:20443/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"test"}'
  sleep 0.5
done
```

**Résultat attendu :**
```
Request 1: 401  (ou 200 si credentials valides)
Request 2: 401
Request 3: 401
Request 4: 401
Request 5: 401
Request 6: 429  ← Rate limited
Request 7: 429
Request 8: 429
Request 9: 429
Request 10: 429
```

### 6.2 Test manuel du rate limiting sur /health

```bash
# Envoyer 25 requêtes rapidement (limite = 20/min)
for i in {1..25}; do
  echo -n "Request $i: "
  curl -s -o /dev/null -w "%{http_code}\n" \
    https://vault.mon-domaine.fr:20443/health
done
```

**Résultat attendu :** 20 × `200`, puis 5 × `429`

### 6.3 Test de non-régression sync

```bash
# Lancer les tests E2E depuis le serveur
cd ~/apps/sync-obsidian/backend
./tests_remote.sh
```

### 6.4 Vérification des logs

```bash
# Voir les requêtes rate-limited dans les logs Caddy
docker compose -f docker-compose.prod.yml logs caddy | grep -i "rate"
```

---

## 7. Monitoring post-déploiement

### Métriques à surveiller

| Métrique | Commande | Seuil d'alerte |
|----------|----------|----------------|
| Requêtes 429 | `grep "429" access.log \| wc -l` | > 100/heure (attaque possible) |
| Temps de réponse | `curl -w "%{time_total}"` | > 2s |
| Certificat TLS | `curl -vI 2>&1 \| grep "expire"` | < 7 jours |

### Commandes utiles post-déploiement

```bash
# Voir les stats en temps réel
docker compose -f docker-compose.prod.yml logs -f caddy

# Vérifier l'état des conteneurs
docker compose -f docker-compose.prod.yml ps

# Inspecter la config Caddy chargée
docker exec caddy caddy list-modules | grep rate

# Tester la connectivité
curl -v https://vault.mon-domaine.fr:20443/health
```

---

## 8. Configuration avancée (optionnel)

### 8.1 Personnaliser la réponse 429

```caddyfile
rate_limit @login {
    zone login {
        key    {remote_host}
        events 5
        window 1m
    }
}

handle_errors {
    @ratelimited expression {err.status_code} == 429
    respond @ratelimited "Too many login attempts. Retry in 60 seconds." 429
}
```

### 8.2 Whitelist d'IPs (monitoring interne)

```caddyfile
@monitoring {
    remote_ip 10.0.0.0/8 192.168.0.0/16
}
# Pas de rate limit pour les IPs internes
route @monitoring {
    reverse_proxy syncobsidian:8000
}
```

### 8.3 Rate limit par utilisateur authentifié

Pour un rate limiting plus fin basé sur le token JWT (nécessite extraction du claim) :

```caddyfile
# Non implémenté - nécessiterait un module custom ou une logique côté FastAPI
```

---

## 9. Checklist de déploiement

- [ ] Fichier `Dockerfile.caddy` modifié
- [ ] Fichier `Caddyfile` modifié
- [ ] Commit et push sur le repo
- [ ] Git pull sur le serveur prod
- [ ] Rebuild de l'image Caddy
- [ ] Vérification des logs de démarrage
- [ ] Test rate limit `/auth/login` (5 req → 429)
- [ ] Test rate limit `/health` (20 req → 429)
- [ ] Test fonctionnel sync depuis Obsidian
- [ ] Tests E2E passent (`tests_remote.sh`)

---

## 10. Risques et mitigations

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Build Caddy échoue | Service down | Tester le build en local d'abord |
| Config Caddyfile invalide | Caddy ne démarre pas | Valider avec `caddy validate` |
| Rate limit trop agressif | Utilisateurs légitimes bloqués | Commencer avec des limites hautes, ajuster |
| Perte certificat TLS | HTTPS cassé | Volumes Caddy persistants (déjà en place) |

---

## 11. Références

- [caddy-ratelimit GitHub](https://github.com/mholt/caddy-ratelimit)
- [Documentation Caddy](https://caddyserver.com/docs/)
- [OWASP Rate Limiting](https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html)

---

*Spécification créée le 1er février 2026*
